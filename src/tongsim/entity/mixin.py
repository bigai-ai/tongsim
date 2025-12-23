"""
entity.mixin
"""

from collections import defaultdict
from typing import ClassVar, TypeVar

from tongsim.connection.grpc.unary_api import UnaryAPI
from tongsim.connection.tags import ComponentType
from tongsim.core.world_context import WorldContext
from tongsim.logger import get_logger

from .entity import Entity

_logger = get_logger("entity")

T = TypeVar("T")


__all__ = [
    "AgentEntity",
    "CameraEntity",
]


async def _bind_ability_methods[T](entity: Entity, ability_type: type[T]) -> None:
    """
    Dynamically bind public methods of an Ability from its Impl onto an `Entity`.

    This forwards all public methods defined in the Ability Protocol from the
    `entity.async_as_(Ability)` implementation to the entity instance itself.

    Args:
        entity (Entity): The target entity to inject methods into.
        ability_type (type[Protocol]): The Ability Protocol type.

    """
    # TODO: Avoid overriding attributes already defined on `Entity`.

    assert hasattr(ability_type, "__annotations__"), (
        "ability_type must be a Protocol type"
    )

    impl = await entity.async_as_(ability_type)
    for attr in dir(ability_type):
        # Skip private and special methods.
        if attr.startswith("_"):
            continue
        # Only bind callables.
        value = getattr(impl, attr, None)
        if not callable(value):
            continue

        setattr(entity, attr, value)


class MixinEntityBase(Entity):
    """
    Base class that declares supported abilities via `_ability_types` and
    automatically binds those ability methods onto the entity instance.

    `_ability_types` is a class variable and must be explicitly defined by subclasses.
    """

    _ability_types: ClassVar[list[type]] = []

    @classmethod
    async def create(cls, *args, **kwargs):
        self = cls(*args, **kwargs)
        for ability in cls._ability_types:
            await _bind_ability_methods(self, ability)
        return self

    @classmethod
    async def from_grpc(
        cls, entity_id: str, world_context: WorldContext
    ) -> "MixinEntityBase":
        """
        Construct an entity by querying its components via gRPC.
        """

        # TODO: Duplicated logic exists here to keep the base `Entity` implementation minimal.
        resp = await UnaryAPI.query_components(world_context.conn, entity_id)
        if resp is None:
            raise RuntimeError(f"Failed to query components for entity '{entity_id}'.")

        components: dict[ComponentType, list[str]] = defaultdict(list)
        for component_id, component_type in resp.items():
            components[component_type].append(component_id)

        _logger.debug(
            f"[Consturct mixin entity from gRPC] Entity {entity_id}  ---  ability-types: {list(cls._ability_types)}"
        )
        return await cls.create(entity_id, world_context, components)


class CameraEntity(MixinEntityBase):
    """
    TongSIM camera entity.
    """

    _ability_types: ClassVar[list[type]] = []


class AgentEntity(MixinEntityBase):
    """
    Agent entity.
    """

    _ability_types: ClassVar[list[type]] = []
