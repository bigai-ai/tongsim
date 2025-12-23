# Runtime

This section introduces the core runtime building blocks that every TongSim
Python session relies on.

- `TongSim` exposes a synchronous, user-friendly facade that bootstraps
  `WorldContext` and offers high-level helpers.
- `WorldContext` owns the dedicated `AsyncLoop`, gRPC connections, and the
  overall lifecycle management for a running session.
- `AsyncLoop` wraps an asyncio event loop inside a background thread so SDK
  code can drive asynchronous calls safely from synchronous workflows.
- Runtime helpers also include basic logging setup and version reporting.

## References

### TongSim

::: tongsim.tongsim.TongSim

### WorldContext

::: tongsim.core.world_context.WorldContext

### AsyncLoop

::: tongsim.core.async_loop.AsyncLoop

### Logging

::: tongsim.logger.initialize_logger

::: tongsim.logger.set_log_level

::: tongsim.logger.get_logger

### Version

::: tongsim.version.get_version_info
