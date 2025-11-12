"""
tests.test_shapes
Demonstrate discriminator-driven model dispatch using Shape façade.

:author: Christopher O'Brien <obriencj@preoccupied.net>
:license: GNU General Public License v3
:ai-assistant: GPT-5 Codex via Cursor
"""


from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import Field

from preoccupied.pydantic.versioned import Discriminator, MatchSelector, Match


@pytest.fixture
def shapes():
    """
    Provide a namespace containing Shape façade and concrete subclasses.
    """

    class Shape(MatchSelector):
        """
        Façade capturing shared shape attributes and discriminator selector.
        """

        name: str = Discriminator(
            description="Identifier selecting the concrete shape model.",
        )
        color: str = Field(default="black")

    class Circle(Shape):
        """
        Circle-specific properties.
        """

        name: str = Match("circle")
        radius: float

    class Triangle(Shape):
        """
        Triangle-specific properties.
        """

        name: str = Match("triangle")
        base: float
        height: float

    class Rectangle(Shape):
        """
        Rectangle-specific properties.
        """

        name: str = Match("rectangle")
        width: float
        height: float

    class Square(Rectangle):
        """
        Square-specific properties.
        """

        name: str = Match("square")
        side: float
        width: float = Field(init=False, frozen=True, default=None)
        height: float = Field(init=False, frozen=True, default=None)

        def model_post_init(self, __context) -> None:
            super().model_post_init(__context)
            object.__setattr__(self, "width", self.side)
            object.__setattr__(self, "height", self.side)

    return SimpleNamespace(**locals())


@pytest.fixture
def shapes_allow_missing_facade():
    """
    Provide a namespace with allow-missing discriminator lacking a default.
    """

    class Shape(MatchSelector):
        """
        Façade that should fall back to itself when selector is omitted.
        """

        name: str = Discriminator(allow_missing=True)
        color: str = Field(default="black")

    class Circle(Shape):
        """
        Circle-specific properties.
        """

        name: str = Match("circle")
        radius: float

    return SimpleNamespace(**locals())


def test_shape_model_validate_returns_concrete_subclass(shapes):
    """
    The façade dispatches validation to the target subclass.
    """

    payload = {"name": "circle", "radius": 2.5, "color": "blue"}
    instance = shapes.Shape.model_validate(payload)
    assert isinstance(instance, shapes.Circle)
    assert instance.radius == 2.5
    assert instance.color == "blue"


def test_shape_instantiation_creates_concrete_instance(shapes):
    """
    Instantiating the façade yields the appropriate subclass instance.
    """

    instance = shapes.Shape(name="triangle", base=3.0, height=4.0, color="green")
    assert isinstance(instance, shapes.Triangle)
    assert instance.base == 3.0
    assert instance.height == 4.0


# TODO: haven't decided on this yet
# def test_shape_allow_missing_without_default_returns_facade(shapes_allow_missing_facade):
#     """
#     Missing selector with allow_missing but no default should return the façade.
#     """

#     payload = {"color": "silver"}
#     instance = shapes_allow_missing_facade.Shape.model_validate(payload)
#     assert isinstance(instance, shapes_allow_missing_facade.Shape)
#     assert instance.color == "silver"


def test_shape_requires_single_discriminator():
    """
    Facade definitions must declare exactly one discriminator field.
    """

    with pytest.raises(ValueError) as error:
        class FacadeWithoutDiscriminator(MatchSelector):
            """
            Facade lacking discriminator; registration should fail.
            """

            color: str = Field(default="black")

        FacadeWithoutDiscriminator  # pragma: no cover

    assert "must declare exactly one Discriminator field" in str(error.value)


def test_shape_rejects_multiple_discriminators():
    """
    Facade definitions cannot declare more than one discriminator field.
    """

    with pytest.raises(ValueError) as error:
        class FacadeWithMultipleDiscriminators(MatchSelector):
            """
            Facade declaring two discriminators; registration should fail.
            """

            primary: str = Discriminator()
            secondary: str = Discriminator()

        FacadeWithMultipleDiscriminators  # pragma: no cover

    assert "must declare exactly one Discriminator field" in str(error.value)


def test_shape_missing_selector_raises(shapes):
    """
    Omitted selector fails validation by default.
    """

    payload = {"radius": 1.0}
    try:
        shapes.Shape.model_validate(payload)
    except ValueError as error:
        assert "requires discriminator field" in str(error)
    else:
        raise AssertionError("Expected ValueError for missing selector")


def test_shape_unknown_selector_raises(shapes):
    """
    Unknown selectors surface clear resolution errors.
    """

    payload = {"name": "pentagon", "side": 2.0}
    try:
        shapes.Shape.model_validate(payload)
    except ValueError as error:
        assert "No discriminator match" in str(error)
    else:
        raise AssertionError("Expected ValueError for unknown selector")


def test_shape_rectangle_resolution(shapes):
    """
    Rectangle selector routes to Rectangle subclass and preserves dimensions.
    """

    payload = {"name": "rectangle", "width": 6.0, "height": 2.0}
    instance = shapes.Shape.model_validate(payload)
    assert isinstance(instance, shapes.Rectangle)
    assert instance.width == 6.0
    assert instance.height == 2.0


def test_shape_square_resolution(shapes):
    """
    Square selector routes to Square subclass and maps side to width/height.
    """

    payload = {"name": "square", "side": 4.0, "color": "orange"}
    instance = shapes.Shape.model_validate(payload)
    assert isinstance(instance, shapes.Square)
    assert instance.side == 4.0
    assert instance.color == "orange"
    assert instance.width == 4.0
    assert instance.height == 4.0


@pytest.fixture
def shapes_with_default():
    """
    Provide a namespace containing Shape façade with default Blob fallback.
    """

    class Shape(MatchSelector):
        """
        Façade that falls back to Blob when selector is missing.
        """

        name: str = Discriminator(default="blob", allow_missing=True)
        color: str = Field(default="black")

    class Circle(Shape):
        """
        Circle-specific properties.
        """

        name: str = Match("circle")
        radius: float

    class Triangle(Shape):
        """
        Triangle-specific properties.
        """

        name: str = Match("triangle")
        base: float
        height: float

    class Rectangle(Shape):
        """
        Rectangle-specific properties.
        """

        name: str = Match("rectangle")
        width: float
        height: float

    class Square(Rectangle):
        """
        Square-specific properties.
        """

        name: str = Match("square")
        side: float
        width: float = Field(init=False, frozen=True, default=None)
        height: float = Field(init=False, frozen=True, default=None)

        def model_post_init(self, __context) -> None:
            super().model_post_init(__context)
            object.__setattr__(self, "width", self.side)
            object.__setattr__(self, "height", self.side)

    class Blob(Shape):
        """
        Default blob shape used when no selector is provided.
        """

        name: str = Match("blob")
        payload: str = Field(default="blob")

    return SimpleNamespace(**locals())


def test_shape_missing_selector_uses_default_blob(shapes_with_default):
    """
    When selector is missing, the façade returns the configured fallback class.
    """

    payload = {"color": "purple"}
    instance = shapes_with_default.Shape.model_validate(payload)
    assert isinstance(instance, shapes_with_default.Blob)
    assert instance.payload == "blob"
    assert instance.color == "purple"


def test_shape_explicit_blob_selector(shapes_with_default):
    """
    Explicit blob selector resolves to Blob subclass.
    """

    payload = {"name": "blob", "payload": "goo"}
    instance = shapes_with_default.Shape.model_validate(payload)
    assert isinstance(instance, shapes_with_default.Blob)
    assert instance.payload == "goo"


def test_shape_subclass_requires_single_match():
    """
    Subclasses must provide exactly one match selector override.
    """

    class Shape(MatchSelector):
        """
        Façade declaring a discriminator for testing.
        """

        name: str = Discriminator()

    with pytest.raises(ValueError) as error:
        class NoMatchShape(Shape):
            """
            Subclass failing to provide match configuration.
            """

            pass

        NoMatchShape  # pragma: no cover

    assert "must declare exactly one Match field" in str(error.value)


def test_shape_subclass_rejects_multiple_matches():
    """
    Subclasses cannot declare more than one match selector.
    """

    class Shape(MatchSelector):
        """
        Façade declaring a discriminator for testing.
        """

        name: str = Discriminator()

    with pytest.raises(ValueError) as error:
        class MultiMatchShape(Shape):
            """
            Subclass declaring multiple match configurations.
            """

            name: str = Match("polygon")
            alias: str = Match("poly")

        MultiMatchShape  # pragma: no cover

    assert "must declare exactly one Match field" in str(error.value)


def test_shape_duplicate_match_values_disallowed():
    """
    Duplicate match values across subclasses must raise errors.
    """

    class Shape(MatchSelector):
        """
        Façade declaring a discriminator for testing.
        """

        name: str = Discriminator()

    class FirstShape(Shape):
        """
        Subclass registering initial match value.
        """

        name: str = Match("duplicate")

    with pytest.raises(ValueError) as error:
        class DuplicateShape(Shape):
            """
            Subclass reusing existing match value.
            """

            name: str = Match("duplicate")

        DuplicateShape  # pragma: no cover

    assert "Duplicate selector value" in str(error.value)


# The end.
