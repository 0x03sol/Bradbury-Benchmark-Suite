"""
Bradbury Benchmark Suite — Configuration

Loads environment variables and provides validated settings
for all testnet interactions.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Tuple
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@dataclass(frozen=True)
class NetworkConfig:
    """Immutable network configuration for Bradbury Testnet."""
    rpc_url: str = field(default_factory=lambda: os.getenv("GENLAYER_RPC_URL", "https://rpc-bradbury.genlayer.com"))
    chain_id: int = field(default_factory=lambda: int(os.getenv("GENLAYER_CHAIN_ID", "4221")))
    symbol: str = field(default_factory=lambda: os.getenv("GENLAYER_SYMBOL", "GEN"))
    faucet_url: str = field(default_factory=lambda: os.getenv("FAUCET_URL", "https://testnet-faucet.genlayer.foundation"))
    explorer_zksync: str = field(default_factory=lambda: os.getenv("EXPLORER_ZKSYNC", "https://zksync-os-testnet-genlayer.explorer.zksync.dev"))
    explorer_bradbury: str = field(default_factory=lambda: os.getenv("EXPLORER_BRADBURY", "http://explorer-bradbury.genlayer.com"))


@dataclass(frozen=True)
class BenchmarkConfig:
    """Immutable benchmark execution parameters."""
    iterations: int = field(default_factory=lambda: int(os.getenv("BENCHMARK_ITERATIONS", "100")))
    validator_counts: Tuple[int, ...] = field(default_factory=lambda: tuple(int(x.strip()) for x in os.getenv("VALIDATOR_COUNTS", "3,5,7,11").split(",")))
    default_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("DEFAULT_TIMEOUT_SECONDS", "300")))
    models: Tuple[str, ...] = field(default_factory=lambda: tuple(x.strip() for x in os.getenv("MODELS", "openai/gpt-4,anthropic/claude-3-opus,meta/llama-3-70b").split(",")))


@dataclass(frozen=True)
class PathsConfig:
    """Immutable filesystem paths."""
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "./data")).resolve())
    reports_dir: Path = field(default_factory=lambda: Path(os.getenv("REPORTS_DIR", "./reports")).resolve())
    contracts_dir: Path = field(default_factory=lambda: (Path(__file__).resolve().parents[1] / "contracts"))


# Global singleton instances
NETWORK = NetworkConfig()
BENCHMARK = BenchmarkConfig()
PATHS = PathsConfig()


def ensure_dirs() -> None:
    """Create data and reports directories if missing. Idempotent."""
    PATHS.data_dir.mkdir(parents=True, exist_ok=True)
    PATHS.reports_dir.mkdir(parents=True, exist_ok=True)
