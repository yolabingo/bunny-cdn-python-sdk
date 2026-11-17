"""Live smoke tests against the real Bunny API.

Run with ``uv run poe test-smoke``. Needs ``BUNNYCDN_API_PYTEST`` (an account API key);
without it every test is skipped. Tests share one pull zone named ``pytest-smoke-<epoch>-<hex>``
and run in file order, so don't run them with ``-n``.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import signal
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx2
import pytest

from bunny_cdn_sdk import CoreClient, LoggingClient, RetryTransport
from bunny_cdn_sdk._exceptions import BunnyNotFoundError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bunny_cdn_sdk.models.core import PullZoneModel

ENV_VAR = "BUNNYCDN_API_PYTEST"
DOMAIN_VAR = "BUNNYCDN_PYTEST_DOMAIN"  # optional hostname-test domain; default smoke.test
PREFIX = "pytest-smoke-"
ORIGIN = "https://example.com"
HTTP_TIMEOUT = 30.0  # seconds per HTTP request
TEST_TIMEOUT = 120  # seconds per test, including retries
STALE_AFTER = 3600  # leftover zones older than this are swept at session start


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    here = Path(__file__).parent
    for item in items:
        if item.path.is_relative_to(here):
            item.add_marker(pytest.mark.smoke)


@pytest.fixture(autouse=True)
def _test_timeout() -> Iterator[None]:
    """Fail any test that runs past TEST_TIMEOUT; teardown (zone delete) still runs."""

    def fail(_signum: int, _frame: object) -> None:
        msg = f"smoke test exceeded {TEST_TIMEOUT}s"
        raise TimeoutError(msg)

    # shortcut: SIGALRM is Unix-only and main-thread-only; use pytest-timeout if Windows runs this.
    old = signal.signal(signal.SIGALRM, fail)
    signal.alarm(TEST_TIMEOUT)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, old)


@pytest.fixture(scope="session")
def api_key() -> str:
    key = os.environ.get(ENV_VAR, "").strip()
    if not key:
        pytest.skip(f"{ENV_VAR} is not set")
    return key


def _http() -> httpx2.Client:
    transport = RetryTransport(httpx2.HTTPTransport(), max_retries=2, backoff_base=1.0)
    return httpx2.Client(transport=transport, timeout=HTTP_TIMEOUT)


@pytest.fixture(scope="session")
def core(api_key: str) -> Iterator[CoreClient]:
    with _http() as http, CoreClient(api_key, client=http) as client:
        yield client


@pytest.fixture(scope="session")
def logging_client(api_key: str) -> Iterator[LoggingClient]:
    with _http() as http, LoggingClient(api_key, client=http) as client:
        yield client


def _created_at(name: str) -> int | None:
    stamp = name.removeprefix(PREFIX).split("-", 1)[0]
    return int(stamp) if name.startswith(PREFIX) and stamp.isdigit() else None


@pytest.fixture(scope="session")
def _sweep_stale(core: CoreClient) -> None:
    """Delete pytest-smoke-* zones left by crashed runs (only this prefix, only if stale)."""
    cutoff = time.time() - STALE_AFTER
    for zone in core.list_pull_zones():  # not search=: it lags for new zones
        created = _created_at(zone.get("Name") or "")
        if created is not None and created < cutoff:
            with contextlib.suppress(BunnyNotFoundError):
                core.delete_pull_zone(zone["Id"])


@pytest.fixture(scope="session")
def zone_name() -> str:
    return f"{PREFIX}{int(time.time())}-{secrets.token_hex(3)}"


@pytest.fixture(scope="session")
def zone(core: CoreClient, zone_name: str, _sweep_stale: None) -> Iterator[PullZoneModel]:
    """The run's pull zone, deleted at session end even if tests fail."""
    created = core.create_pull_zone(Name=zone_name, OriginUrl=ORIGIN)
    try:
        yield core.get_pull_zone(created["Id"])
    finally:
        with contextlib.suppress(BunnyNotFoundError):  # test_zz_delete may have removed it
            core.delete_pull_zone(created["Id"])
