from typing import Final, TypeVar

from tongsim.core.world_context import WorldContext
from tongsim.logger import get_logger

_logger = get_logger("entity")

T = TypeVar("T")


class Entity:
    """
    An `Entity` represents an object in a TongSIM world.

    Responsibilities:

    - Manage component IDs grouped by component type
    - Provide Ability access and casting mechanisms

    Note:
        `Entity` does not store component data directly; it only maintains the
        component-id structure.
    """

    __slots__ = ("_ability_cache", "_components", "_id", "_world_context")

    def __init__(
        self,
        entity_id: str,
        world_context: WorldContext,
    ):
        self._id: Final[str] = entity_id
        self._world_context: Final[WorldContext] = world_context
        self._ability_cache: dict[type, object] = {}  # Cache created Impl instances.

    @property
    def id(self):
        return self._id

    @property
    def context(self):
        return self._world_context

    def __repr__(self) -> str:
        return f"Entity(id: {self._id})"
