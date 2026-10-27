#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "click==8.3.3",
#     "websocket-client==1.9.2",
#     "pytest==9.1.1",
# ]
#
# [tool.uv]
# exclude-newer = "2026-10-27T00:00:00Z"
# ///
"""Unit tests for the pure logic of the paje CLI.

The CDP/browser calls are validated live against a real Chrome; these tests
cover the deterministic helpers — picking the right tab and building the in-page
fetch expression — so a regression is caught without a browser.
"""

import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).resolve().parent.parent / "pajemploi_cli.py"


@pytest.fixture(scope="module")
def paje():
    loader = SourceFileLoader("paje", str(_MODULE_PATH))
    spec = importlib.util.spec_from_loader("paje", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_pick_target_none_when_no_pajemploi_tab(paje):
    targets = [{"type": "page", "url": "https://example.com", "webSocketDebuggerUrl": "ws://x"}]
    assert paje._pick_target(targets) is None


def test_pick_target_finds_pajemploi_page(paje):
    targets = [{"type": "page", "url": "https://pajemploi.urssaf.fr/employeur/tableau-de-bord",
                "webSocketDebuggerUrl": "ws://x"}]
    assert paje._pick_target(targets)["webSocketDebuggerUrl"] == "ws://x"


def test_pick_target_prefers_app_route_over_landing(paje):
    targets = [
        {"type": "page", "url": "https://pajemploi.urssaf.fr/", "webSocketDebuggerUrl": "ws://landing"},
        {"type": "page", "url": "https://pajemploi.urssaf.fr/employeur/salaries", "webSocketDebuggerUrl": "ws://app"},
    ]
    assert paje._pick_target(targets)["webSocketDebuggerUrl"] == "ws://app"


def test_pick_target_ignores_non_page_targets(paje):
    targets = [{"type": "service_worker", "url": "https://pajemploi.urssaf.fr/sw.js", "webSocketDebuggerUrl": "ws://sw"}]
    assert paje._pick_target(targets) is None


def test_build_call_expr_embeds_full_url(paje):
    expr = paje._build_call_expr("/salarie?idSalarie=1", "GET", None)
    assert '"https://api.urssaf.fr/paje/apaj/v1/salarie?idSalarie=1"' in expr


def test_build_call_expr_null_body_for_get(paje):
    expr = paje._build_call_expr("/x", "GET", None)
    assert "const URL = " in expr and "BODY = null" in expr


def test_build_call_expr_serializes_payload(paje):
    expr = paje._build_call_expr("/x", "POST", {"a": 1})
    assert '{"a": 1}' in expr


@pytest.mark.parametrize(
    "url,expected",
    [
        ("http://localhost:9222", True),
        ("http://127.0.0.1:9222", True),
        ("http://10.0.0.5:9222", False),
        ("https://example.com", False),
    ],
)
def test_is_local(paje, url, expected):
    assert paje._is_local(url) is expected


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
