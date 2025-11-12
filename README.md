# preoccupied.pydantic-selector

Dynamic selector utilities for [Pydantic](https://docs.pydantic.dev/) 2.x models. The package supplies façade base classes that dispatch validation to registered subclasses, plus semantic-version helpers for version-aware model families.


## Key Features

- Discriminator-driven façades built on top of `MatchSelector`, using declarative `Discriminator` and `Match` field helpers.
- Automatic subclass registration and dispatch at validation or instantiation time.
- Semantic-version aware selectors via `VersionedSelector`, powered by a reusable `SemverMap`.
- Policy-driven version resolution supporting `exact`, `nearest_ge`, and `nearest_le` strategies.
- Tested examples covering default fallbacks, duplicate protection, and custom selector behaviour.


## Installation

```shell
python -m pip install preoccupied.pydantic-selector
```

Requires:

- Python 3.8+
- [Pydantic](https://docs.pydantic.dev/)>=2
- [semver](https://python-semver.readthedocs.io/en/latest/)>=3


## Quick Start

### Match-Based Facades

```python
from pydantic import BaseModel, Field
from preoccupied.pydantic.selector import Discriminator, Match, MatchSelector


class Shape(MatchSelector):
    name: str = Discriminator(description="Selects the concrete shape model.")
    color: str = Field(default="black")


class Circle(Shape):
    name: str = Match("circle")
    radius: float


class Rectangle(Shape):
    name: str = Match("rectangle")
    width: float
    height: float


payload = {"name": "circle", "radius": 2.5}
shape = Shape.model_validate(payload)
assert isinstance(shape, Circle)
```


### Versioned Selectors

```python
from preoccupied.pydantic.selector import (
    Discriminator,
    Match,
    Version,
    VersionedSelector,
)


class Document(VersionedSelector):
    version: Version = Discriminator(default="1.0.0", allow_missing=True)
    payload: str


class DocumentV1(Document):
    version: Version = Match("1.0.0")
    payload: str = "v1"


class DocumentV2(Document):
    version: Version = Match("2.0.0")
    payload: str = "v2"


doc = Document.model_validate({"version": "2.0.0"})
assert isinstance(doc, DocumentV2)

fallback = Document.model_validate({})
assert isinstance(fallback, DocumentV1)
```

By default `VersionedSelector` resolves to the nearest lower registered version. Override `__version_policy__` with `'exact'`, `'nearest_le'` (or `'le'`), or `'nearest_ge'` (or `'ge'`) to change the selection strategy.


## Development

Set up a virtual environment with the runtime dependencies, then install the project in editable mode:

```shell
python -m pip install -e .
```

Run the automated test suite with `tox`:

```shell
tox
```


## Contact & License

**Author**: Christopher O'Brien <obriencj@gmail.com>

**Repository**: https://github.com/obriencj/pydantic-selector

**AI Assistance**: This project was developed with assistance from
[GPT-5 Codex] via [Cursor IDE](https://cursor.com). See [VIBE.md](VIBE.md) for additional details.

**License**: GNU General Public License v3 or later. See
<https://www.gnu.org/licenses/> for details.
