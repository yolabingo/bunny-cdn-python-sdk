"""Tests for __version__."""

import importlib.metadata

import bunny_cdn_sdk


def test_version_matches_package_metadata() -> None:
    assert bunny_cdn_sdk.__version__ == importlib.metadata.version("bunny-cdn-sdk")
