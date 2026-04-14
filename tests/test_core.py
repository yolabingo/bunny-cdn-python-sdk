"""Happy-path tests for CoreClient (all 37 public methods + 2 extras)."""

from __future__ import annotations

import httpx

from bunny_cdn_sdk._client import _BaseClient
from bunny_cdn_sdk.core import CoreClient

# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------


def make_core_client(handler) -> CoreClient:
    """Inject a MockTransport into CoreClient via __new__ + _BaseClient.__init__."""
    transport = httpx.MockTransport(handler)
    core = CoreClient.__new__(CoreClient)
    _BaseClient.__init__(core, "test_api_key", client=httpx.Client(transport=transport))
    core.base_url = "https://api.bunny.net"
    return core


# ---------------------------------------------------------------------------
# Group A — Pull Zone CRUD
# ---------------------------------------------------------------------------


def test_list_pull_zones_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"Items": [], "CurrentPage": 1, "TotalItems": 0, "HasMoreItems": False},
        )

    core = make_core_client(handler)
    result = core.list_pull_zones()
    assert isinstance(result, dict)
    assert "Items" in result


def test_get_pull_zone_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 42, "Name": "test-zone"})

    core = make_core_client(handler)
    result = core.get_pull_zone(42)
    assert isinstance(result, dict)
    assert result["Id"] == 42


def test_create_pull_zone_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 10, "Name": "new-zone"})

    core = make_core_client(handler)
    result = core.create_pull_zone(Name="new-zone", OriginUrl="https://origin.example.com")
    assert isinstance(result, dict)
    assert result["Id"] == 10


def test_update_pull_zone_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 42, "Name": "updated-zone"})

    core = make_core_client(handler)
    result = core.update_pull_zone(42, Name="updated-zone")
    assert isinstance(result, dict)
    assert result["Id"] == 42


def test_delete_pull_zone_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    core = make_core_client(handler)
    result = core.delete_pull_zone(42)
    assert result == {}


# ---------------------------------------------------------------------------
# Group B — Pull Zone extras
# ---------------------------------------------------------------------------


def test_purge_pull_zone_cache_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    core = make_core_client(handler)
    result = core.purge_pull_zone_cache(1)
    assert result == {}


def test_add_custom_hostname_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    core = make_core_client(handler)
    result = core.add_custom_hostname(1, "cdn.example.com")
    assert result == {}


def test_remove_custom_hostname_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    core = make_core_client(handler)
    result = core.remove_custom_hostname(1, "cdn.example.com")
    assert result == {}


def test_add_blocked_ip_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    core = make_core_client(handler)
    result = core.add_blocked_ip(1, "1.2.3.4")
    assert result == {}


def test_remove_blocked_ip_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    core = make_core_client(handler)
    result = core.remove_blocked_ip(1, "1.2.3.4")
    assert result == {}


# ---------------------------------------------------------------------------
# Group C — Pull Zone batch + pagination (2 extras)
# ---------------------------------------------------------------------------


def test_get_pull_zones_returns_both_in_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/pullzone/1" in url:
            return httpx.Response(200, json={"Id": 1, "Name": "zone-a"})
        return httpx.Response(200, json={"Id": 2, "Name": "zone-b"})

    core = make_core_client(handler)
    result = core.get_pull_zones([1, 2])
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["Id"] == 1
    assert result[1]["Id"] == 2


def test_iter_pull_zones_yields_all_items() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(
                200,
                json={
                    "Items": [{"Id": 1}],
                    "CurrentPage": 1,
                    "TotalItems": 2,
                    "HasMoreItems": True,
                },
            )
        return httpx.Response(
            200,
            json={
                "Items": [{"Id": 2}],
                "CurrentPage": 2,
                "TotalItems": 2,
                "HasMoreItems": False,
            },
        )

    core = make_core_client(handler)
    result = list(core.iter_pull_zones())
    assert result == [{"Id": 1}, {"Id": 2}]


# ---------------------------------------------------------------------------
# Group D — Storage Zone CRUD + iter
# ---------------------------------------------------------------------------


def test_list_storage_zones_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"Items": [], "CurrentPage": 1, "TotalItems": 0, "HasMoreItems": False},
        )

    core = make_core_client(handler)
    result = core.list_storage_zones()
    assert isinstance(result, dict)
    assert "Items" in result


def test_get_storage_zone_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 7, "Name": "my-storage"})

    core = make_core_client(handler)
    result = core.get_storage_zone(7)
    assert isinstance(result, dict)
    assert result["Id"] == 7


def test_create_storage_zone_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 5, "Name": "new-storage"})

    core = make_core_client(handler)
    result = core.create_storage_zone(Name="new-storage", Region="DE")
    assert isinstance(result, dict)
    assert result["Id"] == 5


def test_update_storage_zone_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 7, "ReplicationRegions": ["NY"]})

    core = make_core_client(handler)
    result = core.update_storage_zone(7, ReplicationRegions=["NY"])
    assert isinstance(result, dict)
    assert result["Id"] == 7


def test_delete_storage_zone_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    core = make_core_client(handler)
    result = core.delete_storage_zone(7)
    assert result == {}


def test_iter_storage_zones_yields_items() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "Items": [{"Id": 7, "Name": "my-storage"}],
                "CurrentPage": 1,
                "TotalItems": 1,
                "HasMoreItems": False,
            },
        )

    core = make_core_client(handler)
    result = list(core.iter_storage_zones())
    assert result == [{"Id": 7, "Name": "my-storage"}]


# ---------------------------------------------------------------------------
# Group E — DNS Zone CRUD + iter
# ---------------------------------------------------------------------------


def test_list_dns_zones_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"Items": [], "CurrentPage": 1, "TotalItems": 0, "HasMoreItems": False},
        )

    core = make_core_client(handler)
    result = core.list_dns_zones()
    assert isinstance(result, dict)
    assert "Items" in result


def test_get_dns_zone_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 3, "Domain": "example.com"})

    core = make_core_client(handler)
    result = core.get_dns_zone(3)
    assert isinstance(result, dict)
    assert result["Id"] == 3


def test_create_dns_zone_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 3, "Domain": "example.com"})

    core = make_core_client(handler)
    result = core.create_dns_zone(Domain="example.com")
    assert isinstance(result, dict)
    assert result["Id"] == 3


def test_update_dns_zone_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 3, "CustomNameserversEnabled": True})

    core = make_core_client(handler)
    result = core.update_dns_zone(3, CustomNameserversEnabled=True)
    assert isinstance(result, dict)
    assert result["Id"] == 3


def test_delete_dns_zone_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    core = make_core_client(handler)
    result = core.delete_dns_zone(3)
    assert result == {}


def test_iter_dns_zones_yields_items() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "Items": [{"Id": 3, "Domain": "example.com"}],
                "CurrentPage": 1,
                "TotalItems": 1,
                "HasMoreItems": False,
            },
        )

    core = make_core_client(handler)
    result = list(core.iter_dns_zones())
    assert result == [{"Id": 3, "Domain": "example.com"}]


# ---------------------------------------------------------------------------
# Group F — DNS Records
# ---------------------------------------------------------------------------


def test_add_dns_record_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 99, "Type": 0, "Name": "www"})

    core = make_core_client(handler)
    result = core.add_dns_record(1, Type=0, Name="www", Value="1.2.3.4", Ttl=300)
    assert isinstance(result, dict)
    assert result["Id"] == 99


def test_update_dns_record_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 99, "Value": "5.6.7.8"})

    core = make_core_client(handler)
    result = core.update_dns_record(1, 99, Value="5.6.7.8")
    assert isinstance(result, dict)
    assert result["Id"] == 99


def test_delete_dns_record_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    core = make_core_client(handler)
    result = core.delete_dns_record(1, 99)
    assert result == {}


# ---------------------------------------------------------------------------
# Group G — Video Library CRUD
# ---------------------------------------------------------------------------


def test_list_video_libraries_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"Items": [], "CurrentPage": 1, "TotalItems": 0, "HasMoreItems": False},
        )

    core = make_core_client(handler)
    result = core.list_video_libraries()
    assert isinstance(result, dict)
    assert "Items" in result


def test_get_video_library_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 11, "Name": "my-library"})

    core = make_core_client(handler)
    result = core.get_video_library(11)
    assert isinstance(result, dict)
    assert result["Id"] == 11


def test_create_video_library_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 11, "Name": "my-library"})

    core = make_core_client(handler)
    result = core.create_video_library(Name="my-library")
    assert isinstance(result, dict)
    assert result["Id"] == 11


def test_update_video_library_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 11, "EnableDRM": True})

    core = make_core_client(handler)
    result = core.update_video_library(11, EnableDRM=True)
    assert isinstance(result, dict)
    assert result["Id"] == 11


def test_delete_video_library_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    core = make_core_client(handler)
    result = core.delete_video_library(11)
    assert result == {}


# ---------------------------------------------------------------------------
# Group H — Utilities
# ---------------------------------------------------------------------------


def test_purge_url_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    core = make_core_client(handler)
    result = core.purge_url("https://cdn.example.com/image.jpg")
    assert result == {}


def test_get_statistics_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"BandwidthUsed": 100, "RequestsServed": 50})

    core = make_core_client(handler)
    result = core.get_statistics()
    assert isinstance(result, dict)
    assert result["BandwidthUsed"] == 100


def test_list_countries_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Items": [{"IsoCode": "US", "Name": "United States"}]})

    core = make_core_client(handler)
    result = core.list_countries()
    assert isinstance(result, dict)
    assert "Items" in result


def test_list_regions_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Items": [{"Id": 1, "Name": "Falkenstein"}]})

    core = make_core_client(handler)
    result = core.list_regions()
    assert isinstance(result, dict)
    assert "Items" in result


def test_get_billing_returns_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Balance": 10.0, "MonthlyChargesStorage": 0.5})

    core = make_core_client(handler)
    result = core.get_billing()
    assert isinstance(result, dict)
    assert result["Balance"] == 10.0


# ---------------------------------------------------------------------------
# Coverage gap tests — branch paths not hit by happy-path tests above
# ---------------------------------------------------------------------------


def test_core_client_init_direct() -> None:
    """Covers CoreClient.__init__ (lines 47-48) via direct construction."""
    core = CoreClient("direct_key")
    assert core.base_url == "https://api.bunny.net"
    assert core.api_key == "direct_key"


def test_list_pull_zones_with_search() -> None:
    """Covers the search param branch in list_pull_zones (line 72)."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert "search=my-zone" in str(request.url)
        return httpx.Response(
            200,
            json={"Items": [], "CurrentPage": 1, "TotalItems": 0, "HasMoreItems": False},
        )

    core = make_core_client(handler)
    result = core.list_pull_zones(search="my-zone")
    assert isinstance(result, dict)


def test_iter_pull_zones_with_search() -> None:
    """Covers the search param branch in iter_pull_zones (line 142)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "Items": [{"Id": 1}],
                "CurrentPage": 1,
                "TotalItems": 1,
                "HasMoreItems": False,
            },
        )

    core = make_core_client(handler)
    result = list(core.iter_pull_zones(search="filter"))
    assert result == [{"Id": 1}]


def test_list_dns_zones_with_search() -> None:
    """Covers the search param branch in list_dns_zones (line 369)."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert "search=example" in str(request.url)
        return httpx.Response(
            200,
            json={"Items": [], "CurrentPage": 1, "TotalItems": 0, "HasMoreItems": False},
        )

    core = make_core_client(handler)
    result = core.list_dns_zones(search="example")
    assert isinstance(result, dict)


def test_iter_dns_zones_with_search() -> None:
    """Covers the search param branch in iter_dns_zones (line 437)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "Items": [{"Id": 3}],
                "CurrentPage": 1,
                "TotalItems": 1,
                "HasMoreItems": False,
            },
        )

    core = make_core_client(handler)
    result = list(core.iter_dns_zones(search="example"))
    assert result == [{"Id": 3}]


def test_purge_url_with_kwargs() -> None:
    """Covers the extra kwargs branch in purge_url (lines 575-576)."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        # Verify URL contains the base purge param and the extra kwarg
        assert "url=" in url
        assert "extra_param=1" in url
        return httpx.Response(204, content=b"")

    core = make_core_client(handler)
    result = core.purge_url("https://cdn.example.com/image.jpg", extra_param="1")
    assert result == {}
