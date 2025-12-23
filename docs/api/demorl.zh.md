# Core Control

本页描述 TongSIM Lite 的**基础控制 API**：用于与 UE 世界中的 actor 交互，包括状态查询、生成/销毁、导航辅助、射线检测与控制台命令等。

!!! note ":material-information-outline: 命名说明"
    协议层这些方法由 `DemoRLService` 实现（见 `protobuf/tongsim_lite_protobuf/demo_rl.proto`）。尽管名字包含 “DemoRL”，但在 TongSIM Lite 中它承担的是**通用控制面**的角色。

## Key Functions

- `query_info`：获取当前世界中已追踪 actor 的状态快照列表。
- `reset_level`：重载当前关卡（触发 map travel）。
- `get_actor_state`：按 GUID 查询 actor 的位置、朝向向量、标签等元数据。
- `get_actor_transform` / `set_actor_transform`：读取/设置 actor 的 world transform。
- `spawn_actor` / `destroy_actor`：在当前世界中生成/销毁 actor。
- `simple_move_towards`：以恒速将 actor 朝目标点移动。
- `query_navigation_path`：查询两点间的 NavMesh 路径。
- `navigate_to_location`：使用 UE NavMesh 驱动角色移动到目标点。
- `pick_up_object` / `drop_object`：面向任务的交互 helper（需要关卡支持）。
- `exec_console_command`：执行 UE 控制台命令。
- `single_line_trace_by_object` / `multi_line_trace_by_object`：批量射线检测并返回命中信息。

## API References

::: tongsim.connection.grpc.unary_api.UnaryAPI.query_info

::: tongsim.connection.grpc.unary_api.UnaryAPI.reset_level

::: tongsim.connection.grpc.unary_api.UnaryAPI.get_actor_state

::: tongsim.connection.grpc.unary_api.UnaryAPI.get_actor_transform

::: tongsim.connection.grpc.unary_api.UnaryAPI.set_actor_transform

::: tongsim.connection.grpc.unary_api.UnaryAPI.spawn_actor

::: tongsim.connection.grpc.unary_api.UnaryAPI.destroy_actor

::: tongsim.connection.grpc.unary_api.UnaryAPI.simple_move_towards

::: tongsim.connection.grpc.unary_api.UnaryAPI.query_navigation_path

::: tongsim.connection.grpc.unary_api.UnaryAPI.navigate_to_location

::: tongsim.connection.grpc.unary_api.UnaryAPI.pick_up_object

::: tongsim.connection.grpc.unary_api.UnaryAPI.drop_object

::: tongsim.connection.grpc.unary_api.UnaryAPI.exec_console_command

::: tongsim.connection.grpc.unary_api.UnaryAPI.single_line_trace_by_object

::: tongsim.connection.grpc.unary_api.UnaryAPI.multi_line_trace_by_object
