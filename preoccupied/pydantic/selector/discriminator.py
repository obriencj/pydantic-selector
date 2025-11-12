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
preoccupied.pydantic.selector.discriminator

Registration field markers for façade models and concrete subclasses.

Use the :func:`Discriminator` factory to create a discriminator field for a façade model.
Use the :func:`Match` factory to create a field for a concrete subclass.

Example:

```python
class Shape(MatchSelector):
    name: str = Discriminator()
    color: str = Field(default="black")

class Circle(Shape):
    name: str = Match("circle")
    radius: float

class Rectangle(Shape):
    name: str = Match("rectangle")
    width: float
    height: float
```

:author: Christopher O'Brien <obriencj@preoccupied.net>
:license: GNU General Public License v3
:ai-assistant: GPT-5 Codex via Cursor
"""


from dataclasses import dataclass
from typing import Any, Mapping, Optional, List

from pydantic import Field
from pydantic.fields import FieldInfo


__all__ = (
    "Discriminator",
    "DiscriminatorConfig",
    "Match",
    "MatchConfig",
)


@dataclass(frozen=True)
class DiscriminatorConfig:
    """
    Marker metadata identifying discriminator behaviour for a façade field.
    """

    allow_missing: bool
    default_value: Any
    metadata: Mapping[str, Any]


def Discriminator(  # noqa: N802 - factory function intentionally PascalCase
        default: Any = ...,
        *,
        allow_missing: bool = False,
        metadata: Optional[Mapping[str, Any]] = None,
        **field_kwargs: Any) -> FieldInfo:
    """
    Create a FieldInfo configured as the discriminator selector.
    """

    info = Field(default, **field_kwargs)

    if metadata is None:
        metadata = {}

    config = DiscriminatorConfig(
        allow_missing=allow_missing,
        default_value=default,
        metadata=metadata,
    )

    existing: List[Any] = list(info.metadata)
    existing.append(config)
    object.__setattr__(info, "metadata", existing)

    return info


@dataclass(frozen=True)
class MatchConfig:
    """
    Marker metadata identifying a concrete subclass selector value.
    """

    value: Any


def Match(value: Any) -> FieldInfo:  # noqa: N802 - PascalCase factory
    """
    Declare the selector value for a concrete subclass.
    """

    info = Field(default=value, init=False)
    metadata = list(info.metadata)
    metadata.append(MatchConfig(value=value))

    # annoying.
    object.__setattr__(info, "metadata", metadata)

    return info


# The end.
