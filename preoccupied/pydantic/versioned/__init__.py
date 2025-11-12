# SPDX-License-Identifier: GPL-3.0-only

"""
preoccupied.pydantic.versioned
Namespace package segment providing version-aware helpers for Pydantic models.

:author: Christopher O'Brien <obriencj@preoccupied.net>
:license: GNU General Public License v3
:ai-assistant: GPT-5 Codex via Cursor
"""

__version__ = "0.1.0"


from .discriminator import Discriminator, Match
from .registry import SelectorRegistry, MatchRegistry
from .selector import SelectorMeta, MatchSelector


__all__ = (
    "Discriminator",
    "Match",
    "SelectorRegistry",
    "MatchRegistry",
    "SelectorMeta",
    "MatchSelector",
)


# The end.
