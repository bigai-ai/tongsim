# Core Control

This page documents TongSIM Lite’s **baseline control API** for interacting with
gameplay actors: querying state, spawning/destroying actors, navigation helpers,
physics traces, and UE console commands.

!!! note ":material-information-outline: Naming note"
    In the protocol, these methods are implemented by `DemoRLService` (see
    `protobuf/tongsim_lite_protobuf/demo_rl.proto`). Despite the proto name,
    the API is used as the **general-purpose** control surface in TongSIM Lite.

## Key Functions

- `query_info`: Fetch aggregated actor snapshots, including every tracked actor.
- `reset_level`: Reload the current level to its initial state (map travel).
- `get_actor_state`: Retrieve an actor's position, orientation vectors, and tag
  metadata by GUID.
- `get_actor_transform` / `set_actor_transform`: Read or update an actor's
  world transform.
- `spawn_actor` / `destroy_actor`: Create or remove actors in the current world.
- `simple_move_towards`: Move an actor toward a world target with a constant
  speed helper.
- `query_navigation_path`: Ask the UE navigation system for a path between two
  world locations.
- `navigate_to_location`: Move a character using UE NavMesh navigation.
- `pick_up_object` / `drop_object`: Task-oriented interaction helpers (level
  support required).
- `exec_console_command`: Execute arbitrary UE console commands on the server.
- `single_line_trace_by_object` / `multi_line_trace_by_object`: Perform physics
  traces and gather hit information.

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
