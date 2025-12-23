# Runtime

本节介绍每个 TongSIM Python 会话都会用到的运行时核心组件：

- `TongSim`：同步友好的入口封装，聚合 `WorldContext` 与常用工具。
- `WorldContext`：管理专用 `AsyncLoop`、gRPC 连接与资源生命周期。
- `AsyncLoop`：在后台线程运行 asyncio loop，便于同步代码安全驱动异步 RPC。

此外，本节也包含基础的日志初始化与版本信息查询接口。

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
