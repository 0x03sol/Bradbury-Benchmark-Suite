"""
Bradbury Benchmark Suite — API Server

Lightweight Flask server that serves benchmark data to the frontend dashboard.
Production deployment uses gunicorn (see Procfile / railway.toml).
"""

import json
import logging
import os
from functools import lru_cache
from pathlib import Path

from flask import Flask, jsonify, send_from_directory, abort
from flask_cors import CORS

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from src.config import PATHS
from src.collector import DataCollector
from src.research import extract_result_flag, compute_url_health

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("api")

_FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"

app = Flask(
    __name__,
    static_folder=str(_FRONTEND_DIST) if _FRONTEND_DIST.exists() else None,
    static_url_path="",
)

# CORS allowlist — comma-separated origins via FRONTEND_ORIGIN, default to localhost dev.
_origins = [o.strip() for o in os.getenv(
    "FRONTEND_ORIGIN",
    "http://localhost:3000,http://localhost:5173",
).split(",") if o.strip()]
CORS(app, resources={r"/api/*": {"origins": _origins}})


def _latest_snapshot():
    """Find the most recent snapshot JSON file by modification time."""
    snapshots = list(PATHS.data_dir.glob("snapshot_*.json"))
    if not snapshots:
        return None
    return max(snapshots, key=lambda p: p.stat().st_mtime)


@lru_cache(maxsize=8)
def _load_snapshot_cached(path_str: str, mtime_ns: int):
    """Cache snapshot DataFrames keyed on (path, mtime). Bypasses re-parse on hot reads."""
    collector = DataCollector()
    collector.load_snapshot(Path(path_str))
    return collector.to_dataframe()


def _current_df():
    """Return (snapshot_path, dataframe) for the latest snapshot, or (None, None)."""
    snapshot = _latest_snapshot()
    if snapshot is None:
        return None, None
    df = _load_snapshot_cached(str(snapshot), snapshot.stat().st_mtime_ns)
    return snapshot, df


@app.route("/api/health")
def api_health():
    """Liveness probe for platform health checks."""
    return jsonify({"status": "ok"})


@app.route("/")
def serve_index():
    """Serve the built React dashboard at the root URL."""
    if _FRONTEND_DIST.exists() and (_FRONTEND_DIST / "index.html").exists():
        return send_from_directory(str(_FRONTEND_DIST), "index.html")
    return jsonify({
        "service": "Bradbury Benchmark Suite API",
        "endpoints": ["/api/health", "/api/summary", "/api/models", "/api/appeals", "/api/url-health"],
    })


@app.route("/<path:filename>")
def serve_static(filename: str):
    """Serve frontend assets (JS, CSS, images) and SPA-fallback to index.html."""
    if not _FRONTEND_DIST.exists():
        abort(404)
    target = _FRONTEND_DIST / filename
    if target.is_file():
        return send_from_directory(str(_FRONTEND_DIST), filename)
    # SPA fallback: any unknown non-API path returns the React shell.
    return send_from_directory(str(_FRONTEND_DIST), "index.html")


@app.route("/api/summary")
def api_summary():
    snapshot, df = _current_df()
    if snapshot is None:
        return jsonify({"error": "No snapshot data available. Run 'collect' first."}), 404

    if "result" in df.columns:
        df = df.copy()
        df["consensus_converged"] = df["result"].apply(lambda r: extract_result_flag(r, "consensus_converged"))
        df["eq_principle_passed"] = df["result"].apply(lambda r: extract_result_flag(r, "eq_principle_passed"))
        df["execution_success"] = df["result"].apply(lambda r: extract_result_flag(r, "execution_success"))
    else:
        df = df.copy()
        df["consensus_converged"] = False
        df["eq_principle_passed"] = False
        df["execution_success"] = False

    total = len(df)
    successes = int(df["success"].sum()) if total else 0

    manifest_path = PATHS.data_dir / "deployed_manifest.json"
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)

    summary = {
        "total_invocations": total,
        "contract_count": len(manifest) if manifest else (df["benchmark_id"].nunique() if "benchmark_id" in df.columns else 0),
        "success_rate_pct": round(successes / total * 100, 2) if total else 0.0,
        "consensus_convergence_pct": round(df["consensus_converged"].sum() / total * 100, 2) if total else 0.0,
        "eq_principle_passed_pct": round(df["eq_principle_passed"].sum() / total * 100, 2) if total else 0.0,
        "execution_success_pct": round(df["execution_success"].sum() / total * 100, 2) if total else 0.0,
        "avg_latency_ms": round(df["latency_ms"].mean(), 2) if total else 0.0,
        "min_latency_ms": round(df["latency_ms"].min(), 2) if total else 0.0,
        "max_latency_ms": round(df["latency_ms"].max(), 2) if total else 0.0,
        "by_principle": {},
        "manifest": manifest,
        "snapshot": snapshot.name,
    }
    for principle, group in df.groupby("principle"):
        n = len(group)
        summary["by_principle"][principle] = {
            "convergence_rate": round(group["success"].mean() * 100, 2),
            "consensus_convergence_pct": round(group["consensus_converged"].sum() / n * 100, 2) if n else 0.0,
            "eq_principle_passed_pct": round(group["eq_principle_passed"].sum() / n * 100, 2) if n else 0.0,
            "execution_success_pct": round(group["execution_success"].sum() / n * 100, 2) if n else 0.0,
            "avg_latency_ms": round(group["latency_ms"].mean(), 2) if n else 0.0,
            "invocations": n,
        }

    return jsonify(summary)


@app.route("/api/models")
def api_models():
    snapshot, df = _current_df()
    if snapshot is None:
        return jsonify([]), 404

    if "model" not in df.columns:
        return jsonify([])

    models = []
    for model, group in df.groupby("model"):
        models.append({
            "name": model,
            "accuracy": round(group["success"].mean() * 100, 2),
            "latency": round(group[group["success"]]["latency_ms"].mean(), 0) if group["success"].any() else 0,
        })
    return jsonify(models)


@app.route("/api/appeals")
def api_appeals():
    snapshot, df = _current_df()
    if snapshot is None:
        return jsonify([]), 404

    if "timestamp" not in df.columns or "appeal_count" not in df.columns:
        return jsonify([])

    import pandas as pd
    df = df.copy()
    df["ts"] = pd.to_datetime(df["timestamp"], unit="s")
    timeline = df.resample("1h", on="ts").agg(
        transactions=("benchmark_id", "count"),
        avg_appeals=("appeal_count", "mean"),
    ).reset_index()

    result = []
    for _, row in timeline.iterrows():
        result.append({
            "hour": row["ts"].strftime("%H:00"),
            "txs": int(row["transactions"]),
            "appeals": round(float(row["avg_appeals"]), 1) if pd.notna(row["avg_appeals"]) else 0,
        })
    return jsonify(result)


@app.route("/api/url-health")
def api_url_health():
    snapshot, df = _current_df()
    if snapshot is None:
        return jsonify([]), 404

    health_df = compute_url_health(df)
    if health_df.empty:
        return jsonify([])
    return jsonify(health_df.to_dict(orient="records"))


if __name__ == "__main__":
    from src.config import ensure_dirs
    ensure_dirs()
    port = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    logger.info("Starting API server on port %d (debug=%s)", port, debug)
    app.run(host="0.0.0.0", port=port, debug=debug)
