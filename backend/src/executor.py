"""
Bradbury Benchmark Suite — Benchmark Executor

Orchestrates deployment, repeated execution, and latency measurement
of all Intelligent Contracts in the suite.
"""

import json
import time
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .client import GenLayerClient
from .config import BENCHMARK, PATHS

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Immutable record of a single benchmark invocation."""
    benchmark_id: str
    contract_address: str
    method: str
    principle: str
    iteration: int
    success: bool
    latency_ms: float
    gas_used: Optional[int] = None
    validator_count: Optional[int] = None
    model: Optional[str] = None
    result: Any = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BenchmarkExecutor:
    """
    Deploys contracts and runs systematic benchmark suites.

    Handles:
    - Warm-up runs (discarded)
    - Iteration tracking
    - Exception isolation (one failure does not abort suite)
    - Progress logging
    """

    def __init__(
        self,
        client: GenLayerClient,
        iterations: Optional[int] = None,
        warmup: int = 0,
    ) -> None:
        self.client = client
        self.iterations = iterations or BENCHMARK.iterations
        self.warmup = warmup
        self.results: List[BenchmarkResult] = []

    def deploy_suite(
        self,
        contract_files: Optional[List[Path]] = None,
    ) -> Dict[str, str]:
        """
        Deploy all benchmark contracts and return a name->address map.

        Args:
            contract_files: List of Path objects for .py contract sources.
                          Defaults to all .py files in backend/contracts.
        """
        if contract_files is None:
            contract_files = sorted(PATHS.contracts_dir.glob("*.py"))

        deployed: Dict[str, str] = {}
        for path in contract_files:
            name = path.stem
            logger.info("Deploying %s ...", name)
            try:
                addr = self.client.deploy_contract(path)
                deployed[name] = addr
            except Exception as exc:
                logger.error("Failed to deploy %s: %s", name, exc)
                raise
        return deployed

    def run_views(
        self,
        suite: Dict[str, str],
        methods: List[Dict[str, Any]],
        callback: Optional[Any] = None,
    ) -> List[BenchmarkResult]:
        """
        Execute a list of view-method benchmarks against deployed contracts.

        Args:
            suite: name -> contract_address map from deploy_suite().
            methods: List of dicts with keys:
                - contract_name: str (key in suite)
                - method: str
                - principle: str (for metadata)
                - args: list (optional)
                - model: str (optional)
                - validator_count: int (optional)
        """
        for method_spec in methods:
            contract_name = method_spec["contract_name"]
            address = suite.get(contract_name)
            if not address:
                logger.warning("Contract %s not deployed; skipping.", contract_name)
                continue

            for i in range(-self.warmup, self.iterations):
                is_warmup = i < 0
                iteration = i if not is_warmup else -(i + 1)

                t0 = time.perf_counter()
                try:
                    # Benchmark methods are @gl.public.write — must go through consensus
                    write_result = self.client.send_transaction(
                        address,
                        method_spec["method"],
                        method_spec.get("args"),
                    )
                    latency = (time.perf_counter() - t0) * 1000
                    # "success" = transaction was ACCEPTED by GenLayer's Optimistic Democracy
                    # consensus protocol. This is the primary on-chain outcome and includes
                    # cases where validators converged on FINISHED_WITH_ERROR (they agreed
                    # the LLM output failed equivalence). Whether the equivalence principle
                    # passed (eq_principle_passed) is tracked as a separate research metric.
                    _status = write_result.get("status")
                    is_success = _status == "accepted"
                    record = BenchmarkResult(
                        benchmark_id=f"{contract_name}.{method_spec['method']}",
                        contract_address=address,
                        method=method_spec["method"],
                        principle=method_spec.get("principle", "unknown"),
                        iteration=iteration,
                        success=is_success,
                        latency_ms=round(latency, 3),
                        model=method_spec.get("model"),
                        validator_count=write_result.get("validator_count") or method_spec.get("validator_count"),
                        result={
                            "tx_hash": write_result.get("tx_hash"),
                            "status": write_result.get("status"),
                            "consensus": write_result.get("consensus"),
                            "execution": write_result.get("execution"),
                            "validator_votes": write_result.get("validator_votes"),
                            "consensus_converged": write_result.get("consensus_converged"),
                            "eq_principle_passed": write_result.get("eq_principle_passed"),
                            "execution_success": write_result.get("execution_success"),
                        },
                    )
                except Exception as exc:
                    latency = (time.perf_counter() - t0) * 1000
                    record = BenchmarkResult(
                        benchmark_id=f"{contract_name}.{method_spec['method']}",
                        contract_address=address,
                        method=method_spec["method"],
                        principle=method_spec.get("principle", "unknown"),
                        iteration=iteration,
                        success=False,
                        latency_ms=round(latency, 3),
                        model=method_spec.get("model"),
                        validator_count=method_spec.get("validator_count"),
                        error=str(exc),
                    )

                if not is_warmup:
                    self.results.append(record)
                    if callback:
                        callback(record)
                    logger.info(
                        "[%s] iter=%d success=%s latency=%.1fms",
                        record.benchmark_id,
                        record.iteration,
                        record.success,
                        record.latency_ms,
                    )

        return self.results

    def clear(self) -> None:
        """Reset result buffer."""
        self.results.clear()

    def summary(self) -> Dict[str, Any]:
        """Compute aggregate statistics over current results."""
        if not self.results:
            return {}

        total = len(self.results)
        successes = sum(1 for r in self.results if r.success)
        # Latency is computed over ALL invocations (incl. FINISHED_WITH_ERROR) because
        # round-trip time is independent of the equivalence-principle outcome.
        latencies = [r.latency_ms for r in self.results]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        max_latency = max(latencies) if latencies else 0.0
        min_latency = min(latencies) if latencies else 0.0

        # Research-level aggregates across the entire run
        converged = sum(
            1 for r in self.results
            if isinstance(r.result, dict) and r.result.get("consensus_converged") is True
        )
        eq_passed = sum(
            1 for r in self.results
            if isinstance(r.result, dict) and r.result.get("eq_principle_passed") is True
        )
        exec_success = sum(
            1 for r in self.results
            if isinstance(r.result, dict) and r.result.get("execution_success") is True
        )

        by_principle: Dict[str, Dict[str, Any]] = {}
        for r in self.results:
            p = r.principle
            if p not in by_principle:
                by_principle[p] = {"total": 0, "success": 0, "converged": 0, "eq_passed": 0, "exec_success": 0, "latencies": []}
            by_principle[p]["total"] += 1
            by_principle[p]["latencies"].append(r.latency_ms)
            if r.success:
                by_principle[p]["success"] += 1
            if isinstance(r.result, dict):
                if r.result.get("consensus_converged") is True:
                    by_principle[p]["converged"] += 1
                if r.result.get("eq_principle_passed") is True:
                    by_principle[p]["eq_passed"] += 1
                if r.result.get("execution_success") is True:
                    by_principle[p]["exec_success"] += 1

        principle_stats = {
            p: {
                "tx_acceptance_rate_pct": round(v["success"] / v["total"] * 100, 2) if v["total"] else 0.0,
                "consensus_convergence_pct": round(v["converged"] / v["total"] * 100, 2) if v["total"] else 0.0,
                "eq_principle_passed_pct": round(v["eq_passed"] / v["total"] * 100, 2) if v["total"] else 0.0,
                "execution_success_pct": round(v["exec_success"] / v["total"] * 100, 2) if v["total"] else 0.0,
                "avg_latency_ms": round(sum(v["latencies"]) / len(v["latencies"]), 2) if v["latencies"] else 0.0,
            }
            for p, v in by_principle.items()
        }

        return {
            "total_invocations": total,
            "success_count": successes,
            "failure_count": total - successes,
            "success_rate_pct": round(successes / total * 100, 2) if total else 0.0,
            "consensus_convergence_pct": round(converged / total * 100, 2) if total else 0.0,
            "eq_principle_passed_pct": round(eq_passed / total * 100, 2) if total else 0.0,
            "execution_success_pct": round(exec_success / total * 100, 2) if total else 0.0,
            "avg_latency_ms": round(avg_latency, 2),
            "min_latency_ms": round(min_latency, 2),
            "max_latency_ms": round(max_latency, 2),
            "by_principle": principle_stats,
        }
