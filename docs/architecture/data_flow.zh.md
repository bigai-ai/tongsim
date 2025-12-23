# :material-waterfall: 数据流与同步

本页说明一次 TongSIM Lite 调用如何从 **Python** 传到 **Unreal** 并返回，以及平台如何保证 **线程安全**、如何理解“**同步**”与“**多帧任务**”。

!!! tip ":material-bug-outline: 排查问题时可先看这里"
    - 调用“卡住”（通常是 reactor 在等待世界推进）
    - 看到 `UNAVAILABLE` / `DEADLINE_EXCEEDED`
    - 重置/切关卡后 actor id 看起来“失效”

---

## :material-source-branch: 一次 RPC 的端到端链路

TongSIM Lite 的设计目标是：**IO 异步化**，但 **世界逻辑在 Game Thread 上确定性执行**。

```text
Python（你的代码）
  -> WorldContext.sync_run(coro)
     -> AsyncLoop 线程（asyncio）
        -> grpc.aio stub.SomeRpc(...)
           -> network
              -> UE gRPC 工作线程（仅处理 IO）
                 -> Channel<RpcEvent>
                    -> UTSGrpcSubsystem::Tick() [Game Thread]
                       -> handler / reactor
                          -> response
```

---

## :material-swap-horizontal: Unary 与 Reactor

=== ":material-flash: Unary（单步调用）"

    Unary handler 在 **Game Thread** 上执行，并在同一帧内快速返回，例如：

    - `DemoRLService/QueryState`
    - `DemoRLService/SpawnActor`
    - `ArenaService/ListArenas`

    ```text
    Frame N:
      - router 分发请求
      - handler 执行（读写世界状态）
      - 返回响应
    ```

=== ":material-progress-clock: Reactor（多帧调用）"

    当操作需要跨多帧完成时，会使用 reactor，例如：

    - `DemoRLService/ResetLevel`
    - `DemoRLService/NavigateToLocation`
    - `ArenaService/LoadArena`
    - `CaptureService/CaptureSnapshot`

    ```text
    Frame N:
      - reactor.onRequest() 接收并缓存参数
    Frame N..M:
      - reactor.Tick() 每帧推进任务
    Frame M:
      - reactor 满足完成条件后回包
    ```

!!! note ":material-information-outline: 为什么需要 reactor"
    Unreal 的 Gameplay / Streaming 都是按帧推进的。reactor 允许“等待完成”，但不会阻塞 Game Thread。

---

## :material-home-import-outline: Arena 流式加载的数据流

Arena 系列接口建立在 UE 的 Streaming Level 上：

1. Python 调用 `ArenaService/LoadArena(level_asset_path, anchor, make_visible)`。
2. UE 通过 `UTSArenaSubsystem::LoadArena(...)` 创建并加载 Streaming Level。
3. Load reactor 周期性检查 `UTSArenaSubsystem::IsArenaReady(...)`。
4. Arena 就绪后返回 `arena_id`（`ObjectId.guid` 中的 FGuid）。

!!! tip ":material-map-marker-radius: Anchor 定义局部坐标系"
    Arena 提供 `LocalToWorld` / `WorldToLocal`，便于在稳定的 **arena-local** 坐标系下编写客户端逻辑。

---

## :material-restore: Level 重置 / 地图切换（Travel）

某些流程会重置大部分甚至整个世界。例如 `DemoRLService/ResetLevel` 会触发地图切换，并等待新世界就绪。

实际影响包括：

- 旧的 Actor 可能被销毁
- Actor GUID 注册表会在 World 初始化后重建
- 客户端侧的缓存应视为失效

!!! warning ":material-alert: 将 reset 视为“边界”"
    如果你跨 reset 保存了 id/流/状态，请确保能检测失效并重新发现所需对象。

---

## :material-sync: 这里的“同步”到底指什么

- **UE 侧**：请求都在 Game Thread 执行；耗时任务用 reactor 逐帧推进。
- **Python 侧**：你可以写同步代码（`sync_run`），底层由异步 loop 负责调度。
- **并发**：可以同时发起多个 RPC，但对世界状态的修改会被 Game Thread 路由器串行化处理。

---

## :material-checklist: 实用建议

- 尽量将请求拆小、明确（避免每帧都“全量查询”）。
- 对长任务设置超时（导航、Streaming、采集等）。
- 大数据（图像/体素）要关注消息大小；Python 端在 `src/tongsim/connection/grpc/core.py` 将单次收发限制配置为 100MB。

---

**下一步：** [系统架构概览](platform_overview.md)
