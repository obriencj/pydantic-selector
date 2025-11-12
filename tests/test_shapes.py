"""
tests.test_shapes
Demonstrate discriminator-driven model dispatch using Shape façade.

:author: Christopher O'Brien <obriencj@preoccupied.net>
:license: GNU General Public License v3
:ai-assistant: GPT-5 Codex via Cursor
"""


from types import SimpleNamespace

import pytest
from pydantic import Field

from preoccupied.pydantic.selector import (
    Discriminator, MatchSelector, Match)


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
def shapes_with_default_value():
    """
    Provide a namespace with allow-missing discriminator lacking a default.
    """

    class Shape(MatchSelector):
        """
        Façade that should fall back to itself when selector is omitted.
        """

        name: str = Discriminator(default="shape")
        color: str = Field(default="black")

    class Circle(Shape):
        """
        Circle-specific properties.
        """

        name: str = Match("circle")
        radius: float

    return SimpleNamespace(**locals())


def test_shape_allow_missing_without_default_returns_facade(shapes_with_default_value):
    """
    Missing selector with allow_missing but no default should return the façade.
    """

    payload = {"color": "silver"}
    instance = shapes_with_default_value.Shape.model_validate(payload)
    assert isinstance(instance, shapes_with_default_value.Shape)
    assert instance.color == "silver"


@pytest.fixture
def shapes_with_missing_value():
    """
    Provide a namespace containing Shape façade with default Blob fallback.
    """

    class Shape(MatchSelector):
        """
        Façade that falls back to Blob when selector is missing.
        """

        name: str = Discriminator(missing_value="blob")
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


def test_shape_missing_selector_uses_default_blob(shapes_with_missing_value):
    """
    When selector is missing, the façade returns the configured fallback class.
    """

    payload = {"color": "purple"}
    instance = shapes_with_missing_value.Shape.model_validate(payload)
    assert isinstance(instance, shapes_with_missing_value.Blob)
    assert instance.payload == "blob"
    assert instance.color == "purple"


def test_shape_explicit_blob_selector(shapes_with_missing_value):
    """
    Explicit blob selector resolves to Blob subclass.
    """

    payload = {"name": "blob", "payload": "goo"}
    instance = shapes_with_missing_value.Shape.model_validate(payload)
    assert isinstance(instance, shapes_with_missing_value.Blob)
    assert instance.payload == "goo"


@pytest.fixture
def shapes_with_mismatch_value():
    """
    Provide a namespace where unknown selectors fall back to Curiosity.
    """

    class Shape(MatchSelector):
        """
        Façade that defers mismatched selectors to Curiosity.
        """

        name: str = Discriminator(
            default="shape",
            mismatch_value="curiosity",
        )
        payload: str = Field(default="shape")

    class Circle(Shape):
        """
        Circle-specific properties.
        """

        name: str = Match("circle")
        payload: str = Field(default="circle")

    class Curiosity(Shape):
        """
        Fallback subclass used for mismatched selectors.
        """

        name: str = Match("curiosity")
        payload: str = Field(default="curiosity")

    return SimpleNamespace(**locals())


def test_shape_mismatch_selector_routes_to_curiosity(shapes_with_mismatch_value):
    """
    Unknown selectors resolve to the configured mismatch fallback subclass.
    """

    payload = {"name": "mars", "payload": "rover"}
    instance = shapes_with_mismatch_value.Shape.model_validate(payload)
    assert isinstance(instance, shapes_with_mismatch_value.Curiosity)

    # the current behavior intentionally keeps the payload value even though
    # we diverted to a different subclass. I *think* that's the best behavior,
    # but it's worth revisiting.
    assert instance.payload == "rover"


def test_shape_explicit_curiosity_selector(shapes_with_mismatch_value):
    """
    Explicit curiosity selector still resolves to Curiosity subclass.
    """

    payload = {"name": "curiosity", "payload": "science"}
    instance = shapes_with_mismatch_value.Shape.model_validate(payload)
    assert isinstance(instance, shapes_with_mismatch_value.Curiosity)
    assert instance.payload == "science"


# The end.
