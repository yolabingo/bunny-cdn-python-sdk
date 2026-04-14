"""Tests for top-level stats command (UTIL-02)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from bunny_cdn_sdk._exceptions import BunnyAuthenticationError
from bunny_cdn_sdk.cli import app
from bunny_cdn_sdk.cli._app import _fmt_bytes

# ---------------------------------------------------------------------------
# _fmt_bytes helper
# ---------------------------------------------------------------------------


def test_fmt_bytes_zero() -> None:
    assert _fmt_bytes(0) == "0 GB"


def test_fmt_bytes_bytes() -> None:
    assert _fmt_bytes(1023) == "0 GB"


def test_fmt_bytes_kilobytes() -> None:
    assert _fmt_bytes(1024) == "0 GB"


def test_fmt_bytes_kilobytes_fractional() -> None:
    assert _fmt_bytes(1536) == "0 GB"


def test_fmt_bytes_megabytes() -> None:
    assert _fmt_bytes(1048576) == "0 GB"


def test_fmt_bytes_gigabytes() -> None:
    # 15032385536 bytes ≈ 14 GB
    assert _fmt_bytes(15032385536) == "14 GB"


# ---------------------------------------------------------------------------
# stats — success path
# ---------------------------------------------------------------------------

_ZONE = {"Id": 1, "Name": "my-zone"}
_STATS = {
    "TotalRequestsServed": 1000,
    "TotalBandwidthUsed": 1048576,
    "BandwidthCachedChart": {"2026-01-01T00:00:00Z": 524288},
    "CacheHitRate": 0.75,
    "Error3xxChart": {"2026-01-01T00:00:00Z": 5},
    "Error4xxChart": {"2026-01-01T00:00:00Z": 10},
    "Error5xxChart": {"2026-01-01T00:00:00Z": 1},
}


def test_stats_success_all_zones(runner) -> None:
    """stats with no flags lists all zones."""
    with (
        patch("bunny_cdn_sdk.core.CoreClient") as MockClient,
    ):
        mc = MockClient.return_value
        mc.iter_pull_zones.return_value = [_ZONE]
        mc.get_statistics.return_value = _STATS
        result = runner.invoke(app, ["--api-key", "k", "stats"])
    assert result.exit_code == 0
    assert "my-zone" in result.output


def test_stats_success_single_zone(runner) -> None:
    """stats --pull-zone-id narrows to one zone."""
    with (
        patch("bunny_cdn_sdk.core.CoreClient") as MockClient,
    ):
        mc = MockClient.return_value
        mc.get_pull_zone.return_value = _ZONE
        mc.get_statistics.return_value = _STATS
        result = runner.invoke(app, ["--api-key", "k", "stats", "--pull-zone-id", "1"])
    assert result.exit_code == 0
    assert "my-zone" in result.output
    mc.get_statistics.assert_called_once()
    call_kwargs = mc.get_statistics.call_args.kwargs
    assert call_kwargs.get("pullZone") == 1
    mc.iter_pull_zones.assert_not_called()


def test_stats_date_flags_passed_to_api(runner) -> None:
    """--from and --to are forwarded as dateFrom/dateTo."""
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mc = MockClient.return_value
        mc.iter_pull_zones.return_value = [_ZONE]
        mc.get_statistics.return_value = _STATS
        runner.invoke(
            app,
            ["--api-key", "k", "stats", "--from", "2026-01-01", "--to", "2026-01-31"],
        )
    call_kwargs = mc.get_statistics.call_args.kwargs
    assert call_kwargs.get("dateFrom") == "2026-01-01"
    assert call_kwargs.get("dateTo") == "2026-01-31"


def test_stats_error_pct_computed(runner) -> None:
    """Error% column uses (3xx+4xx+5xx)/RequestsServed*100."""
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mc = MockClient.return_value
        mc.iter_pull_zones.return_value = [_ZONE]
        mc.get_statistics.return_value = _STATS
        result = runner.invoke(app, ["--api-key", "k", "stats"])
    assert result.exit_code == 0
    # 16 / 1000 * 100 = 1.60 (no % sign — units in header)
    assert "1.60" in result.output


def test_stats_error_pct_zero_requests(runner) -> None:
    """Error% shows '—' when RequestsServed is 0."""
    stats_zero = {**_STATS, "TotalRequestsServed": 0}
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mc = MockClient.return_value
        mc.iter_pull_zones.return_value = [_ZONE]
        mc.get_statistics.return_value = stats_zero
        result = runner.invoke(app, ["--api-key", "k", "stats"])
    assert result.exit_code == 0
    assert "—" in result.output


def test_stats_json_output(runner) -> None:
    """--json outputs a JSON list of per-zone dicts."""
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mc = MockClient.return_value
        mc.iter_pull_zones.return_value = [_ZONE]
        mc.get_statistics.return_value = _STATS
        result = runner.invoke(app, ["--api-key", "k", "--json", "stats"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["Name"] == "my-zone"


def test_stats_missing_auth(runner) -> None:
    """stats without --api-key exits 1 with actionable message."""
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 1
    assert "Missing API key" in result.output


def test_stats_api_error(runner) -> None:
    """stats with API error exits 1."""
    with patch("bunny_cdn_sdk.core.CoreClient") as MockClient:
        mc = MockClient.return_value
        mc.iter_pull_zones.side_effect = BunnyAuthenticationError(
            status_code=401, message="Unauthorized", response=MagicMock()
        )
        result = runner.invoke(app, ["--api-key", "bad", "stats"])
    assert result.exit_code == 1
