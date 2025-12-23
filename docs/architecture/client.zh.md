# :material-language-python: Python 客户端

TongSIM Lite 提供轻量级的 **Python SDK**，用于通过 **gRPC** 控制 UE 实例。SDK 内部基于 `grpc.aio`（异步），同时为脚本和教程提供了更易用的 **同步封装**。

!!! tip ":material-lightbulb-on: 两种使用方式"
    - **同步脚本**：使用 `TongSim` + `context.sync_run(...)`
    - **异步应用**：将协程调度到 `WorldContext.loop` 上执行

---

## :material-door-open: 入口与分层

| 分层 | 核心类型 | 位置 | 职责 |
|---|---|---|---|
| Facade | `tongsim.TongSim` | `src/tongsim/tongsim.py` | 封装 context 与常用 utilities，支持 `with` |
| Runtime | `tongsim.core.WorldContext` | `src/tongsim/core/world_context.py` | 管理异步事件循环与 gRPC 连接，提供 `sync_run` |
| Event loop | `tongsim.core.AsyncLoop` | `src/tongsim/core/async_loop.py` | 独立后台线程运行 asyncio loop |
| gRPC 连接 | `tongsim.connection.grpc.GrpcConnection` | `src/tongsim/connection/grpc/core.py` | 建立 channel 并初始化所有 stubs |
| 高层 API | `UnaryAPI`、`CaptureAPI` | `src/tongsim/connection/grpc/*.py` | 对 proto RPC 的便捷封装 |

---

## :material-rotate-right: AsyncLoop 模型（为什么要单独开一个线程）

gRPC 的 `aio` stub 依赖 asyncio 事件循环。TongSIM Lite 为了让运行时更稳定、也让同步脚本更好写，会在后台线程里维护**唯一的 asyncio loop**：

```text
你的线程（同步代码）
  -> context.sync_run(coro)
     -> AsyncLoop 线程（asyncio + grpc.aio）
        -> await stub.SomeRpc(...)
```

这种设计让同步训练脚本无需显式管理 event loop，同时也保留了异步并发能力。

!!! warning ":material-alert: 避免死锁"
    `WorldContext.sync_run(...)` 不能在 AsyncLoop 线程里调用；SDK 会检测并抛出异常以避免死锁。

---

## :material-console: 常见调用方式

大部分 SDK 调用都遵循相同模式：

1. 从 `context.conn` 拿到连接
2. 调用一个异步 helper（例如 `UnaryAPI.reset_level(...)`）
3. 如果你在同步代码中，使用 `context.sync_run(...)` 等待结果

```python
from tongsim import TongSim
from tongsim.connection.grpc.unary_api import UnaryAPI

with TongSim("127.0.0.1:5726") as ts:
    ts.context.sync_run(UnaryAPI.reset_level(ts.context.conn))
    actors = ts.context.sync_run(UnaryAPI.query_info(ts.context.conn))
    print(f"actors: {len(actors)}")
```

---

## :material-shape-outline: 数据类型与工具

SDK 提供了一些实践性很强的基础组件：

- `tongsim.math`：`Vector3`、`Transform` 等几何工具
- `tongsim.type`：与 RPC 对齐的枚举（例如 RL demo 的朝向/手型）
- `tongsim.entity`：可选的更高层实体封装
- `tongsim.manager.utils`：示例与教程中常用的便捷工具

!!! note ":material-information-outline: Proto 才是权威协议"
    最终的接口协议定义在 `protobuf/tongsim_lite_protobuf/*.proto` 中。Python SDK 主要对生成的 `*_pb2.py` / `*_pb2_grpc.py` 进行封装。

---

## :material-checklist: 最佳实践

- 每个 UE 实例（每个 endpoint）建议对应一个独立的 `WorldContext`。
- 将重 CPU 任务（视觉/规划等）从 AsyncLoop 线程中分离出来，必要时使用线程池/进程池。
- 对重置保持防御性：地图切换可能导致 actor id 与本地缓存失效。

---

**下一步：** [数据流与同步](data_flow.md)
