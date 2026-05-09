"""
Bradbury Benchmark Suite — Research Analysis

Statistical analysis helpers for the research report and dashboard.
"""

from typing import Any, Dict, List

import pandas as pd
import numpy as np


def extract_result_flag(result: Any, key: str) -> bool:
    """Pull a boolean flag out of a result cell that may be a dict or its repr."""
    if isinstance(result, dict):
        return result.get(key) is True
    if isinstance(result, str):
        return f"'{key}': True" in result
    return False


def compute_convergence_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Success rate and latency pivot by principle vs model."""
    if df.empty or "principle" not in df.columns or "model" not in df.columns:
        return pd.DataFrame()
    grouped = df.groupby(["principle", "model"]).agg(
        invocations=("success", "count"),
        successes=("success", "sum"),
        avg_latency_ms=("latency_ms", "mean"),
    ).reset_index()
    grouped["convergence_rate"] = grouped["successes"] / grouped["invocations"] * 100
    return grouped.round(2)


def compute_url_health(df: pd.DataFrame) -> pd.DataFrame:
    """From URL fragility benchmark: HTTP status and change rates."""
    url_records = df[df["benchmark_id"].str.contains("url_fragility", na=False)]
    if url_records.empty:
        return pd.DataFrame()
    # Assume result dict contains status and content_hash
    expanded = url_records["result"].apply(
        lambda x: x if isinstance(x, dict) else {}
    ).apply(pd.Series)
    merged = pd.concat([url_records[["contract_address"]], expanded], axis=1)
    summary = merged.groupby("contract_address").agg(
        total=("status", "count"),
        success_rate=("status", lambda s: (s == 200).mean() * 100),
        cloudflare_blocks=("status", lambda s: (s == 403).sum()),
        paywall_count=("status", lambda s: (s == 402).sum()),
        not_found=("status", lambda s: (s == 404).sum()),
    ).reset_index().round(2)
    return summary


def compute_appeal_timeline(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate appeal frequency over time."""
    if "timestamp" not in df.columns or "appeal_count" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["ts"] = pd.to_datetime(df["timestamp"], unit="s")
    timeline = df.resample("1h", on="ts").agg(
        transactions=("benchmark_id", "count"),
        avg_appeals=("appeal_count", "mean"),
    ).reset_index().round(2)
    return timeline


def compute_model_accuracy(df: pd.DataFrame) -> pd.DataFrame:
    """Compare accuracy per model from consensus logs."""
    if "model" not in df.columns or "success" not in df.columns:
        return pd.DataFrame()
    return (
        df.groupby("model")
        .agg(invocations=("success", "count"), accuracy=("success", "mean"))
        .reset_index()
        .assign(accuracy=lambda x: x["accuracy"] * 100)
        .round(2)
    )
