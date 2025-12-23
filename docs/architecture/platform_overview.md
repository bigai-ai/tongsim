# :material-sitemap: System Overview

**TongSIM Lite** uses a **client–server** architecture:

- **Unreal Engine** hosts the simulation world (physics, navigation, rendering)
- A UE-side **gRPC server** exposes control/observation APIs
- The **Python SDK** connects to the server for training, evaluation, and scripting

This section explains **what runs where**, and how the core modules fit together.

!!! tip ":material-compass: When to read this"
    - You want a mental model of TongSIM Lite’s runtime
    - You are extending the gRPC API or adding a new capability
    - You are debugging connection, reset, or performance issues

---

## :material-layers: Components at a glance

| Component | Location | Responsibilities |
|---|---|---|
| Unreal project (simulation) | `unreal/TongSim_Lite.uproject` | Scenes, agents, physics, navigation, gameplay logic |
| TongSimCore (UE plugins) | `unreal/Plugins/TongSimCore` | Arena streaming, capture sensors, voxelization utilities |
| TongSimGrpc (UE plugins) | `unreal/Plugins/TongSimGrpc` | gRPC server runtime + service handlers (Arena/DemoRL/Capture/…) |
| Protocol definitions | `protobuf/tongsim_lite_protobuf/*.proto` | Cross-language contract for requests/responses |
| Python SDK | `src/tongsim` | Connection management, typed helpers, and higher-level APIs |

!!! note ":material-information-outline: Runtime mode"
    - In **Unreal Editor**, the gRPC server becomes available after you click **Play (PIE)**.
    - In a **packaged build**, the server starts with the game process.

---

## :material-transit-connection-variant: High-level diagram

```text
+-------------------------+           gRPC (protobuf)            +------------------------------+
| Python process          | <----------------------------------> | Unreal Engine (PIE/Packaged) |
|                         |                                      |                              |
| - tongsim.TongSim       |                                      | - World / physics / navmesh  |
| - WorldContext + loop   |                                      | - TongSimCore (sensors, etc) |
| - GrpcConnection/stubs  |                                      | - TongSimGrpc (gRPC server)  |
| - UnaryAPI / CaptureAPI |                                      |                              |
+-------------------------+                                      +------------------------------+
```

---

## :material-key-variant: Core concepts

### :material-controller-classic: UE is the source of truth

All world state (actors, transforms, collisions, navmesh) lives in **Unreal**. Python controls the world by sending gRPC requests such as:

- `DemoRLService/SpawnActor`, `SetActorTransform`, `NavigateToLocation`
- `ArenaService/LoadArena`, `ResetArena`, `LocalToWorld`
- `CaptureService/CaptureSnapshot` (RGB/depth capture)

### :material-fingerprint: Stable object identity (per session)

TongSIM Lite identifies Unreal `Actor` objects using a generated **FGuid**, serialized into `ObjectId.guid` (16 bytes).

!!! warning ":material-alert: Reset invalidates cached objects"
    A **map travel** or a full **reset** can destroy actors and rebuild the world. Cache IDs defensively and re-query when needed.

### :material-timer-sand: Multi-frame operations

Some operations take multiple frames (for example, level streaming or long movement). On the UE side these are implemented as **reactors** (tick-driven request handlers) so that gameplay logic still runs on the **game thread**.

---

## :material-arrow-right-circle: Where to go next

- Learn how requests execute: [Data Flow](data_flow.md)
- Understand the UE side: [Unreal Server](server.md)
- Understand the SDK side: [Python Client](client.md)
- Browse available APIs: [API Documentation](../api/index.md)
