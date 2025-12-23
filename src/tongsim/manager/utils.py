from tongsim.core.world_context import WorldContext
from tongsim.logger import get_logger

_logger = get_logger("utils")


class UtilFuncs:
    """
    Common helper functions for frequently used simulation operations.
    """

    def __init__(self, world_context: WorldContext):
        self._context: WorldContext = world_context
