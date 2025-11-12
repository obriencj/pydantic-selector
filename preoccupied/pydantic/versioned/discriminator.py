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
from typing import Any, Dict, Mapping, Optional, Tuple, Type

from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo


ModelMetaclass = type(BaseModel)

_MISSING = object()


@dataclass(frozen=True)
class DiscriminatorFieldConfig:
    """
    Marker metadata identifying discriminator behaviour for a façade field.
    """

    allow_missing: bool
    default_value: Any
    metadata: Mapping[str, Any]


def _extend_metadata(field_info: FieldInfo, config: DiscriminatorFieldConfig) -> FieldInfo:
    """
    Attach marker metadata to an existing FieldInfo instance.
    """

    existing = list(field_info.metadata)
    existing.append(config)
    object.__setattr__(field_info, "metadata", existing)
    return field_info


def Discriminator(  # noqa: N802 - factory function intentionally PascalCase
    default: Any = ...,
    *,
    allow_missing: bool = False,
    metadata: Optional[Mapping[str, Any]] = None,
    **field_kwargs: Any,
) -> FieldInfo:
    """
    Create a FieldInfo configured as the discriminator selector.
    """

    info = Field(default, **field_kwargs)
    meta = dict(metadata or {})
    config = DiscriminatorFieldConfig(
        allow_missing=allow_missing,
        default_value=meta.get("default"),
        metadata=meta,
    )
    return _extend_metadata(info, config)


class DiscriminatorMeta(ModelMetaclass):
    """
    Metaclass responsible for discriminator-aware model registration.
    """

    def __call__(cls, *args: Any, **kwargs: Any) -> "DiscriminatorBaseModel":
        """
        Route façade instantiation through validation to return concrete subclasses.
        """

        root = getattr(cls, "__discriminator_root__", cls)
        if root is cls:
            if args and kwargs:
                raise TypeError("Mixing positional and keyword arguments is not supported for façades.")
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
        **kwargs: Any,
    ) -> Type["DiscriminatorBaseModel"]:
        selector_value = kwargs.pop("selector", _MISSING)
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        mcls._configure_class(cls, selector_value)
        return cls

    @classmethod
    def _configure_class(
        cls,
        model_cls: Type["DiscriminatorBaseModel"],
        selector_value: Any,
    ) -> None:
        """
        Configure discriminator metadata for a freshly constructed class.
        """

        if model_cls.__name__ == "DiscriminatorBaseModel":
            model_cls.__discriminator_root__ = None
            model_cls.__discriminator_registry__ = {}
            model_cls.__discriminator_selector_field__ = None
            model_cls.__discriminator_config__ = None
            model_cls.__selector_value__ = None
            return

        root = cls._locate_root(bases=model_cls.__mro__[1:])
        if root is None or root is model_cls:
            cls._configure_root(model_cls)
            return
        cls._register_subclass(root, model_cls, selector_value)

    @staticmethod
    def _locate_root(bases: Tuple[Type[Any], ...]) -> Optional[Type["DiscriminatorBaseModel"]]:
        """
        Find the nearest discriminator-aware ancestor in the provided MRO slice.
        """

        for base in bases:
            if isinstance(base, DiscriminatorMeta):
                if base.__name__ == "DiscriminatorBaseModel" and getattr(base, "__discriminator_root__", None) is None:
                    continue
                root = getattr(base, "__discriminator_root__", None)
                return root or base
        return None

    @classmethod
    def _configure_root(cls, model_cls: Type["DiscriminatorBaseModel"]) -> None:
        """
        Initialize a root façade capable of routing to registered subclasses.
        """

        field_name, config = _find_discriminator_definition(model_cls)
        model_cls.__discriminator_root__ = model_cls
        model_cls.__discriminator_registry__ = {}
        model_cls.__discriminator_selector_field__ = field_name
        model_cls.__discriminator_config__ = config
        model_cls.__selector_value__ = None

    @classmethod
    def _register_subclass(
        cls,
        root: Type["DiscriminatorBaseModel"],
        model_cls: Type["DiscriminatorBaseModel"],
        selector_value: Any,
    ) -> None:
        """
        Register a subclass beneath the identified root façade.
        """

        if selector_value is _MISSING:
            raise ValueError(
                f"{model_cls.__name__} must supply 'selector=\"...\"' when subclassing {root.__name__}."
            )
        model_cls.__discriminator_root__ = root
        model_cls.__discriminator_selector_field__ = root.__discriminator_selector_field__
        model_cls.__discriminator_config__ = root.__discriminator_config__
        model_cls.__selector_value__ = selector_value
        root._register_selector(selector_value, model_cls)


class DiscriminatorBaseModel(BaseModel, metaclass=DiscriminatorMeta):
    """
    Base model that dispatches to discriminator-registered subclasses.
    """

    # __discriminator_root__: Optional[Type["DiscriminatorBaseModel"]] = None
    # __discriminator_registry__: Dict[Any, Type["DiscriminatorBaseModel"]] = {}
    # __discriminator_selector_field__: Optional[str] = None
    # __discriminator_config__: Optional[DiscriminatorFieldConfig] = None
    # __selector_value__: Optional[Any] = None


    @classmethod
    def _root(cls) -> Type["DiscriminatorBaseModel"]:
        """
        Retrieve the façade root for the current class.
        """

        return cls.__discriminator_root__ or cls


    @classmethod
    def selector_field(cls) -> Optional[str]:
        """
        Return the configured discriminator field name, if any.
        """

        return cls._root().__discriminator_selector_field__


    @classmethod
    def selector_config(cls) -> Optional[DiscriminatorFieldConfig]:
        """
        Return the discriminator marker metadata, if configured.
        """

        return cls._root().__discriminator_config__


    @classmethod
    def _register_selector(cls, value: Any, subclass: Type["DiscriminatorBaseModel"]) -> None:
        """
        Record a subclass for the provided selector value.
        """

        root = cls._root()
        if value in root.__discriminator_registry__:
            existing = root.__discriminator_registry__[value]
            raise ValueError(
                f"Duplicate discriminator selector '{value}' for {root.__name__}: "
                f"{existing.__name__} already registered."
            )
        root.__discriminator_registry__[value] = subclass


    @classmethod
    def _extract_selector(cls, obj: Any) -> Any:
        """
        Pull the selector value from arbitrary input.
        """

        field = cls.selector_field()
        if field is None:
            raise ValueError(f"{cls.__name__} is missing discriminator configuration.")

        if isinstance(obj, Mapping):
            return obj.get(field, _MISSING)

        if isinstance(obj, BaseModel):
            return getattr(obj, field, _MISSING)

        if hasattr(obj, field):
            return getattr(obj, field)

        return _MISSING


    @classmethod
    def _resolve_subclass(
        cls,
        obj: Any,
    ) -> Tuple[Type["DiscriminatorBaseModel"], Dict[str, Any]]:
        """
        Determine the concrete subclass for the supplied payload.
        """

        data = _normalize_payload(obj)
        field = cls.selector_field()
        config = cls.selector_config()
        if field is None or config is None:
            raise ValueError(f"{cls.__name__} is missing discriminator metadata.")

        value = data.get(field, _MISSING)
        if value is _MISSING:
            if not config.allow_missing:
                raise ValueError(
                    f"{cls.__name__} requires discriminator field '{field}'."
                )
            value = config.default_value
            data[field] = value

        root = cls._root()
        subclass = root.__discriminator_registry__.get(value)
        if subclass is None:
            raise ValueError(
                f"No discriminator match for value '{value}' on {root.__name__}."
            )
        return subclass, data


    @classmethod
    def model_validate(  # type: ignore[override]
            cls,
            obj: Any,
            *,
            strict: Optional[bool] = None,
            from_attributes: Optional[bool] = None,
            context: Optional[Dict[str, Any]] = None) -> "DiscriminatorBaseModel":
        """
        Perform dynamic validation, dispatching façade classes to registered subclasses.
        """

        if cls is cls._root():
            payload = _normalize_payload(obj)
            subclass, normalized = cls._resolve_subclass(payload)
            if subclass is cls:
                return super().model_validate(
                    normalized,
                    strict=strict,
                    from_attributes=from_attributes,
                    context=context,
                )
            return subclass.model_validate(
                normalized,
                strict=strict,
                from_attributes=from_attributes,
                context=context,
            )

        return super().model_validate(
            obj,
            strict=strict,
            from_attributes=from_attributes,
            context=context,
        )


def _find_discriminator_definition(
    model_cls: Type["DiscriminatorBaseModel"],
) -> Tuple[str, DiscriminatorFieldConfig]:
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


def _normalize_payload(obj: Any) -> Dict[str, Any]:
    """
    Convert arbitrary payload objects into a mutable mapping.
    """

    if isinstance(obj, Mapping):
        return dict(obj)

    if isinstance(obj, BaseModel):
        return obj.model_dump()

    return dict(obj)


__all__ = [
    "Discriminator",
    "DiscriminatorBaseModel",
    "DiscriminatorFieldConfig",
    "DiscriminatorMeta",
]

# The end.
