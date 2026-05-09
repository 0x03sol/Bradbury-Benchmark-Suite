"""
Bradbury Benchmark Suite — Data Collector

Aggregates on-chain results from the explorer with off-chain
benchmark metadata into a unified, queryable dataset.
"""

import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .explorer import ExplorerClient
from .config import PATHS

logger = logging.getLogger(__name__)


class DataCollector:
    """
    Merges ExplorerClient output with executor results,
    writes timestamped parquet/CSV snapshots, and provides
    query interfaces for the dashboard.
    """

    def __init__(self, explorer: Optional[ExplorerClient] = None) -> None:
        self.explorer = explorer or ExplorerClient()
        self.dataset: List[Dict[str, Any]] = []

    def ingest(self, records: List[Dict[str, Any]]) -> None:
        """Append raw benchmark results. Idempotent dedup by benchmark_id + iteration."""
        existing_keys = {
            (r.get("benchmark_id"), r.get("iteration"))
            for r in self.dataset
            if r.get("benchmark_id") is not None and r.get("iteration") is not None
        }
        new = 0
        for r in records:
            bid = r.get("benchmark_id")
            it = r.get("iteration")
            if bid is None or it is None:
                self.dataset.append(r)
                new += 1
                continue
            key = (bid, it)
            if key not in existing_keys:
                self.dataset.append(r)
                existing_keys.add(key)
                new += 1
        logger.info("Ingested %d new records (%d duplicates skipped)", new, len(records) - new)

    def enrich_on_chain(self) -> None:
        """Fetch gas used and consensus status from explorer for each record.

        BenchmarkResult stores the tx hash nested under ``result['tx_hash']``;
        legacy/external snapshots may store it top-level. Support both.
        """
        for r in self.dataset:
            tx_hash = r.get("tx_hash")
            if not tx_hash:
                nested = r.get("result")
                if isinstance(nested, dict):
                    tx_hash = nested.get("tx_hash")
            if not tx_hash:
                continue
            try:
                tx = self.explorer.get_transaction(tx_hash)
                r["gas_used"] = tx.get("gasUsed") or tx.get("gas_used")
                r["block_number"] = tx.get("blockNumber") or tx.get("block_number")
                consensus = self.explorer.get_consensus_log(tx_hash)
                r["consensus_converged"] = consensus.get("converged", False)
                r["appeal_count"] = consensus.get("appeal_count", 0)
                r["leader_model"] = consensus.get("leader_model")
                r["validator_models"] = consensus.get("validator_models", [])
            except Exception as exc:
                logger.debug("Enrich failed for %s: %s", tx_hash, exc)

    def to_dataframe(self) -> pd.DataFrame:
        """Return current dataset as a pandas DataFrame."""
        return pd.DataFrame(self.dataset)

    def save_snapshot(self, label: Optional[str] = None) -> Path:
        """Persist CSV + JSON snapshot to data dir."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        label = label or "default"
        base = PATHS.data_dir / f"snapshot_{label}_{timestamp}"
        PATHS.data_dir.mkdir(parents=True, exist_ok=True)

        df = self.to_dataframe()
        csv_path = base.with_suffix(".csv")
        json_path = base.with_suffix(".json")

        df.to_csv(csv_path, index=False)
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(self.dataset, fh, indent=2, default=str)

        logger.info("Snapshot saved: %s, %s", csv_path.name, json_path.name)
        return csv_path

    def load_snapshot(self, path: Path) -> None:
        """Load a prior JSON snapshot."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.dataset.clear()
        self.ingest(data)
        logger.info("Loaded snapshot with %d records from %s", len(self.dataset), path)

    def query(
        self,
        benchmark_id: Optional[str] = None,
        principle: Optional[str] = None,
        success_only: bool = True,
    ) -> pd.DataFrame:
        """Filtered DataFrame query."""
        df = self.to_dataframe()
        if benchmark_id:
            df = df[df["benchmark_id"] == benchmark_id]
        if principle:
            df = df[df["principle"] == principle]
        if success_only:
            df = df[df["success"].eq(True)]
        return df.copy()
