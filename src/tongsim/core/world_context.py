"""
core.world_context

Defines WorldContext, which owns the resources bound to a single TongSim
runtime: the async event loop and gRPC connectivity.
"""

import threading
import uuid
from collections.abc import Awaitable
from concurrent.futures import Future
from typing import Any, Final

from tongsim.connection.grpc import (
    GrpcConnection,
)
from tongsim.core import AsyncLoop
from tongsim.logger import get_logger

_logger = get_logger("world")


class WorldContext:
    """
    Aggregate runtime resources for a TongSim session.

    Responsibilities:
    - Manage the dedicated AsyncLoop.
    - Hold the gRPC connection (GrpcConnection and LegacyGrpcStreamClient).

    Notes:
        - All owned resources are closed automatically during teardown.
    """

    def __init__(self, grpc_endpoint: str):
        self._uuid: Final[uuid.UUID] = uuid.uuid4()
        self._loop: Final[AsyncLoop] = AsyncLoop(name=f"world-main-loop-{self._uuid}")
        self._loop.start()

        self._conn: Final[GrpcConnection]

        # Ensure stubs are initialised on the AsyncLoop so gRPC sees the same loop.
        self.sync_run(self._async_init_grpc(grpc_endpoint))

        _logger.debug(f"[WorldContext {self._uuid}] started.")
        self._is_shutdown: bool = False

    # TODO: classmethod
    async def _async_init_grpc(self, grpc_endpoint: str):
        self._conn = GrpcConnection(grpc_endpoint)

    @property
    def uuid(self) -> str:
        """Short identifier (first eight characters) for this world instance."""
        return str(self._uuid)[:8]

    @property
    def loop(self) -> AsyncLoop:
        """Primary AsyncLoop used for background scheduling."""
        return self._loop

    @property
    def conn(self) -> GrpcConnection:
        """Underlying gRPC connection."""
        return self._conn

    def sync_run(self, coro: Awaitable, timeout: float | None = None) -> Any:
        """
        Execute an async coroutine on the loop and wait for it synchronously.

        Args:
            coro (Awaitable): Coroutine to run.
            timeout (float | None): Optional timeout in seconds. Raises TimeoutError
                if exceeded.

        Returns:
            Any: Result returned by the coroutine.
        """
        if threading.current_thread() is self._loop.thread:
            raise RuntimeError(
                f"Cannot call `sync_run` from the same thread as AsyncLoop [{self._loop.name}] - this would cause a deadlock."
            )

        return self._loop.spawn(
            coro, name=f"[World-Context {self.uuid} sync task]"
        ).result(timeout=timeout)

    def async_task(self, coro: Awaitable[Any], name: str) -> Future[Any]:
        """Schedule a coroutine on the loop without waiting for completion."""
        return self._loop.spawn(coro, name=name)

    def release(self):
        """
        Release all managed resources:
        - cancel outstanding tasks
        - close the gRPC connection
        - stop the event loop
        """
        if self._is_shutdown:
            return
        self._is_shutdown = True

        _logger.debug(f"[WorldContext {self._uuid}] releasing...")

        try:
            self._loop.cancel_tasks(timeout=1.0)
            self._loop.spawn(
                self._conn.aclose(),
                name=f"WorldContext {self.uuid} release gRPC connection.",
            ).result(timeout=1.0)
        except Exception as e:
            _logger.warning(
                f"[WorldContext {self._uuid}] failed to release cleanly: {e}"
            )

        self._loop.stop()
        _logger.debug(f"[WorldContext {self._uuid}] release complete.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def __del__(self):
        _logger.debug(f"[WorldContext {self._uuid}] gc.")
        self.release()
