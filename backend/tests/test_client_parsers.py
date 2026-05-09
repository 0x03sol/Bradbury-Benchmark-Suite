"""
Unit tests for the GenLayer CLI output parsers in src.client.

These exercise the regex/substring heuristics that translate raw CLI stdout
into structured benchmark results — the most fragile and load-bearing code
in the suite.
"""

import os

import pytest

# Avoid the live CLI version probe in GenLayerClient.__init__ during tests.
os.environ.setdefault("PRIVATE_KEY", "0x" + "0" * 64)

from src.client import GenLayerClient


@pytest.fixture
def client():
    # Don't run __init__ — we only want the unbound parser methods.
    return GenLayerClient.__new__(GenLayerClient)


# --------------------------------------------------------------------------- #
# Address extraction
# --------------------------------------------------------------------------- #
def test_extract_address_label_form(client):
    out = "Deploying...\nContract Address: 0x8aEF4546645239508A39BCce55026D9Fb9C6C610\n"
    assert client._extract_address(out) == "0x8aEF4546645239508A39BCce55026D9Fb9C6C610"


def test_extract_address_json_key(client):
    out = "{'contractAddress': '0xCc9481Eae9Fab61600f949a304ae877C241B1E1f'}"
    assert client._extract_address(out) == "0xCc9481Eae9Fab61600f949a304ae877C241B1E1f"


def test_extract_address_does_not_match_tx_hash_prefix(client):
    # 64-char hex → must NOT be returned as a 40-char address.
    tx = "0x" + "ab" * 32
    assert client._extract_address(f"tx submitted: {tx}") is None


def test_extract_address_returns_none_when_absent(client):
    assert client._extract_address("nothing useful here") is None


# --------------------------------------------------------------------------- #
# Tx hash extraction
# --------------------------------------------------------------------------- #
def test_extract_tx_hash(client):
    tx = "0x" + "f" * 64
    assert client._extract_tx_hash(f"hash: {tx}") == tx


def test_extract_tx_hash_none(client):
    assert client._extract_tx_hash("no hash here") is None


# --------------------------------------------------------------------------- #
# JSON-from-CLI parser
# --------------------------------------------------------------------------- #
def test_parse_cli_json_object():
    from src.client import _parse_cli_json
    out = "INFO: starting\nresult: {\"ok\": true, \"n\": 3}"
    assert _parse_cli_json(out) == {"ok": True, "n": 3}


def test_parse_cli_json_array():
    from src.client import _parse_cli_json
    assert _parse_cli_json("noise [1, 2, 3]") == [1, 2, 3]


def test_parse_cli_json_falls_back_to_raw():
    from src.client import _parse_cli_json
    assert _parse_cli_json("plain text") == "plain text"
