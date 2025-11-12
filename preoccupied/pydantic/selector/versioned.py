# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, see <http://www.gnu.org/licenses/>.

"""
preoccupied.pydantic.selector.versioned

A façade selector model for Pydantic that resolves versioned subclasses using an
internal :class:`SemverMap`.

Example:

```python
class Thing(VersionedSelector):
    version: Version = Discriminator(default="1.0.0", allow_missing=True)
    payload: str

class Thing_v1(Thing):
    version: Version = Match("1.0.0")
    payload: str = "v1"

class Thing_v1_5(Thing):
    version: Version = Match("1.5.0")
    payload: str = "v1.5"

class Thing_v2(Thing):
    version: Version = Match("2.0.0")
    payload: str = "v2"

thing = Thing.model_validate({"version": "1.2.0"})
assert thing.payload == "v1"

thing = Thing.model_validate({"version": "1.5.1"})
assert thing.payload == "v1.5"

thing = Thing.model_validate({"version": "2.0.0"})
assert thing.payload == "v2"
```

:author: Christopher O'Brien <obriencj@preoccupied.net>
:license: GNU General Public License v3
:ai-assistant: GPT-5 Codex via Cursor
"""

from typing import Any, Optional, Type

from semver import Version as SemVersion

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

from .registry import MatchRegistry
from .selector import MatchSelector
from .semvermap import SemverMap


__all__ = (
    "Version",
    "VersionedRegistry",
    "VersionedSelector",
)


def _ensure_version(value: Any) -> SemVersion:
    """
    Convert supported inputs into a ``semver.Version`` instance.
    """

    if isinstance(value, SemVersion):
        return value
    if isinstance(value, str):
        return SemVersion.parse(value)
    raise TypeError(f"Unsupported version value: {value!r}")


class Version(SemVersion):
    """
    Pydantic-compatible wrapper validating semantic version values.
    """

    @classmethod
    def _validate(cls, value: Any) -> SemVersion:
        return _ensure_version(value)


    @classmethod
    def __get_pydantic_core_schema__(
            cls,
            source_type: Any,
            handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda value: str(value),
                return_schema=core_schema.str_schema(),
            ),
        )


    @classmethod
    def __get_pydantic_json_schema__(
            cls,
            core_schema_: core_schema.CoreSchema,
            handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        json_schema = handler(core_schema_)
        json_schema.update({"type": "string", "format": "semver"})
        return json_schema


class VersionedRegistry(MatchRegistry):
    """
    Registry that resolves selectors using :class:`SemverMap`.
    """

    def __init__(self, facade: Type[MatchSelector]) -> None:
        super().__init__(facade)
        policy = getattr(facade, "__version_policy__", "le")
        self._semver = SemverMap(default_policy=policy)


    def register(self, subclass: Type[MatchSelector]) -> None:
        matches = self.discover_matches(subclass)
        if len(matches) != 1:
            raise ValueError(
                f"{subclass.__name__} must declare exactly one Match field."
            )
        value = matches[0][1].value
        version = _ensure_version(value)
        super().register(subclass)
        self._semver.set(version, subclass)


    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = super().normalize(payload)
        field = getattr(self, "discriminator_field", None)
        if field is None:
            return payload
        if field not in payload:
            return payload
        value = payload[field]
        if value is ...:
            return payload
        payload[field] = str(_ensure_version(value))
        return payload


    def resolve(self, payload: dict[str, Any]) -> Type[MatchSelector]:
        field = getattr(self, "discriminator_field", None)
        if field is None or field not in payload:
            return self.facade
        selector = payload[field]
        if selector is ...:
            return self.facade
        return self._semver.get(str(selector))


class VersionedSelector(MatchSelector):
    """
    Selector façade that resolves versioned subclasses using ``SemverMap``.
    """

    __selector_registry_cls__ = VersionedRegistry
    __version_policy__: Optional[str] = "le"


# The end.
