# :material-language-python: Python Client

TongSIM Lite provides a lightweight **Python SDK** for controlling a UE instance over **gRPC**. Internally it uses `grpc.aio` (async), while offering a convenient **synchronous facade** for scripts and tutorials.

!!! tip ":material-lightbulb-on: Two ways to use the SDK"
    - **Synchronous scripts**: use `TongSim` + `context.sync_run(...)`
    - **Async applications**: schedule coroutines on `WorldContext.loop`

---

## :material-door-open: Entry points

| Layer | Main type | Location | What it does |
|---|---|---|---|
| Facade | `tongsim.TongSim` | `src/tongsim/tongsim.py` | One-stop wrapper (context + utilities), supports `with` |
| Runtime | `tongsim.core.WorldContext` | `src/tongsim/core/world_context.py` | Owns the async loop + gRPC connection; provides `sync_run` |
| Event loop | `tongsim.core.AsyncLoop` | `src/tongsim/core/async_loop.py` | Dedicated background thread running an asyncio loop |
| gRPC connection | `tongsim.connection.grpc.GrpcConnection` | `src/tongsim/connection/grpc/core.py` | Creates channel + instantiates all service stubs |
| High-level APIs | `UnaryAPI`, `CaptureAPI` | `src/tongsim/connection/grpc/*.py` | Convenience wrappers around proto RPCs |

---

## :material-rotate-right: AsyncLoop model (why there is a background thread)

gRPC `aio` stubs expect an asyncio loop. TongSIM Lite standardizes runtime behavior by running **one dedicated asyncio loop in a background thread**:

```text
Your thread (sync code)
  -> context.sync_run(coro)
     -> AsyncLoop thread (asyncio + grpc.aio)
        -> await stub.SomeRpc(...)
```

This design keeps synchronous training scripts simple, while still allowing async concurrency when needed.

!!! warning ":material-alert: Avoid deadlocks"
    `WorldContext.sync_run(...)` cannot be called from the AsyncLoop thread. The SDK guards against this and raises an error if you try.

---

## :material-console: Typical call pattern

The “shape” of most SDK calls is:

1. Get the connection from `context.conn`
2. Call an async helper (for example `UnaryAPI.reset_level(...)`)
3. Use `context.sync_run(...)` if you are in synchronous code

```python
from tongsim import TongSim
from tongsim.connection.grpc.unary_api import UnaryAPI

with TongSim("127.0.0.1:5726") as ts:
    ts.context.sync_run(UnaryAPI.reset_level(ts.context.conn))
    actors = ts.context.sync_run(UnaryAPI.query_info(ts.context.conn))
    print(f"actors: {len(actors)}")
```

---

## :material-shape-outline: Data types and helpers

The SDK includes small, practical building blocks:

- `tongsim.math`: `Vector3`, `Transform`, geometry helpers
- `tongsim.type`: enums used by RPCs (for example RL demo orientation/hand types)
- `tongsim.entity`: optional wrappers for higher-level interaction patterns
- `tongsim.manager.utils`: convenience utilities used by examples/tutorials

!!! note ":material-information-outline: Protobuf is the source of truth"
    The authoritative API contract is defined in `protobuf/tongsim_lite_protobuf/*.proto`. The Python SDK wraps generated `*_pb2.py` / `*_pb2_grpc.py` modules.

---

## :material-checklist: Best practices

- Create **one `WorldContext` per UE instance** (per endpoint).
- Keep heavy CPU work (vision, planning) off the AsyncLoop thread; offload it to worker threads/processes if needed.
- Handle resets defensively: a map travel can invalidate cached actor IDs and local state.

---

**Next:** [Data Flow](data_flow.md)
