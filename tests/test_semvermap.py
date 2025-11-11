# SPDX-License-Identifier: GPL-3.0-only

"""
tests.test_semvermap
Unit tests for the SemverMap convenience API.

:author: Christopher O'Brien <obriencj@preoccupied.net>
:license: GNU General Public License v3
:ai-assistant: GPT-5 Codex via Cursor
"""

from typing import Iterator

import pytest
from semver import Version

from preoccupied.pydantic.versioned.semvermap import SemverMap


@pytest.fixture
def sample_map() -> SemverMap[str]:
    """
    Provide a SemverMap populated with common versions.
    """

    mapping: SemverMap[str] = SemverMap()
    mapping.set("1.0.0", "alpha")
    mapping.set("1.2.0", "bravo")
    mapping.set("2.0.0", "charlie")
    return mapping


def test_set_and_get_exact_version(sample_map: SemverMap[str]) -> None:
    """
    Retrieving an exact version returns the associated value.
    """

    result = sample_map.get("1.2.0")
    assert result == "bravo"


def test_get_uses_default_value(sample_map: SemverMap[str]) -> None:
    """
    Missing selectors return the supplied default when provided.
    """

    result = sample_map.get("9.9.9", default="fallback")
    assert result == "fallback"


def test_get_missing_without_default_raises(sample_map: SemverMap[str]) -> None:
    """
    Missing selectors raise when no default is supplied.
    """

    with pytest.raises(ValueError):
        sample_map.get("9.9.9")


def test_get_with_policy_override(sample_map: SemverMap[str]) -> None:
    """
    Policy overrides support range lookups.
    """

    result = sample_map.get("1.1.5", policy="nearest_le")
    assert result == "alpha"


def test_dunder_getitem(sample_map: SemverMap[str]) -> None:
    """
    __getitem__ delegates to get for convenience access.
    """

    assert sample_map["1.0.0"] == "alpha"


def test_contains_checks_strings_and_versions(sample_map: SemverMap[str]) -> None:
    """
    __contains__ recognises both string selectors and Version instances.
    """

    assert "1.2.0" in sample_map
    assert Version.parse("2.0.0") in sample_map
    assert "0.1.0" not in sample_map


def test_versions_iterates_in_order(sample_map: SemverMap[str]) -> None:
    """
    versions() yields Version objects in ascending order.
    """

    versions: Iterator[Version] = sample_map.versions()
    assert list(versions) == [
        Version.parse("1.0.0"),
        Version.parse("1.2.0"),
        Version.parse("2.0.0"),
    ]


def test_earliest_and_latest(sample_map: SemverMap[str]) -> None:
    """
    earliest() and latest() expose the lowest and highest stored versions.
    """

    assert sample_map.earliest() == Version.parse("1.0.0")
    assert sample_map.latest() == Version.parse("2.0.0")


# The end.
