#!/usr/bin/env python3
"""Verification script for Task 3: _BaseClient behavior validation."""

import asyncio
import sys

import httpx

from bunny_cdn_sdk._client import _BaseClient


def test_instantiation() -> bool:
    """Test basic instantiation."""
    print("Test 1: Basic instantiation...", end=" ")
    try:
        client = _BaseClient("test-key")
        assert client.api_key == "test-key"
        assert client._client_owner is True
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_instantiation_with_client() -> bool:
    """Test instantiation with injected client."""
    print("Test 2: Instantiation with injected AsyncClient...", end=" ")
    try:
        async def cleanup() -> None:
            injected_client = httpx.AsyncClient()
            client = _BaseClient("test-key", client=injected_client)
            assert client.api_key == "test-key"
            assert client._client_owner is False
            await injected_client.aclose()

        asyncio.run(cleanup())
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_sync_context_manager() -> bool:
    """Test sync context manager."""
    print("Test 3: Sync context manager...", end=" ")
    try:
        with _BaseClient("test-key") as client:
            assert client.api_key == "test-key"
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_async_context_manager() -> bool:
    """Test async context manager."""
    print("Test 4: Async context manager...", end=" ")
    try:
        async def async_cm() -> None:
            async with _BaseClient("test-key") as client:
                assert client.api_key == "test-key"

        asyncio.run(async_cm())
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_header_injection() -> bool:
    """Test header injection."""
    print("Test 5: Header injection (AccessKey and User-Agent)...", end=" ")
    try:
        async def test_headers() -> None:
            # Create a mock transport that captures the request
            captured_request: dict[str, object] = {}

            def mock_handler(request: httpx.Request) -> httpx.Response:
                captured_request["headers"] = dict(request.headers)
                return httpx.Response(200, json={"ok": True})

            transport = httpx.MockTransport(mock_handler)
            mock_client = httpx.AsyncClient(transport=transport)
            client = _BaseClient("test-key", client=mock_client)

            # Make a request
            response = await client._request("GET", "https://api.bunny.net/test")
            await mock_client.aclose()

            # Verify headers (httpx normalizes header names to lowercase)
            headers = captured_request.get("headers", {})
            assert isinstance(headers, dict), f"Headers is not dict: {type(headers)}"
            assert headers.get("accesskey") == "test-key", (
                f"AccessKey mismatch: {headers.get('accesskey')}"
            )
            assert headers.get("user-agent") == "bunny-cdn-sdk/0.1.0", (
                f"User-Agent mismatch: {headers.get('user-agent')}"
            )

        asyncio.run(test_headers())
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_concurrent_gather() -> bool:
    """Test concurrent gather."""
    print("Test 6: Concurrent gather (results in order)...", end=" ")
    try:
        async def gather_test() -> None:
            client = _BaseClient("test-key")

            async def coro1() -> str:
                return "a"

            async def coro2() -> str:
                return "b"

            results = await client._gather(coro1(), coro2())
            assert results == ["a", "b"], f"Results mismatch: {results}"

        asyncio.run(gather_test())
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def main() -> int:
    """Run all tests."""
    print("=" * 60)
    print("Task 3: _BaseClient Verification")
    print("=" * 60)

    results = [
        test_instantiation(),
        test_instantiation_with_client(),
        test_sync_context_manager(),
        test_async_context_manager(),
        test_header_injection(),
        test_concurrent_gather(),
    ]

    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
