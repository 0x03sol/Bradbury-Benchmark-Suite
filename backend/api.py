"""
Bradbury Benchmark Suite — API Server

Lightweight Flask server that serves benchmark data to the frontend dashboard.
"""

import json
import logging
import os
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from src.config import PATHS
from src.collector import DataCollector

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("api")

app = Flask(__name__)
CORS(app)


def _latest_snapshot():
    """Find the most recent snapshot JSON file."""
    snapshots = sorted(PATHS.data_dir.glob("snapshot_*.json"))
    return snapshots[-1] if snapshots else None


def _extract_flag(result, key: str) -> bool:
    """Pull a boolean flag out of the (possibly stringified) result dict."""
    if isinstance(result, dict):
        return result.get(key) is True
    if isinstance(result, str):
        # The DataFrame may have stringified the dict; do a quick substring check.
        return f"'{key}': True" in result
    return False


@app.route("/api/summary")
def api_summary():
    snapshot = _latest_snapshot()
    if not snapshot:
        return jsonify({"error": "No snapshot data available. Run 'collect' first."}), 404

    collector = DataCollector()
    collector.load_snapshot(snapshot)
    df = collector.to_dataframe()

    # Derive research flags per row (consensus convergence, eq pass, exec success)
    if "result" in df.columns:
        df = df.copy()
        df["consensus_converged"] = df["result"].apply(lambda r: _extract_flag(r, "consensus_converged"))
        df["eq_principle_passed"] = df["result"].apply(lambda r: _extract_flag(r, "eq_principle_passed"))
        df["execution_success"] = df["result"].apply(lambda r: _extract_flag(r, "execution_success"))
    else:
        df["consensus_converged"] = False
        df["eq_principle_passed"] = False
        df["execution_success"] = False

    total = len(df)
    successes = int(df["success"].sum()) if total else 0

    # Manifest of deployed contracts (best-effort)
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
    snapshot = _latest_snapshot()
    if not snapshot:
        return jsonify([]), 404

    collector = DataCollector()
    collector.load_snapshot(snapshot)
    df = collector.to_dataframe()

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
    snapshot = _latest_snapshot()
    if not snapshot:
        return jsonify([]), 404

    collector = DataCollector()
    collector.load_snapshot(snapshot)
    df = collector.to_dataframe()

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
    snapshot = _latest_snapshot()
    if not snapshot:
        return jsonify([]), 404

    collector = DataCollector()
    collector.load_snapshot(snapshot)
    df = collector.to_dataframe()

    from src.research import compute_url_health
    health_df = compute_url_health(df)
    if health_df.empty:
        return jsonify([])
    return jsonify(health_df.to_dict(orient="records"))


if __name__ == "__main__":
    from src.config import ensure_dirs
    ensure_dirs()
    port = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    logger.info("Starting API server on port %d", port)
    app.run(host="0.0.0.0", port=port, debug=True)
