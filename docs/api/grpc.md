# :material-connection: gRPC Connection

TongSIM Lite uses **gRPC** to connect Python to Unreal. The SDK wraps `grpc.aio` and auto-instantiates all service stubs for you.

In most code you don’t need to build channels manually—use `WorldContext.conn` and call the service helpers (for example `UnaryAPI` / `CaptureAPI`).

---

## :material-lan-connect: Key building blocks

| Component | Location | What it does |
|---|---|---|
| `GrpcConnection` | `src/tongsim/connection/grpc/core.py` | Creates the gRPC channel and instantiates all stubs |
| Stub discovery | `src/tongsim/connection/grpc/utils.py` | Auto-finds `*_pb2_grpc.py` stubs via reflection |
| Safe wrappers | `src/tongsim/connection/grpc/utils.py` | Error-handling decorators for async RPC calls |
| SDK↔Proto conversion | `src/tongsim/connection/grpc/utils.py` | Converts `Vector3`/`Transform` to protobuf messages |

!!! note ":material-information-outline: Message size"
    The Python channel is configured with a 100MB send/receive limit in `GrpcConnection` to support image and voxel payloads.

---

## API References

::: tongsim.connection.grpc.core.GrpcConnection

::: tongsim.connection.grpc.utils.iter_all_grpc_stubs

::: tongsim.connection.grpc.utils.iter_all_proto_messages

::: tongsim.connection.grpc.utils.safe_async_rpc

::: tongsim.connection.grpc.utils.safe_unary_stream

::: tongsim.connection.grpc.utils.sdk_to_proto

::: tongsim.connection.grpc.utils.proto_to_sdk
