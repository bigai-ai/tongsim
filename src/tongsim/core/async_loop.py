"""
core.async_loop

Defines AsyncLoop, a helper that runs an asyncio event loop inside a dedicated
thread so we can schedule coroutines from synchronous contexts.

Goals:
1. Keep connection-related coroutines (for example gRPC connections) on the
   same thread so AsyncLoop can manage their lifetime consistently.
   Note: a single loop still shares state, so callers must remain mindful of
   their own concurrency guarantees.
2. Allow heavy or blocking operations to be offloaded to purpose-built threads
   while the caller thread stays responsive.
"""

import asyncio
import contextlib
import threading
from collections.abc import Awaitable
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

from tongsim.logger import get_logger

_logger = get_logger("core")


class AsyncLoop:
    """
    Wrap an asyncio event loop that lives on a dedicated background thread and
    exposes a TaskGroup for scheduling.

    Features:
    - Persistent background thread hosting the event loop.
    - Managed asyncio.TaskGroup for business coroutines.
    """

    def __init__(self, name: str = "AsyncLoop") -> None:
        """
        Initialise the AsyncLoop wrapper.

        Args:
            name: Identifier used for the loop thread and logging.
        """
        self._name = name
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._group_ready = threading.Event()
        self._main_task: asyncio.Task[Any] | None = None
        self._task_group: asyncio.TaskGroup | None = None
        self._business_tasks: set[asyncio.Task[Any]] = (
            set()
        )  # Track tasks spawned for application work.

    @property
    def thread(self) -> threading.Thread:
        return self._thread

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    @property
    def name(self) -> str:
        return self._name

    def start(self, timeout: float = 1.0) -> None:
        """
        Launch the background thread and event loop.

        Args:
            timeout: Maximum time to wait for the loop and TaskGroup to become ready.

        Raises:
            RuntimeError: If the loop fails to start within the timeout.
        """
        if self.is_running():
            raise RuntimeError(f"[AsyncLoop {self._name}] already running.")

        self._thread = threading.Thread(target=self._run, name=self._name, daemon=True)
        self._thread.start()

        if not self._group_ready.wait(timeout):
            raise RuntimeError(f"[AsyncLoop {self._name}] timeout starting event loop.")

        _logger.debug(f"[AsyncLoop {self._name}] started.")

    def _run(self) -> None:
        """Background thread body: create and drive the event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)  # Bind loop to the current thread.
        self._main_task = self._loop.create_task(self._main(), name="__main_task__")
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()
            _logger.debug(f"[AsyncLoop {self._name}] loop closed.")

    async def _main(self) -> None:
        """Main coroutine: keep the TaskGroup alive until shutdown."""
        try:
            async with asyncio.TaskGroup() as tg:
                self._task_group = tg
                self._group_ready.set()
                await asyncio.Future()  # Keep running; cancellation ends the loop.
        except asyncio.CancelledError:
            _logger.debug(
                f"[AsyncLoop {self._name}] main task cancelled; shutting down TaskGroup."
            )
        finally:
            assert self._loop is not None
            self._loop.call_soon_threadsafe(self._loop.stop)

    def spawn(self, coro: Awaitable[Any], name: str = "") -> Future[Any]:
        """
        Submit a coroutine to the TaskGroup.

        Args:
            coro: Coroutine object to execute.
            name: Optional name for logging.

        Returns:
            Future: A concurrent.futures.Future mirroring coroutine completion or
                raising the underlying exception.
        """
        if not (self._loop and self._task_group):
            raise RuntimeError(f"[AsyncLoop {self._name}] not started.")

        outer: Future[Any] = Future()

        def _schedule() -> None:
            task: asyncio.Task[Any] = self._task_group.create_task(coro, name=name)
            self._business_tasks.add(task)

            def _on_done(t: asyncio.Task[Any]) -> None:
                self._business_tasks.discard(t)
                if t.cancelled():
                    outer.cancel()
                else:
                    exc = t.exception()
                    if exc:
                        _logger.exception(
                            f"[AsyncLoop {self._name}] Task {name!r} raised: {exc}"
                        )
                        outer.set_exception(exc)
                        # Bubble the exception so the TaskGroup cancels outstanding work.
                        assert self._main_task is not None
                        self._main_task.cancel()
                    else:
                        outer.set_result(t.result())

            task.add_done_callback(_on_done)

        self._loop.call_soon_threadsafe(_schedule)
        return outer

    def cancel_tasks(self, timeout: float) -> None:
        """
        Cancel all application tasks that were spawned via ``spawn``.

        Args:
            timeout: Maximum time to wait for cancellation to finish.
        """
        if not self.is_running():
            return

        future = asyncio.run_coroutine_threadsafe(self._cancel_tasks_seq(), self._loop)
        try:
            future.result(timeout)
        except FutureTimeoutError:
            _logger.warning(f"[AsyncLoop {self._name}] cancel_tasks timeout.")

    async def _cancel_tasks_seq(self) -> None:
        """Internal helper: cancel tracked business tasks on the loop thread."""
        _logger.debug(
            f"[AsyncLoop {self._name}] cancelling {len(self._business_tasks)} business task(s)."
        )
        if not self._business_tasks:
            return

        tasks = list(self._business_tasks)
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)
        self._business_tasks.clear()

    def stop(self, timeout: float = 5.0) -> None:
        """
        Gracefully stop the AsyncLoop:
        cancel business tasks -> cancel main task -> stop loop -> join thread.

        Args:
            timeout: Maximum time to wait for shutdown.
        """
        if not self.is_running():
            return

        # Cancelling the main TaskGroup will cascade to outstanding tasks.
        assert self._main_task is not None and self._loop is not None
        self._loop.call_soon_threadsafe(self._main_task.cancel)

        self._thread.join(timeout)
        if self._thread.is_alive():
            _logger.warning(f"AsyncLoop '{self._name}' did not exit cleanly.")
        self._thread = None

    def is_running(self) -> bool:
        """
        Check whether the loop thread is alive.

        Returns:
            bool: ``True`` when the loop is running, otherwise ``False``.
        """
        return bool(self._thread and self._thread.is_alive())

    def log_task_list(self) -> None:
        """Log all tasks currently known to the loop for diagnostics."""
        if not (self._loop and self._task_group):
            return
        task_list = asyncio.all_tasks(self._loop)
        _logger.warning(f"[AsyncLoop {self._name}] {len(task_list)} active task(s):")
        for task in task_list:
            state = (
                "cancelled"
                if task.cancelled()
                else "done"
                if task.done()
                else "pending"
            )
            detail = ""
            if task.done() and (exc := task.exception()):
                detail = f"  exception: {type(exc).__name__}: {exc}"
            coro = task.get_coro()
            _logger.warning(
                f"  - {task.get_name()} [{state}]{detail} | coro={coro.__name__ if hasattr(coro, '__name__') else coro}"
            )

    def __del__(self) -> None:
        """Ensure resources are released when the loop object is garbage collected."""
        _logger.debug(f"[AsyncLoop {self._name}] __del__ called, attempting cleanup.")
        with contextlib.suppress(Exception):
            self.stop()
