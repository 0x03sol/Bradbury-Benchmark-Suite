"""
Bradbury Benchmark Suite — CLI Entry Point

Usage:
    python main.py deploy
    python main.py run
    python main.py collect
    python main.py report
    python main.py dashboard
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from src.config import ensure_dirs, BENCHMARK, PATHS
from src.client import GenLayerClient
from src.executor import BenchmarkExecutor
from src.explorer import ExplorerClient
from src.collector import DataCollector
from src.exporter import Exporter
from src import research
from src.research import extract_result_flag

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def _load_private_key() -> str:
    key = os.getenv("PRIVATE_KEY")
    if not key:
        logger.error("PRIVATE_KEY env var not set.")
        sys.exit(1)
    return key


def cmd_deploy(args: argparse.Namespace) -> None:
    ensure_dirs()
    client = GenLayerClient(private_key=_load_private_key())
    executor = BenchmarkExecutor(client)
    deployed = executor.deploy_suite()
    manifest = PATHS.data_dir / "deployed_manifest.json"
    with open(manifest, "w", encoding="utf-8") as fh:
        json.dump(deployed, fh, indent=2)
    logger.info("Manifest written: %s", manifest)
    for name, addr in deployed.items():
        print(f"{name}: {addr}")


def cmd_run(args: argparse.Namespace) -> None:
    ensure_dirs()
    manifest = PATHS.data_dir / "deployed_manifest.json"
    if not manifest.exists():
        logger.error("No manifest found. Run 'deploy' first.")
        sys.exit(1)
    with open(manifest, "r", encoding="utf-8") as fh:
        suite = json.load(fh)

    client = GenLayerClient(private_key=_load_private_key())
    executor = BenchmarkExecutor(client, iterations=args.iterations)

    # Map of contract -> list of (method, principle) pairs that the contract actually implements
    contract_methods: dict = {
        "code_audit": [
            ("benchmark_strict", "strict_eq"),
            ("benchmark_prompt_comparative", "prompt_comparative"),
            ("benchmark_custom", "custom"),
        ],
        "dispute_resolution": [
            ("benchmark_prompt_comparative", "prompt_comparative"),
            ("benchmark_custom", "custom"),
        ],
        "price_oracle": [
            ("benchmark_strict", "strict_eq"),
            ("benchmark_prompt_comparative", "prompt_comparative"),
            ("benchmark_prompt_non_comparative", "prompt_non_comparative"),
            ("benchmark_custom", "custom"),
        ],
        "prompt_injection": [
            ("benchmark_strict", "strict_eq"),
            ("benchmark_prompt_comparative", "prompt_comparative"),
            ("benchmark_custom", "custom"),
        ],
        "sentiment_analysis": [
            ("benchmark_strict", "strict_eq"),
            ("benchmark_prompt_comparative", "prompt_comparative"),
            ("benchmark_custom", "custom"),
        ],
        "url_fragility": [
            ("benchmark_strict", "strict_eq"),
            ("benchmark_prompt_comparative", "prompt_comparative"),
            ("benchmark_custom", "custom"),
        ],
        "vision_pattern": [
            ("benchmark_prompt_comparative", "prompt_comparative"),
            ("benchmark_custom", "custom"),
        ],
    }

    methods = []
    for name, addr in suite.items():
        for method_name, principle in contract_methods.get(name, []):
            methods.append({
                "contract_name": name,
                "method": method_name,
                "principle": principle,
                "args": [],
            })

    executor.run_views(suite, methods)
    summary = executor.summary()
    print(json.dumps(summary, indent=2))

    snapshot = PATHS.data_dir / f"results_{args.label}.json"
    with open(snapshot, "w", encoding="utf-8") as fh:
        json.dump([r.to_dict() for r in executor.results], fh, indent=2, default=str)
    logger.info("Results saved: %s", snapshot)


def cmd_collect(args: argparse.Namespace) -> None:
    ensure_dirs()
    manifest = PATHS.data_dir / "deployed_manifest.json"
    if not manifest.exists():
        logger.error("No manifest found.")
        sys.exit(1)
    with open(manifest, "r", encoding="utf-8") as fh:
        suite = json.load(fh)

    collector = DataCollector()
    for path in PATHS.data_dir.glob("results_*.json"):
        with open(path, "r", encoding="utf-8") as fh:
            collector.ingest(json.load(fh))

    collector.enrich_on_chain()
    csv_path = collector.save_snapshot(label=args.label)
    print(f"Snapshot: {csv_path}")


def cmd_report(args: argparse.Namespace) -> None:
    ensure_dirs()
    snapshots = list(PATHS.data_dir.glob("snapshot_*.json"))
    if not snapshots:
        logger.error("No snapshots found. Run 'collect' first.")
        sys.exit(1)
    latest = max(snapshots, key=lambda p: p.stat().st_mtime)

    collector = DataCollector()
    collector.load_snapshot(latest)
    df = collector.to_dataframe()

    total = len(df)
    if total and "result" in df.columns:
        df = df.copy()
        df["consensus_converged"] = df["result"].apply(lambda r: extract_result_flag(r, "consensus_converged"))
        df["eq_principle_passed"] = df["result"].apply(lambda r: extract_result_flag(r, "eq_principle_passed"))
        df["execution_success"] = df["result"].apply(lambda r: extract_result_flag(r, "execution_success"))
    else:
        for c in ("consensus_converged", "eq_principle_passed", "execution_success"):
            df[c] = False

    summary = {
        "total_invocations": total,
        "success_rate_pct": round(df["success"].sum() / total * 100, 2) if total else 0.0,
        "consensus_convergence_pct": round(df["consensus_converged"].sum() / total * 100, 2) if total else 0.0,
        "eq_principle_passed_pct": round(df["eq_principle_passed"].sum() / total * 100, 2) if total else 0.0,
        "execution_success_pct": round(df["execution_success"].sum() / total * 100, 2) if total else 0.0,
        "avg_latency_ms": round(df["latency_ms"].mean(), 2) if total else 0.0,
        "min_latency_ms": round(df["latency_ms"].min(), 2) if total else 0.0,
        "max_latency_ms": round(df["latency_ms"].max(), 2) if total else 0.0,
        "by_principle": {},
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

    manifest_path = PATHS.data_dir / "deployed_manifest.json"
    manifest_data = None
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest_data = json.load(fh)

    exporter = Exporter()
    report_path = exporter.generate_research_report(summary, df, manifest=manifest_data)
    csv_path = exporter.export_csv(df, f"benchmark_data_{args.label}.csv")
    print(f"Report: {report_path}")
    print(f"CSV: {csv_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bradbury Benchmark Suite")
    sub = parser.add_subparsers(dest="command", required=True)

    p_deploy = sub.add_parser("deploy", help="Deploy all benchmark contracts")
    p_deploy.set_defaults(func=cmd_deploy)

    p_run = sub.add_parser("run", help="Execute benchmark suite")
    p_run.add_argument("--iterations", type=int, default=BENCHMARK.iterations)
    p_run.add_argument("--label", type=str, default="default")
    p_run.set_defaults(func=cmd_run)

    p_collect = sub.add_parser("collect", help="Collect and enrich on-chain data")
    p_collect.add_argument("--label", type=str, default="default")
    p_collect.set_defaults(func=cmd_collect)

    p_report = sub.add_parser("report", help="Generate research report + CSV")
    p_report.add_argument("--label", type=str, default="default")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
