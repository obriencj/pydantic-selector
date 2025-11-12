# SPDX-License-Identifier: GPL-3.0-only

"""
tests.test_policies
Unit tests covering resolution policy helpers.

:author: Christopher O'Brien <obriencj@preoccupied.net>
:license: GNU General Public License v3
:ai-assistant: GPT-5 Codex via Cursor
"""


import pytest
from semver import Version

from preoccupied.pydantic.versioned.semvermap import (
    ResolveVersionExact,
    ResolveVersionGE,
    ResolveVersionLE)


@pytest.fixture
def version_sequence():
    """
    Provide an ordered list of semantic versions for policy evaluation.
    """

    return [
        Version.parse("1.0.0"),
        Version.parse("1.1.0"),
        Version.parse("1.2.0"),
        Version.parse("2.0.0")
    ]


@pytest.mark.parametrize(
    "selector, expected, note",
    [
        ("1.1.0", Version.parse("1.1.0"), "exact match"),
        ("1.1.5", Version.parse("1.1.0"), "nearest lower version"),
        ("0.9.9", None, "no candidate less than selector"),
        (">1.1.0", Version.parse("1.2.0"), "greater-than selector"),
        ("<1.2.0", Version.parse("1.0.0"), "less-than selector"),
        ("==1.1.0", Version.parse("1.1.0"), "equal-to selector"),
        (">=1.1.0;<2.0.0", Version.parse("1.1.0"), "range selector"),
    ],
)
def test_resolve_version_le(
        version_sequence,
        selector,
        expected,
        note):
    """
    ResolveVersionLE scenarios for exact, range, and inequality selectors.
    """

    resolver = ResolveVersionLE()
    result = resolver.resolve(selector, version_sequence)
    assert result == expected, note


@pytest.mark.parametrize(
    "selector, expected, note",
    [
        ("1.2.0", Version.parse("1.2.0"), "exact match"),
        ("1.1.5", Version.parse("1.2.0"), "nearest higher version"),
        ("3.0.0", None, "no candidate greater than selector"),
        (">1.1.0", Version.parse("2.0.0"), "greater-than selector"),
        ("<1.2.0", Version.parse("1.1.0"), "less-than selector"),
        ("==1.1.0", Version.parse("1.1.0"), "equal-to selector"),
        (">=1.0.0;<2.0.0", Version.parse("1.2.0"), "range selector"),
    ],
)
def test_resolve_version_ge(
        version_sequence,
        selector,
        expected,
        note):
    """
    ResolveVersionGE scenarios for exact, range, and inequality selectors.
    """

    resolver = ResolveVersionGE()
    result = resolver.resolve(selector, version_sequence)
    assert result == expected, note


@pytest.mark.parametrize(
    "selector, expected, note",
    [
        ("2.0.0", Version.parse("2.0.0"), "exact match"),
        ("1.1.5", None, "selector between versions"),
        (">=1.0.0;<2.0.0", Version.parse("1.2.0"), "range selector"),
        (">=3.0.0;<4.0.0", None, "range selector without candidates"),
    ],
)
def test_resolve_version_exact(
        version_sequence,
        selector,
        expected,
        note):
    """
    ResolveVersionExact scenarios covering exact and range selectors.
    """

    resolver = ResolveVersionExact()
    result = resolver.resolve(selector, version_sequence)
    assert result == expected, note


# The end.
