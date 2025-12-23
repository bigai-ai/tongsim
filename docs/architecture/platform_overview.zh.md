# :material-sitemap: 系统架构概览

**TongSIM Lite** 采用典型的 **Client–Server** 架构：

- **Unreal Engine** 负责运行仿真世界（物理、导航、渲染）
- UE 侧内置 **gRPC Server**，对外提供控制与观测接口
- **Python SDK** 作为客户端连接 UE，用于训练、评测与脚本化控制

本章节帮助你建立“**哪些模块在哪运行**”的直观认知，并说明核心模块如何协作。

!!! tip ":material-compass: 何时阅读本页"
    - 你想快速理解 TongSIM Lite 的运行结构
    - 你准备扩展 gRPC 接口或新增能力
    - 你在排查连接、重置或性能问题

---

## :material-layers: 组件一览

| 组件 | 位置 | 职责 |
|---|---|---|
| Unreal 工程（仿真） | `unreal/TongSim_Lite.uproject` | 场景、智能体、物理、导航与游戏逻辑 |
| TongSimCore（UE 插件） | `unreal/Plugins/TongSimCore` | Arena 多关卡流式加载、传感器采集、体素化工具 |
| TongSimGrpc（UE 插件） | `unreal/Plugins/TongSimGrpc` | gRPC Server 运行时与各类服务实现（Arena/DemoRL/Capture/…） |
| 协议定义（Proto） | `protobuf/tongsim_lite_protobuf/*.proto` | 跨语言的请求/响应协议 |
| Python SDK | `src/tongsim` | 连接管理、类型封装与更高层的 API |

!!! note ":material-information-outline: 运行模式"
    - 在 **Unreal Editor** 中，只有进入 **Play (PIE)** 后 gRPC Server 才会可用。
    - 在 **打包程序** 中，Server 会随游戏进程启动。

---

## :material-transit-connection-variant: 高层结构图

```text
+-------------------------+           gRPC (protobuf)            +------------------------------+
| Python 进程              | <----------------------------------> | Unreal Engine (PIE/Packaged) |
|                         |                                      |                              |
| - tongsim.TongSim       |                                      | - World / 物理 / NavMesh     |
| - WorldContext + loop   |                                      | - TongSimCore（传感器等）     |
| - GrpcConnection/stubs  |                                      | - TongSimGrpc（gRPC Server）  |
| - UnaryAPI / CaptureAPI |                                      |                              |
+-------------------------+                                      +------------------------------+
```

---

## :material-key-variant: 核心概念

### :material-controller-classic: UE 是“世界状态”的唯一来源

所有世界状态（Actor、Transform、碰撞、NavMesh）都在 **Unreal** 中维护。Python 通过 gRPC 调用来控制与观测，例如：

- `DemoRLService/SpawnActor`、`SetActorTransform`、`NavigateToLocation`
- `ArenaService/LoadArena`、`ResetArena`、`LocalToWorld`
- `CaptureService/CaptureSnapshot`（RGB/Depth 采集）

### :material-fingerprint: 会话内稳定的对象标识

TongSIM Lite 使用 UE 的 **FGuid** 来标识 `Actor`，并序列化到 `ObjectId.guid`（16 字节）中。

!!! warning ":material-alert: 重置会导致缓存失效"
    **地图切换（Travel）** 或 **完整重置** 可能会销毁并重建世界。建议对 ID 做好失效处理，并在需要时重新查询。

### :material-timer-sand: 多帧任务

部分操作需要跨多帧完成（例如流式加载、长距离移动）。UE 侧使用 **Reactor（逐帧 Tick 的请求处理器）** 来实现这类任务，从而保证逻辑仍在 **Game Thread** 上执行。

---

## :material-arrow-right-circle: 下一步阅读

- 了解一次调用如何贯穿全链路：[数据流与同步](data_flow.md)
- 深入 UE 侧实现：[Unreal 服务端](server.md)
- 深入 SDK 侧实现：[Python 客户端](client.md)
- 查看可用接口：[API 文档](../api/index.md)
