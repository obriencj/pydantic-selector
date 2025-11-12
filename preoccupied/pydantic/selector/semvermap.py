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
preoccupied.pydantic.selector.semvermap

Utility class, providing a mapping of semantic versions to values with
policy-driven selection.

Use the :class:`SemverMap` class to create a mapping of semantic versions to
values.

Example:

```python
mapping = SemverMap()
mapping.set("1.0.0", "alpha")
mapping.set("1.2.0", "bravo")
mapping.set("2.0.0", "charlie")

result = mapping.get("1.2.0")
assert result == "bravo"

result = mapping.get("1.1.5", policy="nearest_le")
assert result == "alpha"
```

:author: Christopher O'Brien <obriencj@preoccupied.net>
:license: GNU General Public License v3
:ai-assistant: GPT-5 Codex via Cursor
"""


import re
from typing import (Dict, Generic, Iterator, List, Mapping, Optional,
                    Protocol, Sequence, Tuple, TypeVar, Union)

from semver import Version


class _Sentinel:
    """
    Internal sentinel marker for unset defaults.
    """


_MISSING = _Sentinel()


matcher_like = re.compile(r"^[<>=]=?").match


class ResolutionPolicy(Protocol):
    """
    Protocol describing resolution behaviour for semantic-version selectors.
    """

    def resolve(
            self,
            selector: str,
            available: Sequence[Version]) -> str:
        """
        Return the selected version string given a selector and available keys.

        :param selector: The selector to resolve.
        :param available: The available versions to resolve from.
        :return: The selected version string.
        """

        ...


class ResolveVersionLE(ResolutionPolicy):
    """
    Resolve selectors toward the greatest available version not exceeding the request.
    """

    def resolve(
            self,
            selector: str,
            available: Sequence[Version]) -> Optional[Version]:
        """
        Return the highest version that satisfies the selector while remaining
        less than or equal to the requested version.

        Range-like selectors (containing semicolon-delimited match expressions
        such as ``<=1.2.0;>=1.0.0``) are applied against each version in
        ascending order until all constraints succeed. Non-range selectors are
        treated as a single ``<=`` comparison evaluated from the highest
        available version downward.
        """

        if matcher_like(selector):
            matchers = selector.split(";")
            for version in available:
                for matcher in matchers:
                    if not version.match(matcher):
                        break
                else:
                    return version

        else:
            matcher = f"<={selector.strip()}"
            for version in reversed(available):
                if version.match(matcher):
                    return version

        return None


class ResolveVersionGE(ResolutionPolicy):
    """
    Resolve selectors toward the smallest available version not less than the request.
    """

    def resolve(
            self,
            selector: str,
            available: Sequence[Version]) -> Optional[Version]:
        """
        Return the lowest version that satisfies the selector while remaining
        greater than or equal to the requested version.

        Range-like selectors are evaluated by scanning the available versions in
        descending order until every constraint succeeds. Non-range selectors are
        interpreted as a single ``>=`` comparison evaluated from the lowest
        available version upward.
        """

        if matcher_like(selector):
            matchers = selector.split(";")
            for version in reversed(available):
                for matcher in matchers:
                    if not version.match(matcher):
                        break
                else:
                    return version

        else:
            matcher = f">={selector.strip()}"
            for version in available:
                if version.match(matcher):
                    return version

        return None


class ResolveVersionExact(ResolutionPolicy):
    """
    Resolve selectors that demand exact matches or bounded ranges.
    """

    def resolve(
            self,
            selector: str,
            available: Sequence[Version]) -> Optional[Version]:
        """
        Return the version that satisfies all selector constraints, whether an
        exact identifier or a semicolon-delimited set of match expressions.

        Range-like selectors are evaluated from highest to lowest version so the
        most recent satisfying entry wins. Non-range selectors are interpreted
        as a single equality comparison.
        """

        if matcher_like(selector):
            matchers = selector.split(";")
            for version in reversed(available):
                for matcher in matchers:
                    if not version.match(matcher):
                        break
                else:
                    return version

        else:
            matcher = f"=={selector.strip()}"
            for version in available:
                if version.match(matcher):
                    return version

        return None


def lookup_policy(policy: str) -> Optional[ResolutionPolicy]:
    if policy in ("nearest_le", "le"):
        return ResolveVersionLE()
    elif policy in ("nearest_ge", "ge"):
        return ResolveVersionGE()
    elif policy in ("exact", "eq"):
        return ResolveVersionExact()
    else:
        return None


V = TypeVar("V")


class SemverMap(Generic[V]):
    """
    Mapping that stores versioned values and resolves selectors via policies.
    """

    def __init__(
            self,
            *,
            default_policy: Union[str, ResolutionPolicy, None] = None) -> None:

        self._default_policy = lookup_policy(default_policy) or ResolveVersionExact()

        # map of Version to value
        self._entries: Dict[Version, V] = {}

        # sorted list of Versions from _entries.keys()
        self._versions: List[Version] = []

        # cache of selector str to Version, bypassing the resolver
        self._cache: Dict[str, Version] = {}


    def resolver(
            self,
            policy: Union[str, ResolutionPolicy, None] = None) -> ResolutionPolicy:
        """
        Return the resolver for the given policy.
        """

        if policy is None:
            return self._default_policy
        elif isinstance(policy, str):
            policy = lookup_policy(policy)
            if policy is None:
                raise ValueError(f"Invalid policy: {policy}")
        return policy


    def set(self, version: Union[str, Version], value: V) -> None:
        """
        Associate `value` with `version`.
        """

        if isinstance(version, str):
            version = Version.parse(version)

        if version in self._entries:
            self._entries[version] = value

        else:
            # adding a new version means we need to clear the cache and re-sort the
            # versions list
            self._cache.clear()
            self._entries[version] = value
            self._versions = sorted(self._entries.keys())


    def get(self,
            selector: str | None = None,
            default: Union[V, _Sentinel] = _MISSING,
            *,
            policy: Union[str, ResolutionPolicy, None] = None) -> V:
        """
        Retrieve the value for `selector` using the provided `policy`. Selector
        may be a string representing a version (eg. "1.0"), a match (eg.
        ">=1.0"), or a range (eg. ">=1.0;<2.0"). If no selector is provided, the
        default policy will be used. If the selector is not found, the default
        value will be returned. If the default value is not provided, a
        ValueError will be raised.

        :param selector: The selector to retrieve the value for.
        :param policy: The policy to use to resolve the selector.
        :param default: The default value to return if the selector is not found.
        :return: The value for the selector.
        """

        if policy is None:
            if selector in self._cache:
                version = self._cache[selector]
            else:
                resolver = self.resolver()
                version = resolver.resolve(selector, self._versions)
                self._cache[selector] = version
        else:
            # when a policy is provided, we bypass the cache
            resolver = self.resolver(policy)
            version = resolver.resolve(selector, self._versions)

        if version is None or version not in self._entries:
            if default is _MISSING:
                raise ValueError(f"No version matching {selector}")
            return default
        return self._entries[version]


    def __getitem__(self, selector: str) -> V:
        """
        Return the value for the given selector.
        """

        return self.get(selector)


    def __setitem__(self, selector: str, value: V) -> None:
        """
        Set the value for the given selector.
        """

        self.set(selector, value)


    def __delitem__(self, selector: str) -> None:
        """
        Delete the value for the given selector.
        """

        self.delete(selector)


    def __contains__(self, selector: Union[str, Version]) -> bool:
        """
        Return True if the given selector is stored.
        """

        if isinstance(selector, str):
            if selector in self._cache:
                return True
            else:
                resolver = self.resolver()
                version = resolver.resolve(selector, self._versions)
                return version is not None and version in self._entries

        elif isinstance(selector, Version):
            return selector in self._entries

        return False


    def items(self) -> Iterator[Tuple[Version, V]]:
        """
        Return an iterator over the stored versions and values in ascending semantic order.
        """

        return self._entries.items()


    def values(self) -> Iterator[V]:
        """
        Return an iterator over the stored values in ascending semantic order.
        """

        return self._entries.values()


    def versions(self) -> Iterator[Version]:
        """
        Return an iterator over the stored versions in ascending semantic order.
        """

        return self._entries.keys()


    def earliest(self) -> Optional[Version]:
        """
        Return the earliest (lowest) stored version.
        """

        return self._versions[0] if self._versions else None


    def latest(self) -> Optional[Version]:
        """
        Return the latest (highest) stored version.
        """

        return self._versions[-1] if self._versions else None


    def update(self, other: Mapping[Union[str, Version], V]) -> None:
        """
        Update the map with the values from another map.
        """

        for version, value in other.items():
            self.set(version, value)


# The end.
