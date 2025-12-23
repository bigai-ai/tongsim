# :material-layers: Multi-level System

TongSIM Lite supports loading multiple **Arena instances** into a single UE world using **level streaming**. This is a key building block for:

- parallel training (multiple isolated arenas in one process)
- fast reset (reload a single arena instance)
- coordinate-stable scripting (arena-local coordinates via an anchor)

---

## :material-puzzle-outline: What is an “Arena” in TongSIM Lite?

An **Arena** is an instance of a `UWorld` level asset streamed into the active world via `ULevelStreamingDynamic`. Each instance has:

- an `arena_id` (FGuid serialized in `ObjectId.guid`)
- an **anchor transform** (defines the arena-local frame)
- a streaming handle (load/visible state)

---

## :material-warehouse: UE-side building blocks

### :material-layers-triple: `UTSArenaSubsystem` (core arena manager)

`UTSArenaSubsystem` is a `UWorldSubsystem` that manages arena instances:

- load/reset/destroy arenas via `ULevelStreamingDynamic::LoadLevelInstanceBySoftObjectPtr`
- maintain `arena_id → streaming level + anchor` mappings
- convert transforms between **arena-local** and **world** space
- spawn actors into an arena level (`OverrideLevel`)

Key file:

- `unreal/Plugins/TongSimCore/Source/TongSimMultiLevel/Public/TSArenaSubsystem.h`
- `unreal/Plugins/TongSimCore/Source/TongSimMultiLevel/Private/TSArenaSubsystem.cpp`

### :material-connection: `UArenaGrpcSubsystem` (gRPC ArenaService)

`UArenaGrpcSubsystem` exposes Arena functionality to Python through gRPC:

- reactors: `LoadArena`, `ResetArena`, `DestroyArena`, `SimpleMoveTowardsInArena`
- unary: `ListArenas`, `SetArenaVisible`, coordinate conversion, spawn/pose helpers
- per-arena mutual exclusion via `BusyArenas` (prevents conflicting operations on the same arena)

Key file:

- `unreal/Plugins/TongSimGrpc/Source/TongSimProto/Private/DemoRL/ArenaGrpcSubsystem.cpp`

!!! note ":material-information-outline: Actor ID refresh"
    After arena load/reset/destroy completes, the server calls `UTSGrpcSubsystem::RefreshActorMappings()` so new actors can be addressed by `ObjectId`.

---

## :material-language-python: Python workflow

The SDK provides wrappers in `UnaryAPI` for `ArenaService`:

- `load_arena(level_asset_path, anchor, make_visible)`
- `reset_arena(arena_id)` / `destroy_arena(arena_id)`
- `list_arenas()` / `set_arena_visible(arena_id, visible)`
- `spawn_actor_in_arena(...)`, `set_actor_pose_local(...)`, `local_to_world(...)`, `world_to_local(...)`

### :material-code-braces: Minimal example

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

## :material-map-marker-radius: Coordinates (anchor-local vs world)

All arena APIs treat transforms as **arena-local** unless explicitly named “world”.

```text
world_transform = local_transform * anchor_transform
local_transform = world_transform.GetRelativeTransform(anchor_transform)
```

!!! tip ":material-compass: Recommended convention"
    Keep each arena authored around its local origin, then use anchors to position instances far apart.

---

## :material-checklist: Best practices & pitfalls

- **Avoid global volumes** inside arena sublevels (directional light, sky, post-process volumes), or you may get duplicates when multiple arenas are loaded.
- Prefer `reset_arena` for fast iteration; it recreates the streaming level while keeping the same `arena_id`.
- For parallel training, choose anchors that are far enough to avoid physics/navmesh interference.
- Expect resets to invalidate scene-local assumptions (actors can be recreated even if `arena_id` stays stable).

---

**Next:** [Voxel Perception Pipeline](voxel_perception.md)
