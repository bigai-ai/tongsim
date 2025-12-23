# Arena

Arena API 通过 `UnaryAPI` 暴露多关卡（streaming）生命周期与 arena-local 坐标系下的 actor 工具。

## Key Functions

- `load_arena`：按关卡资产路径加载一个 arena，并返回 arena GUID。
- `reset_arena` / `destroy_arena`：重置或销毁指定 GUID 的 arena。
- `list_arenas`：列出当前已加载的 arena（包含可见性与 actor 数量等）。
- `set_arena_visible`：切换某个 arena 是否参与渲染与逻辑。
- `spawn_actor_in_arena`：在 arena-local 坐标系中生成 actor。
- `set_actor_pose_local` / `get_actor_pose_local`：读写 arena-local transform。
- `local_to_world` / `world_to_local`：arena-local 与 world 的 transform 转换。
- `arena_simple_move_towards`：在 arena-local 坐标系下的移动 helper。
- `arena_destroy_actor`：销毁 arena 内生成的 actor。

## API References

::: tongsim.connection.grpc.unary_api.UnaryAPI.load_arena

::: tongsim.connection.grpc.unary_api.UnaryAPI.reset_arena

::: tongsim.connection.grpc.unary_api.UnaryAPI.destroy_arena

::: tongsim.connection.grpc.unary_api.UnaryAPI.list_arenas

::: tongsim.connection.grpc.unary_api.UnaryAPI.set_arena_visible

::: tongsim.connection.grpc.unary_api.UnaryAPI.spawn_actor_in_arena

::: tongsim.connection.grpc.unary_api.UnaryAPI.set_actor_pose_local

::: tongsim.connection.grpc.unary_api.UnaryAPI.get_actor_pose_local

::: tongsim.connection.grpc.unary_api.UnaryAPI.local_to_world

::: tongsim.connection.grpc.unary_api.UnaryAPI.world_to_local

::: tongsim.connection.grpc.unary_api.UnaryAPI.arena_simple_move_towards

::: tongsim.connection.grpc.unary_api.UnaryAPI.arena_destroy_actor
