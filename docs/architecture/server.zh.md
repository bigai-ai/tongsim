# :material-server: Unreal 服务端

在 TongSIM Lite 中，“服务端”指你运行的 **Unreal Engine 进程**（Editor 的 PIE 或打包程序）。它负责维护仿真世界，并启动 **gRPC Server** 对外提供控制/观测接口；所有会读写世界状态的逻辑都在 **Game Thread** 上执行。

!!! note ":material-lan-connect: 默认地址"
    gRPC Server 默认绑定 `0.0.0.0:5726`。端口定义位于 `unreal/Plugins/TongSimGrpc/Source/TongosGrpc/Private/TSGrpcSubsystem.cpp`。

---

## :material-package-variant: 你最常会接触的 UE 模块

TongSIM Lite 的 UE 侧代码主要分为两组插件：

| 插件组 | 位置 | 提供的能力 |
|---|---|---|
| TongSimCore | `unreal/Plugins/TongSimCore` | 仿真通用能力（Arena 流式加载、相机采集、体素化等） |
| TongSimGrpc | `unreal/Plugins/TongSimGrpc` | gRPC Server 运行时与各类服务实现 |

---

## :material-connection: gRPC 运行与线程模型

核心约束是：

> **网络 IO 在 gRPC 工作线程处理，但所有 Gameplay / World 的读写必须在 UE Game Thread 执行。**

```text
gRPC worker threads（IO）
  -> Channel<RpcEvent>
     -> UTSGrpcSubsystem::Tick()  [Game Thread]
        -> RpcRouter::handle()
           -> Unary handler 或 Reactor（多帧任务）
```

### :material-router: `UTSGrpcSubsystem`（生命周期 + 路由分发）

`UTSGrpcSubsystem` 是一个 `UGameInstanceSubsystem`（同时可 Tick），主要负责：

- 在 `Initialize()` 中启动 gRPC Server（`tongos::RpcServer`）
- 通过线程安全的 Channel 接收 gRPC 请求事件
- 在每帧 `Tick()` 中在 Game Thread 上处理并分发请求（`UpdateRpcRouter()`）

关键文件：

- `unreal/Plugins/TongSimGrpc/Source/TongosGrpc/Public/TSGrpcSubsystem.h`
- `unreal/Plugins/TongSimGrpc/Source/TongosGrpc/Private/TSGrpcSubsystem.cpp`

!!! tip ":material-shield-check: 这条规则很重要"
    扩展新接口时请保持同样的约束：**不要在 gRPC 工作线程中访问 `UWorld`**。

---

## :material-fingerprint: Actor ID 映射（FGuid ↔ Actor）

为了让 Python 能稳定引用 UE 对象，TongSIM Lite 维护了一套注册表：

- Unreal `Actor` ⇄ 生成的 `FGuid`
- `FGuid` 会序列化到 `ObjectId.guid`（16 字节，前几个字段采用小端布局）

`UTSGrpcSubsystem` 会：

- World 初始化后扫描并注册现存 Actor
- 监听 Actor Spawn 自动注册新对象
- 在 `EndPlay` / `OnDestroyed` 时将对应 ID 标记为 destroyed

这也是“按 id 查询 Actor 状态 / 销毁 Actor”等接口能够工作的前提。

---

## :material-api: 服务与 UE 侧实现

TongSIM Lite 支持多个 gRPC 服务。每个方法通过“方法名字符串”绑定到 **Unary Handler** 或 **Reactor**（例如 `"/tongsim_lite.demo_rl.DemoRLService/QueryState"`）。

| 服务 | Proto | UE 子系统 | 说明 |
|---|---|---|---|
| Arena | `protobuf/tongsim_lite_protobuf/arena.proto` | `UArenaGrpcSubsystem` | 多关卡流式加载 + Anchor 坐标系 |
| DemoRL | `protobuf/tongsim_lite_protobuf/demo_rl.proto` | `UDemoRLSubsystem` | Spawn/query/move/导航等能力 |
| Voxel | `protobuf/tongsim_lite_protobuf/voxel.proto` | `UDemoRLSubsystem` | 通过 `TSVoxelGridFuncLib` 提供体素查询 |
| Capture | `protobuf/tongsim_lite_protobuf/capture.proto` | `UCaptureGrpcSubsystem` | RGB/Depth 相机与 Snapshot |

关键文件：

- `unreal/Plugins/TongSimGrpc/Source/TongSimProto/Private/DemoRL/ArenaGrpcSubsystem.cpp`
- `unreal/Plugins/TongSimGrpc/Source/TongSimProto/Private/DemoRL/DemoRLSubsystem.cpp`
- `unreal/Plugins/TongSimGrpc/Source/TongSimProto/Private/Capture/CaptureGrpcSubsystem.cpp`

---

## :material-progress-clock: Reactor（多帧请求处理器）

部分操作无法在单帧内完成，例如：

- Arena 的加载/重置/销毁（Streaming Level）
- 长距离移动（move-towards、NavMesh 导航）
- 等待一次采集帧完成（snapshot）

因此 UE 侧使用 **Reactor**：

- `onRequest(...)` 接收请求并初始化状态
- `Tick(...)` 每帧推进任务
- 满足完成条件后结束 reactor 并回包

该机制可以保证逻辑与游戏循环对齐，并避免阻塞 Game Thread。

---

## :material-hammer-wrench: 扩展 UE 服务端

=== ":material-file-code-outline: 添加一个新 RPC"

    1. 在 `protobuf/tongsim_lite_protobuf/*.proto` 定义 request/response。
    2. 为 Python 与 UE 生成代码（Python 参考 `scripts/generate_pb2.py`；UE 侧使用 `tongsim_lite_protobuf/*.pb.h` 等生成文件）。
    3. 在 `unreal/Plugins/TongSimGrpc/Source/TongSimProto` 实现 Unary Handler 或 Reactor。
    4. 使用 `UTSGrpcSubsystem::RegisterUnaryHandler` / `RegisterReactor` 注册方法名。

=== ":material-bug-outline: 调试一个现有 RPC"

    - 确认 Editor 已进入 **PIE**，并监听在预期端口上。
    - 在对应子系统（DemoRL/Arena/Capture）中添加 UE 日志定位。
    - 区分调用类型：**Unary** 应快速返回；**Reactor** 会跨多帧等待。

---

**下一步：** [Python 客户端](client.md)
