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
preoccupied.pydantic.versioned.registry
Selector registry abstractions for facade-based selector models.

:author: Christopher O'Brien <obriencj@preoccupied.net>
:license: GNU General Public License v3
:ai-assistant: GPT-5 Codex via Cursor
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple, Type

from pydantic import BaseModel

__all__ = (
    "MatchRegistry",
    "SelectorRegistry",
)


_MISSING = object()


@dataclass(frozen=True)
class SelectorMatch:
    """
    Internal helper describing a registered selector entry.
    """

    value: Any
    subclass: Type[BaseModel]


class SelectorRegistry:
    """
    Base interface for selector registries used by selector façades.
    """

    def register(
            self,
            subclass: Type[BaseModel],
            *,
            value: Any) -> None:
        """
        Register a subclass for the provided selector value.
        """

        raise NotImplementedError

    def resolve(
            self,
            payload: Dict[str, Any],
            *,
            field: str,
            config: Any,
            facade: Type[BaseModel]) -> Tuple[Type[BaseModel], Dict[str, Any]]:
        """
        Resolve the payload to a registered subclass.
        """

        raise NotImplementedError


class MatchRegistry(SelectorRegistry):
    """
    Default registry that matches payload selector values exactly.
    """

    def __init__(self) -> None:
        self._entries: Dict[Any, SelectorMatch] = {}

    def register(
            self,
            subclass: Type[BaseModel],
            *,
            value: Any) -> None:
        if value in self._entries:
            existing = self._entries[value].subclass
            raise ValueError(
                f"Duplicate selector value '{value}' for {subclass.__name__}; "
                f"existing mapping points to {existing.__name__}."
            )
        self._entries[value] = SelectorMatch(value=value, subclass=subclass)

    def resolve(
            self,
            payload: Dict[str, Any],
            *,
            field: str,
            config: Any,
            facade: Type[BaseModel]) -> Tuple[Type[BaseModel], Dict[str, Any]]:
        value = payload.get(field, _MISSING)
        allow_missing = getattr(config, "allow_missing", False)
        default_value = getattr(config, "default_value", None)

        if value is _MISSING:
            if not allow_missing:
                raise ValueError(
                    f"{facade.__name__} requires discriminator field '{field}'."
                )
            value = default_value
            payload[field] = value

        match = self._entries.get(value)
        if match is None:
            raise ValueError(
                f"No discriminator match for value '{value}' on {facade.__name__}."
            )

        return match.subclass, payload
