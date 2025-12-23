# :material-waterfall: Data Flow

This page explains how a TongSIM Lite request travels from **Python** to **Unreal**, how the platform stays **thread-safe**, and what “synchronization” means for multi-frame tasks.

!!! tip ":material-bug-outline: Use this page when debugging"
    - A call “hangs” (likely a reactor waiting for world progress)
    - You get `UNAVAILABLE` / `DEADLINE_EXCEEDED`
    - Actor IDs look “stale” after a reset or level travel

---

## :material-source-branch: One RPC, end-to-end

TongSIM Lite is designed so that **IO is asynchronous**, but **world logic is deterministic and game-thread-owned**.

```text
Python (your code)
  -> WorldContext.sync_run(coro)
     -> AsyncLoop thread (asyncio)
        -> grpc.aio stub.SomeRpc(...)
           -> network
              -> UE gRPC worker thread(s) (IO only)
                 -> Channel<RpcEvent>
                    -> UTSGrpcSubsystem::Tick() [Game Thread]
                       -> handler/reactor
                          -> response
```

---

## :material-swap-horizontal: Unary vs Reactor

=== ":material-flash: Unary (single-step)"

    Unary handlers run on the **game thread** and return a response immediately (within the same tick), for example:

    - `DemoRLService/QueryState`
    - `DemoRLService/SpawnActor`
    - `ArenaService/ListArenas`

    ```text
    Frame N:
      - router dispatches request
      - handler runs, reads/writes world state
      - response is returned
    ```

=== ":material-progress-clock: Reactor (multi-frame)"

    Reactors are used when an operation needs **multiple frames** to complete, for example:

    - `DemoRLService/ResetLevel`
    - `DemoRLService/NavigateToLocation`
    - `ArenaService/LoadArena`
    - `CaptureService/CaptureSnapshot`

    ```text
    Frame N:
      - reactor.onRequest() captures parameters
    Frame N..M:
      - reactor.Tick() advances the task each frame
    Frame M:
      - reactor finishes and returns the response
    ```

!!! note ":material-information-outline: Why reactors exist"
    Unreal gameplay and streaming are frame-based. Reactors let TongSIM Lite “wait for completion” without blocking the game thread.

---

## :material-home-import-outline: Arena streaming flow (multi-level)

Arena operations are implemented on top of UE streaming levels:

1. Python calls `ArenaService/LoadArena(level_asset_path, anchor, make_visible)`.
2. UE creates a streaming level via `UTSArenaSubsystem::LoadArena(...)`.
3. The load reactor periodically checks `UTSArenaSubsystem::IsArenaReady(...)`.
4. When ready, UE returns an `arena_id` (FGuid in `ObjectId.guid`).

!!! tip ":material-map-marker-radius: Anchors define local coordinates"
    Arena APIs expose `LocalToWorld` / `WorldToLocal` so your client logic can operate in a stable **arena-local** frame.

---

## :material-restore: Level reset / map travel

Some flows reset the entire world (or large parts of it). For example, `DemoRLService/ResetLevel` triggers a level travel and waits for the new world to become ready.

Practical consequences:

- Existing actor references may be destroyed
- The Actor GUID registry is rebuilt after world initialization
- Client-side caches should be treated as invalid after reset/travel

!!! warning ":material-alert: Treat reset as a boundary"
    If you keep IDs, streams, or state across resets, make sure you can detect invalidation and re-discover what you need.

---

## :material-sync: What “synchronization” means here

- **UE side**: requests are executed on the game thread; long work should be expressed as reactors that make progress each frame.
- **Python side**: you can write synchronous code (`sync_run`) while the SDK uses an async loop underneath.
- **Concurrency**: multiple RPCs can be in-flight, but world mutations are serialized by the game thread router.

---

## :material-checklist: Practical tips

- Prefer smaller, well-scoped requests (avoid huge “query everything” calls every frame).
- Use explicit timeouts for long operations (navigation, streaming, capture).
- For large payloads (images/voxels), keep an eye on message sizes; the Python channel is configured with a 100MB send/receive limit in `src/tongsim/connection/grpc/core.py`.

---

**Next:** [System Overview](platform_overview.md)
