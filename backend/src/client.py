"""
Bradbury Benchmark Suite — GenLayer Testnet Client

Uses the official GenLayer CLI (`genlayer deploy/call/write`) for
contract deployment, method invocation, and receipt polling on
the Bradbury testnet.  The private key is imported into the CLI's
keystore on first use so all subsequent commands run non-interactively.
"""

import json
import time
import logging
import subprocess
import re
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path

from .config import NETWORK, PATHS

logger = logging.getLogger(__name__)

_ACCOUNT_NAME = "bradbury-bench"


class GenLayerClientError(Exception):
    """Base exception for all client failures."""
    pass


def _run_cli(args: List[str], timeout: int = 120) -> str:
    """Run a genlayer CLI command and return stdout. Raises on non-zero exit."""
    import sys
    import os as _os
    cmd = ["genlayer"] + args
    logger.debug("CLI: %s", " ".join(cmd))
    env = {**_os.environ, "CI": "true", "GENLAYER_NO_PROMPT": "1"}
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=(sys.platform == "win32"),
            stdin=subprocess.DEVNULL,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise GenLayerClientError(f"CLI timed out: {' '.join(cmd)}") from exc
    except FileNotFoundError as exc:
        raise GenLayerClientError(
            "genlayer CLI not found. Install with: npm install -g genlayer"
        ) from exc

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        raise GenLayerClientError(f"CLI error (code {proc.returncode}): {stderr}")

    return proc.stdout.strip()


def _parse_cli_json(output: str) -> Any:
    """Extract JSON from CLI output which may contain leading info lines."""
    for i, ch in enumerate(output):
        if ch in ('{', '['):
            try:
                return json.loads(output[i:])
            except json.JSONDecodeError:
                for j in range(len(output), i, -1):
                    try:
                        return json.loads(output[i:j])
                    except json.JSONDecodeError:
                        continue
    return output


class GenLayerClient:
    """
    Client for GenLayer Bradbury testnet using the official CLI.

    On init, imports the private key into the genlayer CLI keystore
    so that deploy/call/write commands run without interactive prompts.
    """

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        max_retries: int = 3,
        backoff_base: float = 2.0,
    ) -> None:
        self.rpc_url = rpc_url or NETWORK.rpc_url
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._private_key = private_key
        self._account_address: Optional[str] = None

        # Verify CLI is available
        try:
            _run_cli(["--version"], timeout=10)
        except GenLayerClientError:
            raise GenLayerClientError(
                "genlayer CLI not found. Install with: npm install -g genlayer"
            )

        # Set network to Bradbury
        _run_cli(["network", "set", "testnet-bradbury"], timeout=10)

        # Import private key into CLI keystore (non-interactive)
        if private_key:
            self._import_key(private_key)

    def _import_key(self, private_key: str) -> None:
        """Import private key into the genlayer CLI keystore non-interactively."""
        try:
            _run_cli([
                "account", "import",
                "--name", _ACCOUNT_NAME,
                "--private-key", private_key,
                "--password", "benchmark",
                "--overwrite",
            ], timeout=30)
            logger.info("Account imported into CLI keystore")
        except GenLayerClientError as exc:
            logger.warning("Account import failed (may already exist): %s", exc)

        # Set as active account
        try:
            _run_cli(["account", "use", _ACCOUNT_NAME], timeout=10)
        except GenLayerClientError as exc:
            logger.warning("Could not set active account: %s", exc)

        # Unlock so CLI doesn't prompt for password
        try:
            _run_cli(["account", "unlock", "--account", _ACCOUNT_NAME, "--password", "benchmark"], timeout=10)
        except GenLayerClientError as exc:
            logger.debug("Account unlock skipped: %s", exc)

        # Derive address from account show
        try:
            output = _run_cli(["account", "show", "--account", _ACCOUNT_NAME], timeout=10)
            match = re.search(r'0x[0-9a-fA-F]{40}', output)
            if match:
                self._account_address = match.group(0)
                logger.info("Account address: %s", self._account_address)
        except GenLayerClientError:
            pass

    # ------------------------------------------------------------------ #
    # Account helpers
    # ------------------------------------------------------------------ #
    def set_account(self, private_key: str) -> None:
        """Set the private key for signing transactions."""
        self._private_key = private_key
        self._import_key(private_key)

    @property
    def address(self) -> Optional[str]:
        return self._account_address

    def get_balance(self, addr: Optional[str] = None) -> int:
        """Return balance in wei for address."""
        import requests
        target = addr or self.address
        if not target:
            raise GenLayerClientError("No address provided and no account loaded")
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getBalance",
            "params": [target, "latest"],
        }
        resp = requests.post(self.rpc_url, json=payload, timeout=30)
        result = resp.json().get("result", "0x0")
        return int(result, 16)

    # ------------------------------------------------------------------ #
    # Contract deployment
    # ------------------------------------------------------------------ #
    def deploy_contract(
        self,
        contract_source_path: Path,
        constructor_args: Optional[List[Any]] = None,
        gas_limit: Optional[int] = None,
    ) -> str:
        """
        Deploy an Intelligent Contract to Bradbury using the genlayer CLI.

        Returns the deployed contract address.
        """
        contract_path = str(Path(contract_source_path).resolve())
        args = ["deploy", "--contract", contract_path]

        if constructor_args:
            for arg in constructor_args:
                args.extend(["--args", str(arg)])

        if self.rpc_url:
            args.extend(["--rpc", self.rpc_url])

        output = _run_cli(args, timeout=300)
        address = self._extract_address(output)
        if not address:
            raise GenLayerClientError(f"Could not parse contract address from deploy output: {output}")
        logger.info("Contract deployed: %s", address)
        return address

    def _extract_address(self, output: str) -> Optional[str]:
        """Extract the contract address from CLI deploy output.

        The CLI outputs something like:
          Contract Address: 0xabcdef...
        or in JSON:
          'Contract Address': '0xabcdef...'
        We must match AFTER the label to avoid matching the tx hash (64 hex chars).
        """
        # Look for "Contract Address" label followed by a hex address
        match = re.search(r'Contract Address["\s:]*["\']?\s*(0x[0-9a-fA-F]{40})', output, re.IGNORECASE)
        if match:
            return match.group(1)
        # Fallback: look for "contractAddress" (JSON key)
        match = re.search(r'contractAddress["\s:]*["\']?\s*(0x[0-9a-fA-F]{40})', output, re.IGNORECASE)
        if match:
            return match.group(1)
        # Last resort: find a 40-char hex that is NOT part of a 64-char hash
        for m in re.finditer(r'0x([0-9a-fA-F]{40})\b', output):
            # Check this isn't a prefix of a 64-char hash
            start = m.start()
            after = output[start + 2:start + 66]
            if len(after) < 64 or not re.match(r'^[0-9a-fA-F]{64}$', after):
                return m.group(0)
        return None

    # ------------------------------------------------------------------ #
    # Contract interaction
    # ------------------------------------------------------------------ #
    def call_view(
        self,
        contract_address: str,
        method: str,
        args: Optional[List[Any]] = None,
    ) -> Any:
        """Call a @gl.public.view method (no state change, no gas)."""
        cli_args = ["call", contract_address, method]
        if args:
            for arg in args:
                cli_args.extend(["--args", str(arg)])
        if self.rpc_url:
            cli_args.extend(["--rpc", self.rpc_url])

        output = _run_cli(cli_args, timeout=60)
        try:
            return _parse_cli_json(output)
        except Exception:
            return output

    def send_transaction(
        self,
        contract_address: str,
        method: str,
        args: Optional[List[Any]] = None,
        value: int = 0,
        gas_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Send a state-changing transaction via genlayer write.

        The CLI waits for the transaction to be processed, so the output
        contains the full result (status, data, etc.).
        Returns a dict with keys: tx_hash, status, result, raw_output.
        """
        cli_args = ["write", contract_address, method]
        if args:
            for arg in args:
                cli_args.extend(["--args", str(arg)])
        if self.rpc_url:
            cli_args.extend(["--rpc", self.rpc_url])

        output = _run_cli(cli_args, timeout=600)
        tx_hash = self._extract_tx_hash(output)

        # Transaction status (consensus protocol level)
        # Note: FINALIZED alone does NOT mean success — must also check execution result.
        # finalized(error) = FINALIZED + FINISHED_WITH_ERROR → not accepted.
        status = "unknown"
        if "status_name: 'ACCEPTED'" in output:
            status = "accepted"
        elif "status_name: 'FINALIZED'" in output:
            # Only count as accepted if execution did NOT error
            if "txExecutionResultName: 'FINISHED_WITH_ERROR'" in output:
                status = "finalized_error"
            else:
                status = "accepted"
        elif "status_name: 'REJECTED'" in output or "status_name: 'UNDETERMINED'" in output:
            status = "rejected"
        elif "status_name: 'PENDING'" in output:
            status = "pending"

        # Overall consensus result (validators agree among themselves)
        result_name = "unknown"
        if "resultName: 'AGREE'" in output:
            result_name = "agree"
        elif "resultName: 'DISAGREE'" in output:
            result_name = "disagree"

        # Contract execution result
        exec_result = "unknown"
        if "txExecutionResultName: 'SUCCESS'" in output:
            exec_result = "success"
        elif "txExecutionResultName: 'FINISHED_WITH_ERROR'" in output:
            exec_result = "finished_with_error"

        # Parse individual validator votes (AGREE/DISAGREE on the eq principle output)
        votes_match = re.search(
            r"validatorVotesName:\s*\[([^\]]*)\]",
            output,
            re.DOTALL,
        )
        validator_votes: List[str] = []
        if votes_match:
            for v in re.findall(r"'([^']+)'", votes_match.group(1)):
                validator_votes.append(v.lower())

        # Research metrics:
        # - consensus_converged: resultName=='AGREE' means all validators reached the
        #   same execution result (the key convergence metric regardless of eq principle)
        # - eq_principle_passed: all validators voted AGREE on the equivalence check
        # - execution_success: contract returned a value rather than an error
        consensus_converged = result_name == "agree"
        eq_principle_passed = (
            bool(validator_votes) and all(v == "agree" for v in validator_votes)
        )
        execution_success = exec_result == "success"

        return {
            "tx_hash": tx_hash,
            "status": status,
            "consensus": result_name,
            "execution": exec_result,
            "validator_votes": validator_votes,
            "validator_count": len(validator_votes),
            "consensus_converged": consensus_converged,
            "eq_principle_passed": eq_principle_passed,
            "execution_success": execution_success,
            "raw_output": output,
        }

    def _extract_tx_hash(self, output: str) -> Optional[str]:
        """Extract a transaction hash from CLI output."""
        match = re.search(r'0x[0-9a-fA-F]{64}', output)
        return match.group(0) if match else None

    # ------------------------------------------------------------------ #
    # Receipt polling (via explorer API)
    # ------------------------------------------------------------------ #
    def poll_receipt(
        self,
        tx_hash: str,
        timeout: int = 300,
        poll_interval: float = 5.0,
    ) -> Dict[str, Any]:
        """Poll the explorer API until transaction is finalized."""
        import requests
        explorer_url = NETWORK.explorer_bradbury.rstrip("/")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                resp = requests.get(
                    f"{explorer_url}/api/transactions/{tx_hash}",
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "")
                    if status in ("finalized", "accepted"):
                        return data
            except Exception as exc:
                logger.debug("Receipt poll failed for %s: %s", tx_hash, exc)
            time.sleep(poll_interval)
        raise GenLayerClientError(f"Transaction not finalized in {timeout}s: {tx_hash}")

    # ------------------------------------------------------------------ #
    # Batch execution
    # ------------------------------------------------------------------ #
    def execute_batch(
        self,
        calls: List[Dict[str, Any]],
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a batch of view calls sequentially with full error isolation.

        Args:
            calls: List of dicts with keys 'contract', 'method', 'args'.
            callback: Optional per-result callback.

        Returns:
            List of result dicts with keys 'success', 'result', 'error', 'latency_ms'.
        """
        results: List[Dict[str, Any]] = []
        for call in calls:
            t0 = time.perf_counter()
            try:
                result = self.call_view(
                    call["contract"],
                    call["method"],
                    call.get("args"),
                )
                latency = round((time.perf_counter() - t0) * 1000, 3)
                record = {"success": True, "result": result, "error": None, "latency_ms": latency}
            except Exception as exc:
                latency = round((time.perf_counter() - t0) * 1000, 3)
                record = {"success": False, "result": None, "error": str(exc), "latency_ms": latency}
            if callback:
                callback(record)
            results.append(record)
        return results
