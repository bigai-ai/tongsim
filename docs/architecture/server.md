# :material-server: Unreal Server

In TongSIM Lite, the “server” is the **Unreal Engine process** you run (Editor PIE or a packaged build). It owns the simulation world and hosts a **gRPC server** that executes requests safely on the **UE game thread**.

!!! note ":material-lan-connect: Default endpoint"
    The gRPC server binds to `0.0.0.0:5726` by default. The port is defined in `unreal/Plugins/TongSimGrpc/Source/TongosGrpc/Private/TSGrpcSubsystem.cpp`.

---

## :material-package-variant: UE modules you will touch

TongSIM Lite’s UE-side code is primarily split into two plugin groups:

| Plugin group | Location | What it provides |
|---|---|---|
| TongSimCore | `unreal/Plugins/TongSimCore` | Simulation utilities (arena streaming, capture cameras, voxelization) |
| TongSimGrpc | `unreal/Plugins/TongSimGrpc` | gRPC server runtime + service implementations |

---

## :material-connection: gRPC runtime & threading model

The core design principle is:

> **Network IO happens on gRPC worker threads, but all gameplay/world mutation happens on the UE game thread.**

```text
gRPC worker threads (IO)
  -> Channel<RpcEvent>
     -> UTSGrpcSubsystem::Tick()  [Game Thread]
        -> RpcRouter::handle()
           -> Unary handler OR Reactor (multi-frame)
```

### :material-router: `UTSGrpcSubsystem` (server lifecycle + routing)

`UTSGrpcSubsystem` is a `UGameInstanceSubsystem` and tickable object that:

- Starts the gRPC server (`tongos::RpcServer`) during `Initialize()`
- Receives incoming RPC events through a thread-safe channel
- Dispatches those events each frame on the game thread (`UpdateRpcRouter()` / `Tick()`)

Key files:

- `unreal/Plugins/TongSimGrpc/Source/TongosGrpc/Public/TSGrpcSubsystem.h`
- `unreal/Plugins/TongSimGrpc/Source/TongosGrpc/Private/TSGrpcSubsystem.cpp`

!!! tip ":material-shield-check: Why this matters"
    If you add a new API, keep the same rule: **don’t access `UWorld` from gRPC worker threads**.

---

## :material-fingerprint: Actor ID mapping (FGuid ↔ Actor)

To let Python refer to UE objects consistently, TongSIM Lite maintains a registry:

- Unreal `Actor` ⇄ generated `FGuid`
- `FGuid` is serialized into `ObjectId.guid` (16 bytes, little-endian layout for the first fields)

`UTSGrpcSubsystem`:

- Scans actors after world initialization
- Registers new actors on spawn
- Marks IDs as destroyed on `EndPlay` / `OnDestroyed`

This is what enables APIs like “get actor state by id” and “destroy actor by id”.

---

## :material-api: Services and their UE handlers

TongSIM Lite implements multiple gRPC services. Each service is wired by registering method names (for example `"/tongsim_lite.demo_rl.DemoRLService/QueryState"`) to either a **unary handler** or a **reactor**.

| Service | Proto | UE subsystem | Notes |
|---|---|---|---|
| Arena | `protobuf/tongsim_lite_protobuf/arena.proto` | `UArenaGrpcSubsystem` | Multi-level streaming + anchor transforms |
| DemoRL | `protobuf/tongsim_lite_protobuf/demo_rl.proto` | `UDemoRLSubsystem` | Spawn/query/move/navigation utilities |
| Voxel | `protobuf/tongsim_lite_protobuf/voxel.proto` | `UDemoRLSubsystem` | Voxel queries via `TSVoxelGridFuncLib` |
| Capture | `protobuf/tongsim_lite_protobuf/capture.proto` | `UCaptureGrpcSubsystem` | RGB/depth capture cameras + snapshots |

Key files:

- `unreal/Plugins/TongSimGrpc/Source/TongSimProto/Private/DemoRL/ArenaGrpcSubsystem.cpp`
- `unreal/Plugins/TongSimGrpc/Source/TongSimProto/Private/DemoRL/DemoRLSubsystem.cpp`
- `unreal/Plugins/TongSimGrpc/Source/TongSimProto/Private/Capture/CaptureGrpcSubsystem.cpp`

---

## :material-progress-clock: Reactors (multi-frame request handlers)

Some tasks cannot complete within a single frame, such as:

- Streaming a level in/out (arena load/reset/destroy)
- Long-running movement (move-towards, navmesh navigation)
- Waiting for a capture frame to be ready

For these, TongSIM Lite uses **reactors**:

- `onRequest(...)` captures parameters and starts the task
- `Tick(...)` advances the task each frame
- When ready, the reactor finishes and returns a response to the client

This keeps behavior deterministic with the game loop and avoids blocking the game thread.

---

## :material-hammer-wrench: Extending the UE server

=== ":material-file-code-outline: Add a new RPC"

    1. Define the request/response in `protobuf/tongsim_lite_protobuf/*.proto`.
    2. Regenerate code for Python and UE (see `scripts/generate_pb2.py` for Python; UE uses generated headers under `tongsim_lite_protobuf/*.pb.h`).
    3. Implement a unary handler or reactor in `unreal/Plugins/TongSimGrpc/Source/TongSimProto`.
    4. Register the method name via `UTSGrpcSubsystem::RegisterUnaryHandler` / `RegisterReactor`.

=== ":material-bug-outline: Debug an existing RPC"

    - Confirm you are in **PIE** (Editor) and the server is listening on the expected port.
    - Add UE logs in the corresponding subsystem (DemoRL/Arena/Capture).
    - Check whether the call is **unary** (should return immediately) or **reactor** (waits over multiple frames).

---

**Next:** [Python Client](client.md)
