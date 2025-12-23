"""
connection.grpc.bidi_stream

Exports:
- BidiStream: gRPC bidirectional stream controller
- BidiStreamReader: gRPC → Python message reader
- BidiStreamWriter: Python → gRPC message writer
"""

import abc
import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable
from typing import Any, TypeVar

import grpc
from grpc.aio import AioRpcError

from tongsim.logger import get_logger

__all__ = ["BidiStream", "BidiStreamReader", "BidiStreamWriter"]

_logger = get_logger("gRPC")

GrpcReq = TypeVar("GrpcReq")
GrpcResp = TypeVar("GrpcResp")
T = TypeVar("T")


class StreamNotStartedError(RuntimeError):
    """Raised when attempting to communicate before calling `start()`."""

    def __init__(self):
        super().__init__("Stream not started")


class BidiStream[GrpcReq, GrpcResp]:
    """
    Wrapper for gRPC stream-stream calls with read/write state and lifecycle management.

    The scheduling of read/write loops is intentionally left to the caller to better fit
    structured concurrency models.
    """

    def __init__(
        self, stub_func: Callable[[], grpc.aio.StreamStreamCall], name: str = ""
    ):
        self._stub_func = stub_func
        self._name = name
        self._running: bool = False
        self._stream: grpc.aio.StreamStreamCall | None = None

    async def start(self):
        """Initialize the gRPC stream (must be called before read/write)."""
        if self._stream is not None:
            raise RuntimeError("Stream already started")
        self._stream = self._stub_func()
        self._running = True
        _logger.info(f"[{self._name}] Stream started.")

    def is_running(self) -> bool:
        return self._running

    async def write(self, req: GrpcReq) -> bool:
        if not self._running or self._stream is None:
            raise StreamNotStartedError
        try:
            await self._stream.write(req)
            return True
        except AioRpcError as e:
            _logger.warning(f"[{self._name}] Write failed: {e}")
            return False

    async def aclose(self):
        if not self._stream:
            return
        _logger.debug(f"[{self._name}] Closing stream.")
        self._running = False
        with contextlib.suppress(Exception):
            await self._stream.done_writing()
        with contextlib.suppress(Exception):
            await self._stream.cancel()

    async def done_writing(self):
        """Close the write side of the stream while keeping the read side open."""
        if self._stream and self._running:
            try:
                await self._stream.done_writing()
                _logger.debug(f"[{self._name}] Done writing.")
            except AioRpcError as e:
                _logger.warning(f"[{self._name}] done_writing failed: {e}")
        self._running = False

    async def read(self) -> GrpcResp:
        """Read a single response message."""
        if self._stream is None:
            raise StreamNotStartedError
        try:
            return await self._stream.read()
        except AioRpcError as e:
            _logger.warning(f"[{self._name}] Read failed: {e}")
            raise

    def __aiter__(self):
        if self._stream is None:
            raise StreamNotStartedError
        return self._read_iterator()

    async def _read_iterator(self):
        if not self._stream:
            raise StreamNotStartedError

        while self._running:
            try:
                result = await self._stream.read()
                if result is None:
                    break
                yield result
            except asyncio.CancelledError:
                _logger.debug(f"[{self._name}] Read loop cancelled.")
                break
            except AioRpcError as e:
                _logger.warning(f"[{self._name}] Read loop error: {e}")
                break
            except Exception as e:
                _logger.exception(f"[{self._name}] Unexpected error in read loop: {e}")
                break

        self._running = False
        _logger.info(f"[{self._name}] Stream exited.")


class BidiStreamReader[T](abc.ABC):
    """
    Abstract base class that reads gRPC messages and decodes them into Python objects.

    Subclasses must implement `_decode()`.
    """

    def __init__(self, stream: BidiStream):
        self._stream = stream

    async def read(self) -> T:
        grpc_resp = await self._stream.read()
        return self._decode(grpc_resp)

    def __aiter__(self) -> AsyncIterator[T]:
        return self._internal_iterator()

    async def _internal_iterator(self) -> AsyncIterator[T]:
        async for grpc_resp in self._stream:
            yield self._decode(grpc_resp)

    @abc.abstractmethod
    def _decode(self, grpc_resp: Any) -> T:
        """
        Convert a gRPC response message into a Python object.
        """
        ...


class BidiStreamWriter(abc.ABC):
    """
    Abstract base class that takes Python arguments and encodes them into gRPC requests.

    Subclasses must implement `_encode()`.
    """

    def __init__(self, stream: BidiStream):
        self._stream = stream

    async def write(self, *args, **kwargs) -> bool:
        grpc_req = self._encode(*args, **kwargs)
        return await self._stream.write(grpc_req)

    async def done(self):
        await self._stream.done_writing()

    @abc.abstractmethod
    def _encode(self, *args, **kwargs) -> GrpcReq:
        """
        Encode Python arguments into a gRPC request message.
        """
        ...
