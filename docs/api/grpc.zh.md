# :material-connection: gRPC 连接（Connection）

TongSIM Lite 使用 **gRPC** 连接 Python 与 Unreal。SDK 基于 `grpc.aio`，并会自动实例化所有服务的 Stub。

多数情况下你不需要手动创建 channel：直接使用 `WorldContext.conn`，并调用上层 API（例如 `UnaryAPI` / `CaptureAPI`）即可。

---

## :material-lan-connect: 核心组件

| 组件 | 位置 | 职责 |
|---|---|---|
| `GrpcConnection` | `src/tongsim/connection/grpc/core.py` | 创建 gRPC channel 并初始化所有 stubs |
| Stub 自动发现 | `src/tongsim/connection/grpc/utils.py` | 通过反射遍历 `*_pb2_grpc.py` 自动加载 Stub |
| 安全调用封装 | `src/tongsim/connection/grpc/utils.py` | 对异步 RPC 调用做异常兜底 |
| SDK↔Proto 转换 | `src/tongsim/connection/grpc/utils.py` | `Vector3`/`Transform` 与 protobuf 的互转 |

!!! note ":material-information-outline: 消息大小"
    Python 端在 `GrpcConnection` 中配置了 100MB 的收发限制，用于支持图像与体素等大 payload。

---

## API References

::: tongsim.connection.grpc.core.GrpcConnection

::: tongsim.connection.grpc.utils.iter_all_grpc_stubs

::: tongsim.connection.grpc.utils.iter_all_proto_messages

::: tongsim.connection.grpc.utils.safe_async_rpc

::: tongsim.connection.grpc.utils.safe_unary_stream

::: tongsim.connection.grpc.utils.sdk_to_proto

::: tongsim.connection.grpc.utils.proto_to_sdk
