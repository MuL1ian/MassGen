# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest


def _env_flag(name: str) -> bool:
    v = os.getenv(name, "").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("massgen-triage")
    group.addoption(
        "--run-integration",
        action="store_true",
        default=_env_flag("RUN_INTEGRATION"),
        help="Run tests marked as integration (or set RUN_INTEGRATION=1).",
    )
    group.addoption(
        "--run-docker",
        action="store_true",
        default=_env_flag("RUN_DOCKER"),
        help="Run tests marked as docker (or set RUN_DOCKER=1).",
    )
    group.addoption(
        "--run-expensive",
        action="store_true",
        default=_env_flag("RUN_EXPENSIVE"),
        help="Run tests marked as expensive (or set RUN_EXPENSIVE=1).",
    )
    group.addoption(
        "--xfail-expired-fail",
        action="store_true",
        default=_env_flag("XFAIL_EXPIRED_FAIL"),
        help="Fail the test session if any xfail registry entry is past expiry (or set XFAIL_EXPIRED_FAIL=1).",
    )
    group.addoption(
        "--xfail-registry",
        action="store",
        default=os.getenv("XFAIL_REGISTRY", "massgen/tests/xfail_registry.yml"),
        help="Path to xfail registry YAML (default: massgen/tests/xfail_registry.yml).",
    )


@dataclass(frozen=True)
class _XfailEntry:
    nodeid: str
    reason: str
    link: Optional[str]
    expires: Optional[date]
    strict: bool


_expired_xfails: List[_XfailEntry] = []


def _parse_iso_date(d: Any) -> Optional[date]:
    if d is None:
        return None
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        s = d.strip()
        if not s:
            return None
        # Support YYYY-MM-DD only; anything else is considered invalid and ignored.
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _load_xfail_registry(path: str) -> Dict[str, _XfailEntry]:
    p = Path(path)
    if not p.exists():
        return {}

    try:
        import yaml  # type: ignore
    except Exception:
        # If YAML isn't available, skip registry application rather than breaking all tests.
        return {}

    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return {}

    entries: Dict[str, _XfailEntry] = {}
    for nodeid, cfg in raw.items():
        if not isinstance(nodeid, str) or not nodeid.strip():
            continue
        if not isinstance(cfg, dict):
            continue
        reason = str(cfg.get("reason", "")).strip()
        if not reason:
            continue
        link = cfg.get("link")
        link_s = str(link).strip() if link is not None else None
        expires = _parse_iso_date(cfg.get("expires"))
        strict = bool(cfg.get("strict", True))
        entries[nodeid] = _XfailEntry(
            nodeid=nodeid,
            reason=reason,
            link=link_s,
            expires=expires,
            strict=strict,
        )
    return entries


def _should_skip_marker(item: pytest.Item, marker: str) -> bool:
    return item.get_closest_marker(marker) is not None


def pytest_collection_modifyitems(config: pytest.Config, items: List[pytest.Item]) -> None:
    run_integration = bool(config.getoption("--run-integration"))
    run_docker = bool(config.getoption("--run-docker"))
    run_expensive = bool(config.getoption("--run-expensive"))
    xfail_registry_path = str(config.getoption("--xfail-registry"))

    # 1) Default policy: skip integration/docker/expensive unless explicitly enabled.
    skip_integration = pytest.mark.skip(reason="integration test (enable with --run-integration or RUN_INTEGRATION=1)")
    skip_docker = pytest.mark.skip(reason="docker test (enable with --run-docker or RUN_DOCKER=1)")
    skip_expensive = pytest.mark.skip(reason="expensive test (enable with --run-expensive or RUN_EXPENSIVE=1)")

    for item in items:
        if (not run_integration) and _should_skip_marker(item, "integration"):
            item.add_marker(skip_integration)
        if (not run_docker) and _should_skip_marker(item, "docker"):
            item.add_marker(skip_docker)
        if (not run_expensive) and _should_skip_marker(item, "expensive"):
            item.add_marker(skip_expensive)

    # 2) Expiring xfail registry: apply known-failure tracking.
    registry = _load_xfail_registry(xfail_registry_path)
    if not registry:
        return

    today = datetime.now(timezone.utc).date()
    for item in items:
        entry = registry.get(item.nodeid)
        if entry is None:
            continue

        reason = entry.reason
        if entry.link:
            reason = f"{reason} ({entry.link})"
        item.add_marker(pytest.mark.xfail(reason=reason, strict=entry.strict))

        if entry.expires is not None and entry.expires < today:
            _expired_xfails.append(entry)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    # Optional: fail if any xfail registry entries are expired.
    cfg = session.config
    if not bool(cfg.getoption("--xfail-expired-fail")):
        return
    if not _expired_xfails:
        return

    # Add a visible error summary and force non-zero exit.
    lines = [
        "Expired xfail registry entries detected (set XFAIL_EXPIRED_FAIL=0 to disable, but please fix/remove them):",
        *[f"- {e.nodeid} (expired: {e.expires}) :: {e.reason}" for e in _expired_xfails],
    ]
    session.config.warn("C1", "\n".join(lines))  # type: ignore[attr-defined]
    session.exitstatus = 1
