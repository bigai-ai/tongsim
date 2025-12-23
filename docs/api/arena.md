# Arena

Arena APIs expose level lifecycle and local-space actor utilities through
`UnaryAPI`.

## Key Functions

- `load_arena`: Load an arena level asset using an anchor transform and return
  the arena GUID.
- `reset_arena` / `destroy_arena`: Reset or tear down an arena identified by
  its GUID.
- `list_arenas`: Inspect all arenas currently loaded on the server, including
  visibility and actor counts.
- `set_arena_visible`: Toggle whether an arena participates in rendering and
  gameplay logic.
- `spawn_actor_in_arena`: Spawn an actor inside the arena's local coordinate
  system.
- `set_actor_pose_local` / `get_actor_pose_local`: Write or read an actor's
  transform expressed in local arena coordinates.
- `local_to_world` / `world_to_local`: Convert transforms between arena-local
  and world space.
- `arena_simple_move_towards`: Drive a pawn toward a target in arena-local
  space using the built-in simple movement helper.
- `arena_destroy_actor`: Remove an actor from the arena.

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
