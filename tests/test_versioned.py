"""
tests.test_versioned_selector
Tests for the semantic-version aware selector facade.

:author: Christopher O'Brien <obriencj@preoccupied.net>
:license: GNU General Public License v3
:ai-assistant: GPT-5 Codex via Cursor
"""

from types import SimpleNamespace

import pytest
from semver import Version

from preoccupied.pydantic.versioned import (
    Discriminator, Match, Version,
    VersionedSelector)


@pytest.fixture
def documents() -> SimpleNamespace:
    """
    Provide a namespace containing versioned document selectors and variants.
    """

    class Document(VersionedSelector):
        version: Version = Discriminator(default="1.0.0", allow_missing=True)
        payload: str

    class DocumentV1(Document):
        version: Version = Match("1.0.0")
        payload: str = "v1"

    class DocumentV2(Document):
        version: Version = Match("2.0.0")
        payload: str = "v2"

    return SimpleNamespace(**locals())


@pytest.mark.parametrize(
    "input_version, expected_cls, expected_payload",
    [
        ("1.0.0", "DocumentV1", "v1"),
        ("2.0.0", "DocumentV2", "v2"),
        ("2.1.5", "DocumentV2", "v2"),  # nearest lower version via default policy
    ],
)
def test_versioned_selector_resolves_nearest_lower(
        documents: SimpleNamespace,
        input_version: str,
        expected_cls: str,
        expected_payload: str) -> None:
    instance = documents.Document.model_validate({"version": input_version})
    expected_type = getattr(documents, expected_cls)
    assert isinstance(instance, expected_type)
    assert instance.payload == expected_payload


def test_versioned_selector_uses_default_when_missing(documents: SimpleNamespace) -> None:
    instance = documents.Document.model_validate({})
    assert isinstance(instance, documents.DocumentV1)
    assert instance.payload == "v1"


def test_versioned_selector_accepts_version_instance(documents: SimpleNamespace) -> None:
    version_obj = Version.parse("2.0.0")
    instance = documents.Document.model_validate({"version": version_obj})
    assert isinstance(instance, documents.DocumentV2)


def test_versioned_selector_raises_for_unmatched_selector(documents: SimpleNamespace) -> None:
    with pytest.raises(ValueError):
        documents.Document.model_validate({"version": "0.5.0"})


@pytest.fixture
def exact_documents() -> SimpleNamespace:
    """
    Provide a namespace containing versioned document selectors and variants.
    """

    class Document(VersionedSelector):
        __version_policy__ = "exact"

        version: Version = Discriminator(default="1.0.0", allow_missing=True)
        payload: str

    class DocumentV1(Document):
        version: Version = Match("1.0.0")
        payload: str = "v1"

    class DocumentV2(Document):
        version: Version = Match("2.0.0")
        payload: str = "v2"

    return SimpleNamespace(**locals())


def test_versioned_selector_exact_policy_requires_exact_match(
        exact_documents: SimpleNamespace) -> None:

    instance = exact_documents.Document.model_validate({"version": "2.0.0"})
    assert isinstance(instance, exact_documents.DocumentV2)

    with pytest.raises(ValueError):
        exact_documents.Document.model_validate({"version": "2.1.0"})


@pytest.fixture
def le_documents() -> SimpleNamespace:
    """
    Provide a namespace containing versioned document selectors and variants.
    """

    class Document(VersionedSelector):
        __version_policy__ = "le"

    class DocumentV1(Document):
        version: Version = Match("1.0.0")
        payload: str = "v1"

    class DocumentV2(Document):
        version: Version = Match("2.0.0")
        payload: str = "v2"

    return SimpleNamespace(**locals())



# The end.
