# :material-layers: 多层关卡系统

TongSIM Lite 支持在同一个 UE World 中通过 **Level Streaming** 加载多个 **Arena 实例**。它是实现以下能力的基础：

- 并行训练（一个进程内加载多个相互隔离的 arena）
- 快速复位（仅重载某个 arena 实例）
- 稳定坐标系（通过 anchor 提供 arena-local 坐标）

---

## :material-puzzle-outline: TongSIM Lite 里的 Arena 是什么？

在 TongSIM Lite 中，**Arena** 本质上是一个 `UWorld` 关卡资产的“实例”，通过 `ULevelStreamingDynamic` 被加载到当前世界中。每个实例包含：

- `arena_id`（FGuid，序列化到 `ObjectId.guid`）
- **anchor transform**（定义 arena-local 坐标系）
- streaming 句柄（loaded/visible 状态）

---

## :material-warehouse: UE 侧核心模块

### :material-layers-triple: `UTSArenaSubsystem`（Arena 核心管理）

`UTSArenaSubsystem` 是一个 `UWorldSubsystem`，负责：

- 通过 `ULevelStreamingDynamic::LoadLevelInstanceBySoftObjectPtr` 加载/重置/销毁 arena
- 维护 `arena_id → Streaming + Anchor` 的映射
- 在 **arena-local** 与 **world** 坐标系之间做变换
- 在指定 arena 的 `ULevel` 中生成 actor（`OverrideLevel`）

关键文件：

- `unreal/Plugins/TongSimCore/Source/TongSimMultiLevel/Public/TSArenaSubsystem.h`
- `unreal/Plugins/TongSimCore/Source/TongSimMultiLevel/Private/TSArenaSubsystem.cpp`

### :material-connection: `UArenaGrpcSubsystem`（gRPC 的 ArenaService）

`UArenaGrpcSubsystem` 将 Arena 能力通过 gRPC 暴露给 Python：

- reactors：`LoadArena`、`ResetArena`、`DestroyArena`、`SimpleMoveTowardsInArena`
- unary：`ListArenas`、`SetArenaVisible`、坐标转换、spawn/pose 等
- 通过 `BusyArenas` 做单 arena 互斥（避免同一 arena 上的冲突操作）

关键文件：

- `unreal/Plugins/TongSimGrpc/Source/TongSimProto/Private/DemoRL/ArenaGrpcSubsystem.cpp`

!!! note ":material-information-outline: Actor ID 刷新"
    Arena 的 load/reset/destroy 完成后，服务端会调用 `UTSGrpcSubsystem::RefreshActorMappings()`，确保新加载的 actor 可通过 `ObjectId` 被寻址。

---

## :material-language-python: Python 侧常见用法

SDK 在 `UnaryAPI` 中提供了对 `ArenaService` 的封装：

- `load_arena(level_asset_path, anchor, make_visible)`
- `reset_arena(arena_id)` / `destroy_arena(arena_id)`
- `list_arenas()` / `set_arena_visible(arena_id, visible)`
- `spawn_actor_in_arena(...)`、`set_actor_pose_local(...)`、`local_to_world(...)`、`world_to_local(...)`

### :material-code-braces: 最小示例

```python
from tongsim import TongSim
from tongsim.connection.grpc.unary_api import UnaryAPI
from tongsim.math import Transform, Vector3

LEVEL = "/Game/Maps/Sublevels/MyArena.MyArena"

with TongSim("127.0.0.1:5726") as ts:
    a0 = ts.context.sync_run(
        UnaryAPI.load_arena(ts.context.conn, LEVEL, anchor=Transform(location=Vector3(0, 0, 0)))
    )
    a1 = ts.context.sync_run(
        UnaryAPI.load_arena(ts.context.conn, LEVEL, anchor=Transform(location=Vector3(5000, 0, 0)))
    )
    ts.context.sync_run(UnaryAPI.set_arena_visible(ts.context.conn, a1, visible=False))
    print("arenas:", ts.context.sync_run(UnaryAPI.list_arenas(ts.context.conn)))
```

---

## :material-map-marker-radius: 坐标系（arena-local 与 world）

Arena 系列接口默认在 **arena-local** 坐标系下工作，除非接口名明确写了 “world”。

```text
world_transform = local_transform * anchor_transform
local_transform = world_transform.GetRelativeTransform(anchor_transform)
```

!!! tip ":material-compass: 推荐约定"
    制作关卡时把内容放在局部原点附近；并行训练时用 anchor 将实例摆放到足够远的位置。

---

## :material-checklist: 最佳实践与常见坑

- 子关卡内尽量避免放置全局性对象（方向光、天空、后处理体积等），多实例加载时会重复叠加。
- 优先使用 `reset_arena` 做快速迭代；它会重建 streaming level，但保持 `arena_id` 不变。
- 并行训练时，anchor 之间保持足够距离，避免物理/导航互相干扰。
- reset 后请假设场景状态被重建（即使 `arena_id` 稳定，actor 也可能被重新创建）。

---

**下一步：** [体素感知管线](voxel_perception.md)
