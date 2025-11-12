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
preoccupied.pydantic.versioned
Namespace package segment providing version-aware helpers for Pydantic models.

:author: Christopher O'Brien <obriencj@preoccupied.net>
:license: GNU General Public License v3
:ai-assistant: GPT-5 Codex via Cursor
"""


from .discriminator import Discriminator, Match
from .registry import SelectorRegistry, MatchRegistry
from .selector import SelectorMeta, MatchSelector
from .semvermap import SemverMap
from .versioned import Version, VersionedRegistry, VersionedSelector


__all__ = (
    "Discriminator",
    "Match",

    "SelectorMeta",
    "SelectorRegistry",

    "MatchRegistry",
    "MatchSelector",

    "Version",
    "VersionedRegistry",
    "VersionedSelector",

    "SemverMap",
)


# The end.
