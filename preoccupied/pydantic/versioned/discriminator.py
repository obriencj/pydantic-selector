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
preoccupied.pydantic.versioned.discriminator
Dynamic discriminator helpers and registration-aware base model primitives.

:author: Christopher O'Brien <obriencj@preoccupied.net>
:license: GNU General Public License v3
:ai-assistant: GPT-5 Codex via Cursor
"""


from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Type
from typing_extensions import TypeAlias

from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from .registry import MatchRegistry, SelectorRegistry


__all__ = (
    "Discriminator",
    "DiscriminatorFieldConfig",
    "Match",
    "MatchConfig",
    "SelectorMeta",
    "SimpleSelector",
)


_MISSING = object()


@dataclass(frozen=True)
class DiscriminatorFieldConfig:
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

    config = DiscriminatorFieldConfig(
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
    object.__setattr__(info, "metadata", metadata)
    return info


class SelectorMeta(type(BaseModel)):
    """
    Metaclass responsible for discriminator-aware model registration.
    """

    def __call__(cls, *args: Any, **kwargs: Any) -> Type[BaseModel]:
        """
        Route façade instantiation through validation to return concrete subclasses.
        """

        root = getattr(cls, "__selector_root__", cls)
        if root is cls:
            if args and kwargs:
                raise TypeError(
                    "Mixing positional and keyword arguments is not"
                    " supported for façades."
                )
            if kwargs:
                payload: Any = dict(kwargs)
            elif len(args) == 1:
                payload = args[0]
            elif not args:
                payload = {}
            else:
                raise TypeError("Unexpected positional arguments for façade instantiation.")
            return cls.model_validate(payload)
        return super().__call__(*args, **kwargs)


    def __new__(  # type: ignore[override]
            mcls,
            name: str,
            bases: Tuple[type, ...],
            namespace: Dict[str, Any],
            **kwargs: Any) -> Type[BaseModel]:

        if "selector" in kwargs:
            raise TypeError(
                "Selector subclasses must declare selector metadata using Match(...); "
                "the 'selector=' keyword is no longer supported."
            )

        selector_value = _MISSING

        model_cls = super().__new__(mcls, name, bases, namespace, **kwargs)

        if model_cls.__dict__.get("__selector_registry_cls__", None) is not None:
            # This is a new selector base class, so we'll just set that up.
            mcls._initialize_base(model_cls)
            mcls._attach_interface(model_cls)

        else:
            root = mcls._locate_root(bases=model_cls.__mro__[1:])
            if root is None:
                # No selector-aware parent; treat this as a new façade.
                mcls._initialize_base(model_cls)
                mcls._configure_root(model_cls)
                mcls._attach_interface(model_cls)
            elif root is model_cls:
                mcls._configure_root(model_cls)
                mcls._attach_interface(model_cls)
            else:
                # this is a concrete subclass
                mcls._register_subclass(root, model_cls, selector_value)
                mcls._attach_interface(model_cls)

        return model_cls


    @staticmethod
    def _locate_root(
            bases: Tuple[Type[Any], ...]) -> Optional[Type[BaseModel]]:
        """
        Find the nearest selector-aware ancestor in the provided MRO slice.
        """

        for base in bases:
            if isinstance(base, SelectorMeta):
                discriminator = getattr(base, "__selector_discriminator__", None)
                if discriminator is None:
                    # Base hasn't been configured yet; skip it.
                    continue
                return base
        return None


    @classmethod
    def _initialize_base(cls, model_cls: Type[BaseModel]) -> None:
        """
        Seed metadata for the rootless base generated by the factory.
        """

        if "__selector_registry_cls__" not in model_cls.__dict__:
            model_cls.__selector_registry_cls__ = MatchRegistry

        model_cls.__selector_root__ = None
        model_cls.__selector_registry__ = None
        model_cls.__selector_discriminator__ = None
        model_cls.__selector_config__ = None
        model_cls.__selector_value__ = None


    @classmethod
    def _configure_root(cls, model_cls: Type[BaseModel]) -> None:
        """
        Initialize a root façade capable of routing to registered subclasses.
        """

        field_name, config = _find_selector_definition(model_cls)
        registry_cls: Type[SelectorRegistry] = getattr(
            model_cls,
            "__selector_registry_cls__",
            MatchRegistry,
        )
        registry = registry_cls()

        model_cls.__selector_root__ = model_cls
        model_cls.__selector_registry_cls__ = registry_cls
        model_cls.__selector_registry__ = registry
        model_cls.__selector_discriminator__ = field_name
        model_cls.__selector_config__ = config
        model_cls.__selector_value__ = None


    @classmethod
    def _register_subclass(
            cls,
            root: Type[BaseModel],
            model_cls: Type[BaseModel],
            selector_value: Any) -> None:
        """
        Register a subclass beneath the identified root façade.
        """

        if selector_value is _MISSING:
            selector_value = _extract_match_value(
                model_cls,
                getattr(root, "__selector_discriminator__", None),
            )

        registry: SelectorRegistry = getattr(root, "__selector_registry__", None)
        if registry is None:
            registry_cls: Type[SelectorRegistry] = getattr(
                root,
                "__selector_registry_cls__",
                MatchRegistry,
            )
            registry = registry_cls()
            root.__selector_registry__ = registry

        registry.register(model_cls, value=selector_value)

        model_cls.__selector_root__ = root
        model_cls.__selector_registry_cls__ = getattr(
            root,
            "__selector_registry_cls__",
            MatchRegistry,
        )
        model_cls.__selector_registry__ = registry
        model_cls.__selector_discriminator__ = getattr(root, "__selector_discriminator__", None)
        model_cls.__selector_config__ = getattr(root, "__selector_config__", None)
        model_cls.__selector_value__ = selector_value


    @classmethod
    def _attach_interface(cls, model_cls: Type[BaseModel]) -> None:
        """
        Ensure discriminator helper methods and defaults are present on the class.
        """

        if "__selector_normalize__" not in model_cls.__dict__:
            setattr(model_cls, "__selector_normalize__", staticmethod(_normalize_payload))

        if "__selector_resolver__" not in model_cls.__dict__:
            # Resolver defaults to None; subclasses can provide their own.
            setattr(model_cls, "__selector_resolver__", None)

        interface_methods = {
            "selector_discriminator": classmethod(_selector_discriminator_helper),
            "selector_config": classmethod(_selector_config_helper),
            "_resolve_subclass": classmethod(_resolve_subclass_helper),
            "model_validate": classmethod(_model_validate_helper),
        }

        for name, method in interface_methods.items():
            if name not in model_cls.__dict__:
                setattr(model_cls, name, method)


def _selector_discriminator_helper(cls: Type[BaseModel]) -> Optional[str]:
    """
    Return the configured discriminator field name, if any.
    """

    root = getattr(cls, "__selector_root__", cls)
    return getattr(root, "__selector_discriminator__", None)


def _selector_config_helper(
        cls: Type[BaseModel]) -> Optional[DiscriminatorFieldConfig]:
    """
    Return the discriminator marker metadata, if configured.
    """

    root = getattr(cls, "__selector_root__", cls)
    return getattr(root, "__selector_config__", None)


def _resolve_subclass_helper(
        cls: Type[BaseModel],
        obj: Any) -> Tuple[Type[BaseModel], Dict[str, Any]]:
    """
    Determine the concrete subclass for the supplied payload.
    """

    normalize: Callable[[Any], Dict[str, Any]]
    normalize = getattr(cls, "__selector_normalize__", _normalize_payload)
    data = normalize(obj)
    resolver = getattr(cls, "__selector_resolver__", None)
    if callable(resolver):
        result = resolver(cls, data)
        if not isinstance(result, tuple) or len(result) != 2:
            raise ValueError("Custom selector resolver must return (subclass, payload).")
        return result

    field = cls.selector_discriminator()
    config = cls.selector_config()
    if field is None or config is None:
        raise ValueError(f"{cls.__name__} is missing discriminator metadata.")

    root = getattr(cls, "__selector_root__", cls)
    registry: Optional[SelectorRegistry] = getattr(root, "__selector_registry__", None)
    if registry is None:
        registry_cls: Type[SelectorRegistry] = getattr(
            root,
            "__selector_registry_cls__",
            MatchRegistry,
        )
        registry = registry_cls()
        root.__selector_registry__ = registry

    return registry.resolve(data, field=field, config=config, facade=root)


def _model_validate_helper(
        cls: Type[BaseModel],
        obj: Any,
        *,
        strict: Optional[bool] = None,
        from_attributes: Optional[bool] = None,
        context: Optional[Dict[str, Any]] = None) -> Type[BaseModel]:
    """
    Perform dynamic validation, dispatching façade classes to registered subclasses.
    """

    if cls is getattr(cls, "__selector_root__", cls):
        subclass, normalized = cls._resolve_subclass(obj)
        if subclass is cls:
            obj = normalized

        else:
            return subclass.model_validate(
                normalized,
                strict=strict,
                from_attributes=from_attributes,
                context=context)

    return BaseModel.model_validate.__func__(
        cls,
        obj,
        strict=strict,
        from_attributes=from_attributes,
        context=context)


def _find_selector_definition(
        model_cls: Type[BaseModel]) -> Tuple[str, DiscriminatorFieldConfig]:
    """
    Locate the discriminator field declared on the façade.
    """

    found: Optional[Tuple[str, DiscriminatorFieldConfig]] = None
    for name, field_info in model_cls.model_fields.items():
        for item in field_info.metadata:
            if isinstance(item, DiscriminatorFieldConfig):
                if found is not None:
                    raise ValueError(
                        f"{model_cls.__name__} must declare exactly one Discriminator field."
                    )
                found = (name, item)
    if found is None:
        raise ValueError(f"{model_cls.__name__} must declare a field using Discriminator(...).")
    return found


def _extract_match_value(
        model_cls: Type[BaseModel],
        discriminator_field: Optional[str]) -> Any:
    """
    Identify the match value declared on the subclass.
    """

    if discriminator_field:
        field_info = model_cls.model_fields.get(discriminator_field)
        if field_info is not None:
            for item in field_info.metadata:
                if isinstance(item, MatchConfig):
                    return item.value

    for name, field_info in model_cls.model_fields.items():
        for item in field_info.metadata:
            if isinstance(item, MatchConfig):
                return item.value

    raise ValueError(
        f"{model_cls.__name__} must declare selector metadata using Match(...)."
    )


def _normalize_payload(obj: Any) -> Dict[str, Any]:
    """
    Convert arbitrary payload objects into a mutable mapping.
    """

    if isinstance(obj, Mapping):
        return dict(obj)

    if isinstance(obj, BaseModel):
        return obj.model_dump()

    return obj


class SimpleSelector(BaseModel, metaclass=SelectorMeta):
    """
    Base model that acts as a facade for to its subclasses, based on the value
    of a discriminator field.

    Subclasses must declare a single discriminator field using the
    `Discriminator` helper.

    instantiation or model_validate() will select the appropriate subclass based
    on the value of the discriminator field on the incoming data, compared
    against the values of the field on the registered subclasses.
    """

    __selector_registry_cls__ = MatchRegistry


# The end.
