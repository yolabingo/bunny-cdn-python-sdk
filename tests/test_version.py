"""Tests for __version__ attribute via importlib.metadata."""

import importlib.metadata

import bunny_cdn_sdk


def test_version_attribute_exists() -> None:
    """__version__ must be defined on the package."""
    assert hasattr(bunny_cdn_sdk, "__version__"), "__version__ not found on bunny_cdn_sdk"


def test_version_is_non_empty_string() -> None:
    """__version__ must be a non-empty string."""
    version = bunny_cdn_sdk.__version__
    assert isinstance(version, str), f"__version__ is not a str: {type(version)}"
    assert version, f"__version__ is empty: {version!r}"


def test_version_matches_pyproject() -> None:
    """__version__ must match the installed package metadata (pyproject.toml version)."""
    expected = importlib.metadata.version("bunny-cdn-sdk")
    assert bunny_cdn_sdk.__version__ == expected, (
        f"__version__ {bunny_cdn_sdk.__version__!r} != metadata version {expected!r}"
    )


def test_version_in_all() -> None:
    """__version__ must be in __all__."""
    assert "__version__" in bunny_cdn_sdk.__all__, "__version__ not in __all__"


def test_no_bare_version_literal() -> None:
    """__init__.py must not contain a hardcoded __version__ = '...' string literal."""
    import pathlib
    init_path = pathlib.Path(__file__).parent.parent / "src" / "bunny_cdn_sdk" / "__init__.py"
    source = init_path.read_text()
    # Check that there's no direct string assignment like __version__ = "x.y.z"
    import re
    bare_assignment = re.search(r'__version__\s*=\s*["\']', source)
    assert bare_assignment is None, (
        f"Found bare __version__ string literal in __init__.py at position {bare_assignment.start()}"
    )
