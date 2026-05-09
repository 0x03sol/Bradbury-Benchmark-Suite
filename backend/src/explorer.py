"""
Bradbury Benchmark Suite — Explorer API Client

Fetches transaction data, consensus logs, and validator metadata
from both the zkSync GenLayer explorer and the native Bradbury explorer.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from .config import NETWORK

logger = logging.getLogger(__name__)


class ExplorerClientError(Exception):
    pass


class ExplorerClient:
    """Unified interface to GenLayer explorer APIs."""

    def __init__(
        self,
        zksync_url: Optional[str] = None,
        bradbury_url: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self.zksync_url = (zksync_url or NETWORK.explorer_zksync).rstrip("/")
        self.bradbury_url = (bradbury_url or NETWORK.explorer_bradbury).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, base: str, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = urljoin(base + "/", path.lstrip("/"))
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "json" in content_type or resp.text.lstrip().startswith(("{", "[")):
            return resp.json()
        return resp.text

    def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        try:
            return self._get(self.zksync_url, f"/api/v1/transactions/{tx_hash}")
        except requests.HTTPError as exc:
            if exc.response.status_code == 404:
                return {}
            raise ExplorerClientError(f"Explorer error: {exc}") from exc

    def get_transactions_by_address(self, address: str, page: int = 1, limit: int = 50) -> List[Dict[str, Any]]:
        data = self._get(self.zksync_url, "/api/v1/transactions", params={"address": address, "page": page, "limit": limit})
        if isinstance(data, dict):
            return data.get("items", data.get("result", data.get("transactions", [])))
        return data if isinstance(data, list) else []

    def get_contract_source(self, address: str) -> Optional[str]:
        data = self._get(self.zksync_url, f"/api/v1/contracts/{address}")
        if isinstance(data, dict):
            return data.get("source_code") or data.get("contract_source")
        return None

    def get_consensus_log(self, tx_hash: str) -> Dict[str, Any]:
        try:
            return self._get(self.bradbury_url, f"/api/consensus/{tx_hash}")
        except requests.HTTPError as exc:
            if exc.response.status_code == 404:
                return {}
            raise ExplorerClientError(f"Bradbury explorer error: {exc}") from exc

    def get_validator_stats(self, validator_address: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {}
        if validator_address:
            params["address"] = validator_address
        data = self._get(self.bradbury_url, "/api/validators", params=params)
        if isinstance(data, dict):
            return data.get("items", data.get("result", data.get("validators", [])))
        return data if isinstance(data, list) else []

    def get_gas_history(self, days: int = 30) -> List[Dict[str, Any]]:
        data = self._get(self.bradbury_url, "/api/gas/history", params={"days": days})
        if isinstance(data, dict):
            return data.get("items", data.get("result", data.get("history", [])))
        return data if isinstance(data, list) else []

    def export_contract_transactions(self, contract_address: str, max_pages: int = 10) -> List[Dict[str, Any]]:
        all_txs: List[Dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            batch = self.get_transactions_by_address(contract_address, page=page, limit=100)
            if not batch:
                break
            all_txs.extend(batch)
        logger.info("Exported %d transactions for %s", len(all_txs), contract_address)
        return all_txs

    def enrich_with_consensus(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched = []
        for tx in transactions:
            tx_hash = tx.get("hash") or tx.get("transactionHash") or tx.get("tx_hash")
            if tx_hash:
                consensus = self.get_consensus_log(tx_hash)
                tx["_consensus"] = consensus
            enriched.append(tx)
        return enriched
