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
preoccupied.pydantic.selector.registry
Selector registry abstractions for facade-based selector models.

:author: Christopher O'Brien <obriencj@preoccupied.net>
:license: GNU General Public License v3
:ai-assistant: GPT-5 Codex via Cursor
"""


from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Type

from pydantic import BaseModel

from .discriminator import DiscriminatorConfig, MatchConfig


__all__ = (
    "MatchRegistry",
    "SelectorRegistry",
)


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

    def __init__(self, facade: Type[BaseModel]) -> None:
        self.facade = facade


    def register(self, subclass: Type[BaseModel]) -> None:
        """
        Register a subclass under this registry.
        """

        raise NotImplementedError


    def normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize the payload to the expected format for the selector.
        """

        # TODO: the preselect_normalize method isn't documented anywhere
        # at all. whoops.
        if hasattr(self.facade, "preselect_normalize"):
            payload = self.facade.preselect_normalize(payload)
        return dict(payload)


    def resolve(self, payload: Dict[str, Any]) -> Type[BaseModel]:
        """
        Resolve normalized payload to a registered subclass.
        """

        raise NotImplementedError


class MatchRegistry(SelectorRegistry):
    """
    Default registry that matches payload selector values exactly.
    """

    def __init__(self, facade: Type[BaseModel]) -> None:
        super().__init__(facade)
        self._entries: Dict[Any, SelectorMatch] = {}

        found = self.discover_discriminators()
        if len(found) != 1:
            raise ValueError(
                f"{self.facade.__name__} must declare exactly one Discriminator field."
            )
        self.discriminator_field, self.discriminator_config = found[0]


    def discover_discriminators(self) -> List[Tuple[str, DiscriminatorConfig]]:
        found = []
        for name, field_info in self.facade.model_fields.items():
            for item in field_info.metadata:
                if isinstance(item, DiscriminatorConfig):
                    found.append((name, item))
        return found


    def register(self, subclass: Type[BaseModel]) -> None:
        found = self.discover_matches(subclass)
        if len(found) != 1:
            raise ValueError(
                f"{subclass.__name__} must declare exactly one Match field."
            )

        value = found[0][1].value
        if value in self._entries:
            existing = self._entries[value].subclass
            raise ValueError(
                f"Duplicate selector value '{value}' for {subclass.__name__}; "
                f"existing mapping points to {existing.__name__}."
            )
        self._entries[value] = SelectorMatch(value=value, subclass=subclass)


    def discover_matches(
        self,
        subclass: Type[BaseModel]) -> List[Tuple[str, MatchConfig]]:

        found = []
        for name, field_info in subclass.model_fields.items():
            for item in field_info.metadata:
                if isinstance(item, MatchConfig):
                    found.append((name, item))
        return found


    def normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize the payload to the expected format for the selector.
        """

        payload = super().normalize(payload)

        field = self.discriminator_field
        assert field is not None

        config = self.discriminator_config

        if field not in payload:
            if not config.allow_missing:
                raise ValueError(
                    f"{self.facade.__name__} requires discriminator field '{field}'."
                )
            payload[field] = config.default_value

        return payload


    def resolve(self, payload: Dict[str, Any]) -> Type[BaseModel]:

        # TODO: we could have a few different behaviors here for odd situations,
        # like if allow_missing is True, but there's no default value... should we
        # instantiate the facade as a fallback?
        field = self.discriminator_field
        assert field is not None

        # we should have caught this in normalize, what went wrong?
        assert field in payload
        value = payload[field]

        if value is ...:
            return self.facade

        match = self._entries.get(value)
        if match is None:
            raise ValueError(
                f"No discriminator match for value '{value}' on {self.facade.__name__}."
            )
        return match.subclass


# The end.
