"""
tongsim.tongsim

Python facade for a single TongSim UE instance; backed by WorldContext for
connection management and task scheduling.
"""

from typing import Final

from tongsim.core.world_context import WorldContext
from tongsim.manager.utils import UtilFuncs

__all__ = ["TongSim"]


class TongSim:
    """
    High-level SDK entry point for controlling a connected TongSim UE instance.
    All methods expose synchronous, blocking interfaces for scripts or
    synchronous applications.
    """

    def __init__(self, grpc_endpoint: str = "127.0.0.1:5726"):
        """
        Create a TongSim runtime binding.

        Args:
            grpc_endpoint (str): gRPC endpoint of the UE server, for example
                "localhost:5726".
        """
        self._context: Final[WorldContext] = WorldContext(grpc_endpoint)
        self._utils: Final[UtilFuncs] = UtilFuncs(self._context)

    @property
    def utils(self) -> UtilFuncs:
        """
        Return helper utilities that wrap frequently used runtime operations.

        Returns:
            UtilFuncs: Helper wrapper exposing convenience functions.
        """
        return self._utils

    @property
    def context(self) -> WorldContext:
        """
        Access the runtime context that manages connections, event loop and
        task dispatch.

        Returns:
            WorldContext: Context object owning the async loop and gRPC
                resources.
        """
        return self._context

    def close(self):
        """Shut down the current runtime and release all managed resources."""
        self._context.release()

    def __enter__(self):
        """Support ``with`` statements."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support ``with`` statements."""
        self.close()
