from tongsim.math import Transform, Vector3
from tongsim.type.rl_demo import RLDemoHandType, RLDemoOrientationMode
from tongsim_lite_protobuf.arena_pb2 import (
    DestroyActorInArenaRequest,
    DestroyArenaRequest,
    GetActorPoseLocalRequest,
    GetActorPoseLocalResponse,
    ListArenasRequest,
    ListArenasResponse,
    LoadArenaRequest,
    LoadArenaResponse,
    LocalToWorldRequest,
    LocalToWorldResponse,
    ResetArenaRequest,
    SetActorPoseLocalRequest,
    SetArenaVisibleRequest,
    SimpleMoveTowardsInArenaRequest,
    SimpleMoveTowardsInArenaResponse,
    SpawnActorInArenaRequest,
    SpawnActorInArenaResponse,
    WorldToLocalRequest,
    WorldToLocalResponse,
)
from tongsim_lite_protobuf.arena_pb2_grpc import ArenaServiceStub
from tongsim_lite_protobuf.common_pb2 import Empty
from tongsim_lite_protobuf.demo_rl_pb2 import (
    ActorState,
    BatchMultiLineTraceByObjectRequest,
    BatchSingleLineTraceByObjectRequest,
    DemoRLState,
    DestroyActorRequest,
    DropObjectRequest,
    DropObjectResponse,
    ExecConsoleCommandRequest,
    ExecConsoleCommandResponse,
    GetActorStateRequest,
    GetActorStateResponse,
    GetActorTransformRequest,
    GetActorTransformResponse,
    NavigateToLocationRequest,
    NavigateToLocationResponse,
    PickUpObjectRequest,
    PickUpObjectResponse,
    QueryNavigationPathRequest,
    QueryNavigationPathResponse,
    SetActorTransformRequest,
    SimpleMoveTowardsRequest,
    SimpleMoveTowardsResponse,
    SpawnActorRequest,
    SpawnActorResponse,
)
from tongsim_lite_protobuf.demo_rl_pb2_grpc import DemoRLServiceStub
from tongsim_lite_protobuf.object_pb2 import ObjectId
from tongsim_lite_protobuf.voxel_pb2 import QueryVoxelRequest, Voxel
from tongsim_lite_protobuf.voxel_pb2_grpc import VoxelServiceStub

from .core import GrpcConnection
from .utils import proto_to_sdk, safe_async_rpc, sdk_to_proto

# --------------------------
# GUID helpers (UE FGuid LE)
# --------------------------


def _fguid_bytes_to_str(guid_bytes: bytes) -> str:
    """
    Convert Unreal FGuid (16 bytes; first 3 fields little-endian) to canonical
    GUID string: 8-4-4-4-12 uppercase hex.

    Layout (Windows/MS GUID):
      Data1[4] LE, Data2[2] LE, Data3[2] LE, Data4[8] BE(as-is)
    """
    if not guid_bytes:
        return ""
    if len(guid_bytes) != 16:
        return guid_bytes.hex().upper()

    d1 = guid_bytes[0:4][::-1]  # LE -> BE
    d2 = guid_bytes[4:6][::-1]
    d3 = guid_bytes[6:8][::-1]
    d4 = guid_bytes[8:10]  # as-is
    d5 = guid_bytes[10:16]  # as-is
    return f"{d1.hex()}-{d2.hex()}-{d3.hex()}-{d4.hex()}-{d5.hex()}".upper()


def _guid_str_to_fguid_bytes(guid_str: str) -> bytes:
    """
    Convert canonical GUID string (8-4-4-4-12) to Unreal FGuid bytes
    with first 3 fields little-endian.
    """
    if not guid_str:
        return b""
    s = guid_str.replace("-", "").strip()
    if len(s) != 32:
        # Try raw hex fallback
        try:
            b = bytes.fromhex(s)
            return b if len(b) == 16 else b""
        except Exception:
            return b""

    try:
        raw = bytes.fromhex(s)
        # raw = [Data1(4) | Data2(2) | Data3(2) | Data4(8)] all BE
        d1 = raw[0:4][::-1]  # -> LE
        d2 = raw[4:6][::-1]
        d3 = raw[6:8][::-1]
        d4 = raw[8:16]  # as-is
        return d1 + d2 + d3 + d4
    except Exception:
        return b""


def _to_object_id(actor_id: bytes | str | dict) -> ObjectId:
    """
    Build ObjectId from:
      - bytes (len==16, UE FGuid layout), or
      - canonical GUID str "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX", or
      - dict {"guid": <bytes|str>}
    """
    if isinstance(actor_id, dict):
        actor_id = actor_id.get("guid", b"")

    oid = ObjectId()
    if isinstance(actor_id, bytes | bytearray):
        guid_bytes = bytes(actor_id)
    elif isinstance(actor_id, str):
        guid_bytes = _guid_str_to_fguid_bytes(actor_id)
    else:
        guid_bytes = b""

    if not guid_bytes or len(guid_bytes) != 16:
        raise ValueError("actor_id must be 16-byte FGuid or canonical GUID string.")

    oid.guid = guid_bytes
    return oid


def _actor_state_to_dict(actor: ActorState) -> dict:
    """Convert a protobuf ActorState into the SDK-friendly dictionary format."""
    return {
        "id": _fguid_bytes_to_str(actor.object_info.id.guid),
        "name": actor.object_info.name,
        "class_path": actor.object_info.class_path,
        "location": proto_to_sdk(actor.location),
        "unit_forward_vector": proto_to_sdk(actor.unit_forward_vector),
        "unit_right_vector": proto_to_sdk(actor.unit_right_vector),
        "bounding_box": {
            "min": proto_to_sdk(actor.bounding_box.min_vertex),
            "max": proto_to_sdk(actor.bounding_box.max_vertex),
        },
        "tag": actor.tag,
        "destroyed": bool(getattr(actor, "destroyed", False)),
        "current_speed": float(getattr(actor, "current_speed", 0.0)),
    }


# --------------------------
# Public gRPC unary wrappers
# --------------------------


class UnaryAPI:
    """Wrap DemoRLService and ArenaService unary RPC endpoints for Python clients."""

    @staticmethod
    @safe_async_rpc(default=[])
    async def query_info(conn: GrpcConnection) -> list[dict]:
        """
        Fetch state snapshots for every actor in the current Demo RL scene.

        Returns:
            list[dict]: One entry per actor with GUID, name, class path,
                location vectors, basis vectors, bounding box and tag metadata.
        """
        stub = conn.get_stub(DemoRLServiceStub)
        resp: DemoRLState = await stub.QueryState(Empty(), timeout=2.0)

        result: list[dict] = []
        for actor in resp.actor_states:
            result.append(_actor_state_to_dict(actor))
        return result

    @staticmethod
    @safe_async_rpc(default=False)
    async def reset_level(conn: GrpcConnection, timeout: float = 60.0) -> bool:
        """Reset the active Demo RL level."""
        stub = conn.get_stub(DemoRLServiceStub)
        await stub.ResetLevel(Empty(), timeout=timeout)
        return True

    @staticmethod
    @safe_async_rpc(default=(None, None))
    async def simple_move_towards(
        conn: GrpcConnection,
        target_location: Vector3,
        actor_id: bytes | str | dict,
        orientation_mode: RLDemoOrientationMode = RLDemoOrientationMode.ORIENTATION_KEEP_CURRENT,
        given_forward: Vector3 | None = None,
        timeout: float = 3600.0,
        speed_uu_per_sec: float = 300.0,
        tolerance_uu: float = 5.0,
    ) -> tuple[dict | None, dict | None]:
        """
        Move an actor toward the given world-space target using the simple mover.

        Args:
            target_location (Vector3): Destination in world coordinates.
            actor_id (bytes | str | dict): Actor identifier (FGuid bytes or GUID string).
            orientation_mode (RLDemoOrientationMode): Orientation strategy applied during movement.
            given_forward (Vector3 | None): Forward vector used when orientation_mode is ORIENTATION_GIVEN.
            timeout (float): RPC timeout in seconds.
            speed_uu_per_sec (float): Movement speed in Unreal units per second.
            tolerance_uu (float): Distance threshold treated as arrival.

        Returns:
            tuple[Vector3 | None, dict | None]: Current location and optional hit metadata with ``hit_actor`` when blocked.
        """
        req = SimpleMoveTowardsRequest(
            actor_id=_to_object_id(actor_id),
            target_location=sdk_to_proto(target_location),
            orientation_mode=orientation_mode,
            speed_uu_per_sec=float(speed_uu_per_sec),
            tolerance_uu=float(tolerance_uu),
        )

        if (
            orientation_mode == RLDemoOrientationMode.ORIENTATION_GIVEN
            and given_forward is not None
        ):
            req.given_orientation.CopyFrom(sdk_to_proto(given_forward))

        stub = conn.get_stub(DemoRLServiceStub)
        resp: SimpleMoveTowardsResponse = await stub.SimpleMoveTowards(
            req, timeout=timeout
        )

        current_location = proto_to_sdk(resp.current_location)

        hit_result = None
        if resp.HasField("hit_result"):
            hit_result = {"hit_actor": (resp.hit_result.hit_actor)}

        return current_location, hit_result

    @staticmethod
    @safe_async_rpc(default=None)
    async def get_actor_state(conn: GrpcConnection, actor_id: str) -> dict | None:
        """
        Fetch the state of a single actor by identifier.

        Returns:
            dict | None: Actor metadata dictionary, or ``None`` on failure.
        """
        stub = conn.get_stub(DemoRLServiceStub)
        req = GetActorStateRequest(actor_id=_to_object_id(actor_id))
        resp: GetActorStateResponse = await stub.GetActorState(req, timeout=2.0)
        return _actor_state_to_dict(resp.actor_state)

    @staticmethod
    @safe_async_rpc(default=None)
    async def get_actor_transform(conn: GrpcConnection, actor_id: str) -> Transform:
        """
        Retrieve an actor's world transform.

        Returns:
            Transform | None: World transform, or ``None`` on failure.
        """
        stub = conn.get_stub(DemoRLServiceStub)
        req = GetActorTransformRequest(actor_id=_to_object_id(actor_id))
        resp: GetActorTransformResponse = await stub.GetActorTransform(req, timeout=2.0)
        return proto_to_sdk(resp.transform)

    @staticmethod
    @safe_async_rpc(default=False)
    async def set_actor_transform(
        conn: GrpcConnection, actor_id: bytes | str | dict, transform: Transform
    ) -> bool:
        """
        Teleport an actor to the supplied world transform (TeleportPhysics).

        Returns:
            bool: True on success.
        """
        stub = conn.get_stub(DemoRLServiceStub)
        req = SetActorTransformRequest(
            actor_id=_to_object_id(actor_id),
            transform=sdk_to_proto(transform),
        )
        await stub.SetActorTransform(req, timeout=2.0)
        return True

    @staticmethod
    @safe_async_rpc(default=None)
    async def spawn_actor(
        conn: GrpcConnection,
        blueprint: str,
        transform: Transform,
        name: str | None = None,
        tags: list[str] | None = None,
        timeout: float = 5.0,
    ) -> dict | None:
        """
        Spawn an actor in the Demo RL scene and return its identity information.

        Returns:
            dict | None: Dictionary with ``id``, ``name`` and ``class_path``.
        """
        stub = conn.get_stub(DemoRLServiceStub)
        req = SpawnActorRequest(
            blueprint=blueprint,
            transform=sdk_to_proto(transform),
        )
        if name:
            req.name = name
        if tags:
            req.tags.extend(tags)

        resp: SpawnActorResponse = await stub.SpawnActor(req, timeout=timeout)
        ai = resp.actor
        return {
            "id": _fguid_bytes_to_str(ai.id.guid),
            "name": ai.name,
            "class_path": ai.class_path,
        }

    @staticmethod
    @safe_async_rpc(default=None)
    async def query_voxel(
        conn: GrpcConnection,
        transform: Transform,
        voxel_num_x: int,
        voxel_num_y: int,
        voxel_num_z: int,
        box_extent: Vector3,
        actors_to_ignore: list[str] | None = None,
        timeout: float = 5.0,
    ) -> bytes:
        """
        Query voxel occupancy around a transform and return the raw buffer.

        Args:
            transform (Transform): World transform at the center of the volume.
            voxel_num_x (int): Number of samples along the X axis.
            voxel_num_y (int): Number of samples along the Y axis.
            voxel_num_z (int): Number of samples along the Z axis.
            box_extent (Vector3): Half-extent of the query box in world units.
            actors_to_ignore (list[str] | None): Optional actor IDs excluded from sampling.
            timeout (float): RPC timeout in seconds.

        Returns:
            bytes: Serialized voxel data provided by the service.
        """
        if actors_to_ignore is None:
            actors_to_ignore = []

        stub = conn.get_stub(VoxelServiceStub)
        req = QueryVoxelRequest(
            transform=sdk_to_proto(transform),
            voxel_num_x=voxel_num_x,
            voxel_num_y=voxel_num_y,
            voxel_num_z=voxel_num_z,
            extent=sdk_to_proto(box_extent),
            ActorsToIgnore=[_to_object_id(actor_id) for actor_id in actors_to_ignore],
        )
        resp: Voxel = await stub.QueryVoxel(req, timeout=2.0)
        return resp.voxel_buffer

    @staticmethod
    @safe_async_rpc(default=False)
    async def exec_console_command(
        conn: GrpcConnection,
        command: str,
        write_to_log: bool = True,
        timeout: float = 2.0,
    ) -> bool:
        """
        Execute a UE console command such as ``stat fps`` or ``r.Streaming.PoolSize 4000``.

        Returns:
            bool: True when the command was accepted (console output text is unavailable).
        """
        stub = conn.get_stub(DemoRLServiceStub)
        req = ExecConsoleCommandRequest(command=command, write_to_log=write_to_log)
        resp: ExecConsoleCommandResponse = await stub.ExecConsoleCommand(
            req, timeout=timeout
        )
        return bool(resp.success)

    @staticmethod
    @safe_async_rpc(default=None)
    async def query_navigation_path(
        conn: GrpcConnection,
        start: Vector3,
        end: Vector3,
        allow_partial: bool = True,
        require_navigable_end_location: bool = False,
        cost_limit: float | None = None,
        timeout: float = 2.0,
    ) -> dict | None:
        """
        Compute a navigation path between two world positions using the UE navigation system.

        Args:
            start (Vector3): Starting world location.
            end (Vector3): Target world location.
            allow_partial (bool): Allow returning partial paths when a full path is unavailable.
            require_navigable_end_location (bool): Enforce the end point to lie on the navmesh.
            cost_limit (float | None): Optional cost threshold; values <= 0 disable it.
            timeout (float): RPC timeout in seconds.

        Returns:
            dict: Path data including ``points`` (list[Vector3]), ``is_partial`` (bool), ``path_cost`` (float) and ``path_length`` (float).
        """
        stub = conn.get_stub(DemoRLServiceStub)
        req = QueryNavigationPathRequest(
            start=sdk_to_proto(start),
            end=sdk_to_proto(end),
            allow_partial=allow_partial,
            require_navigable_end_location=require_navigable_end_location,
        )
        if cost_limit is not None and cost_limit > 0:
            req.cost_limit = float(cost_limit)

        resp: QueryNavigationPathResponse = await stub.QueryNavigationPath(
            req, timeout=timeout
        )
        return {
            "points": [proto_to_sdk(p) for p in resp.path_points],
            "is_partial": bool(resp.is_partial),
            "path_cost": float(resp.path_cost) if hasattr(resp, "path_cost") else 0.0,
            "path_length": float(resp.path_length)
            if hasattr(resp, "path_length")
            else 0.0,
        }

    @staticmethod
    @safe_async_rpc(default=None)
    async def navigate_to_location(
        conn: GrpcConnection,
        actor_id: bytes | str | dict,
        target_location: Vector3,
        accept_radius: float,
        allow_partial: bool = True,
        speed_uu_per_sec: float | None = None,
        timeout: float = 3600.0,
    ) -> dict | None:
        """
        Navigate a Character to a location using UE NavMesh (server-side async Reactor).

        Returns:
            dict: ``success``, ``message``, ``final_location`` and ``is_partial``.
        """
        stub = conn.get_stub(DemoRLServiceStub)
        req = NavigateToLocationRequest(
            actor_id=_to_object_id(actor_id),
            target_location=sdk_to_proto(target_location),
            accept_radius=float(accept_radius),
            allow_partial=bool(allow_partial),
        )
        if speed_uu_per_sec is not None:
            req.speed_uu_per_sec = float(speed_uu_per_sec)
        resp: NavigateToLocationResponse = await stub.NavigateToLocation(
            req, timeout=timeout
        )
        return {
            "success": bool(resp.success),
            "message": str(resp.message),
            "final_location": proto_to_sdk(resp.final_location),
            "is_partial": bool(resp.is_partial),
        }

    @staticmethod
    @safe_async_rpc(default={"success": False, "message": ""})
    async def pick_up_object(
        conn: GrpcConnection,
        actor_id: bytes | str | dict,
        target_object_id: bytes | str | dict,
        target_object_location: Vector3 | None = None,
        hand: RLDemoHandType = RLDemoHandType.HAND_RIGHT,
        timeout: float = 5.0,
    ) -> dict:
        """
        Request the UE server to pick up the specified target actor.
        """
        stub = conn.get_stub(DemoRLServiceStub)
        req = PickUpObjectRequest(
            actor_id=_to_object_id(actor_id),
            hand=int(hand),
            target_object_id=_to_object_id(target_object_id),
        )
        if target_object_location is not None:
            req.target_object_location.CopyFrom(sdk_to_proto(target_object_location))
        resp: PickUpObjectResponse = await stub.PickUpObject(req, timeout=timeout)
        return {"success": bool(resp.success), "message": str(resp.message)}

    @staticmethod
    @safe_async_rpc(default={"success": False, "message": ""})
    async def drop_object(
        conn: GrpcConnection,
        actor_id: bytes | str | dict,
        target_drop_location: Vector3,
        hand: RLDemoHandType = RLDemoHandType.HAND_RIGHT,
        enable_physics: bool = False,
        timeout: float = 5.0,
    ) -> dict:
        """
        Request the UE server to drop an object (placeholder Reactor endpoint).
        """
        stub = conn.get_stub(DemoRLServiceStub)
        req = DropObjectRequest(
            actor_id=_to_object_id(actor_id),
            hand=int(hand),
            target_drop_location=sdk_to_proto(target_drop_location),
            enable_physics=bool(enable_physics),
        )
        resp: DropObjectResponse = await stub.DropObject(req, timeout=timeout)
        return {"success": bool(resp.success), "message": str(resp.message)}

    # =========================
    # ArenaService (multi-level)
    # =========================

    @staticmethod
    @safe_async_rpc(default="")
    async def load_arena(
        conn: GrpcConnection,
        level_asset_path: str,
        anchor: Transform,
        make_visible: bool = True,
    ) -> str:
        """
        Dynamically load an arena level and return its GUID identifier.

        Returns:
            str: Arena GUID string.
        """
        stub = conn.get_stub(ArenaServiceStub)
        req = LoadArenaRequest(
            level_asset_path=level_asset_path,
            anchor=sdk_to_proto(anchor),
            make_visible=make_visible,
        )
        resp: LoadArenaResponse = await stub.LoadArena(req, timeout=10.0)
        # arena_id.id.guid: bytes(16, UE FGuid LE)
        return _fguid_bytes_to_str(resp.arena_id.guid)

    @staticmethod
    @safe_async_rpc(default=False)
    async def destroy_arena(conn: GrpcConnection, arena_id: str) -> bool:
        """
        Destroy a loaded arena instance.

        Returns:
            bool: True on success.
        """
        stub = conn.get_stub(ArenaServiceStub)
        await stub.DestroyArena(
            DestroyArenaRequest(arena_id=_to_object_id(arena_id)), timeout=5.0
        )
        return True

    @staticmethod
    @safe_async_rpc(default=False)
    async def reset_arena(conn: GrpcConnection, arena_id: str) -> bool:
        """
        Reset the specified arena to its initial state.

        Returns:
            bool: True on success.
        """
        stub = conn.get_stub(ArenaServiceStub)
        await stub.ResetArena(
            ResetArenaRequest(arena_id=_to_object_id(arena_id)), timeout=30.0
        )
        return True

    @staticmethod
    @safe_async_rpc(default=False)
    async def set_arena_visible(
        conn: GrpcConnection, arena_id: str, visible: bool
    ) -> bool:
        """
        Toggle arena visibility for rendering and logic.

        Returns:
            bool: True on success.
        """
        stub = conn.get_stub(ArenaServiceStub)
        await stub.SetArenaVisible(
            SetArenaVisibleRequest(arena_id=_to_object_id(arena_id), visible=visible),
            timeout=2.0,
        )
        return True

    @staticmethod
    @safe_async_rpc(default=[])
    async def list_arenas(conn: GrpcConnection) -> list[dict]:
        """
        List all arena instances with resource path, anchor, visibility and actor count.

        Returns:
            list[dict]: Entries include ``id``, ``asset_path``, ``anchor``, ``is_loaded``, ``is_visible`` and ``num_actors``.
        """
        stub = conn.get_stub(ArenaServiceStub)
        resp: ListArenasResponse = await stub.ListArenas(
            ListArenasRequest(), timeout=2.0
        )
        out: list[dict] = []
        for a in resp.arenas:
            out.append(
                {
                    "id": _fguid_bytes_to_str(a.arena_id.guid),
                    "asset_path": a.asset_path,
                    "anchor": proto_to_sdk(a.anchor),
                    "is_loaded": bool(a.is_loaded),
                    "is_visible": bool(a.is_visible),
                    "num_actors": int(a.num_actors),
                }
            )
        return out

    @staticmethod
    @safe_async_rpc(default=None)
    async def spawn_actor_in_arena(
        conn: GrpcConnection,
        arena_id: str,
        class_path: str,
        local_transform: Transform,
        timeout: float = 5.0,
    ) -> dict | None:
        """
        Spawn an actor inside an arena's local coordinate system and return its identity.

        Returns:
            dict | None: Dictionary with ``id``, ``name`` and ``class_path``.
        """
        stub = conn.get_stub(ArenaServiceStub)
        req = SpawnActorInArenaRequest(
            arena_id=_to_object_id(arena_id),
            class_path=class_path,
            local_transform=sdk_to_proto(local_transform),
        )
        resp: SpawnActorInArenaResponse = await stub.SpawnActorInArena(
            req, timeout=timeout
        )
        ai = resp.actor
        return {
            "id": _fguid_bytes_to_str(ai.id.guid),
            "name": ai.name,
            "class_path": ai.class_path,
        }

    @staticmethod
    @safe_async_rpc(default=False)
    async def set_actor_pose_local(
        conn: GrpcConnection,
        arena_id: str,
        actor_id: str,
        local_transform: Transform,
        reset_physics: bool = True,
    ) -> bool:
        """
        Place an actor at an arena-local transform (converted to world space and teleported).

        Returns:
            bool: True on success.
        """
        stub = conn.get_stub(ArenaServiceStub)
        await stub.SetActorPoseLocal(
            SetActorPoseLocalRequest(
                arena_id=_to_object_id(arena_id),
                actor_id=_to_object_id(actor_id),
                local_transform=sdk_to_proto(local_transform),
                reset_physics=reset_physics,
            ),
            timeout=2.0,
        )
        return True

    @staticmethod
    @safe_async_rpc(default=None)
    async def get_actor_pose_local(
        conn: GrpcConnection, arena_id: str, actor_id: str
    ) -> Transform | None:
        """
        Retrieve an actor's transform expressed in arena-local coordinates.

        Returns:
            Transform | None: Arena-local transform, or ``None`` on failure.
        """
        stub = conn.get_stub(ArenaServiceStub)
        resp: GetActorPoseLocalResponse = await stub.GetActorPoseLocal(
            GetActorPoseLocalRequest(
                arena_id=_to_object_id(arena_id),
                actor_id=_to_object_id(actor_id),
            ),
            timeout=2.0,
        )
        return proto_to_sdk(resp.local_transform)

    @staticmethod
    @safe_async_rpc(default=None)
    async def local_to_world(
        conn: GrpcConnection, arena_id: str, local_transform: Transform
    ) -> Transform | None:
        """
        Convert an arena-local transform to a world transform.

        Returns:
            Transform | None: World transform, or ``None`` on failure.
        """
        stub = conn.get_stub(ArenaServiceStub)
        resp: LocalToWorldResponse = await stub.LocalToWorld(
            LocalToWorldRequest(
                arena_id=_to_object_id(arena_id),
                local=sdk_to_proto(local_transform),
            ),
            timeout=2.0,
        )
        return proto_to_sdk(resp.world)

    @staticmethod
    @safe_async_rpc(default=None)
    async def world_to_local(
        conn: GrpcConnection, arena_id: str, world_transform: Transform
    ) -> Transform | None:
        """
        Convert a world transform to arena-local space.

        Returns:
            Transform | None: Arena-local transform, or ``None`` on failure.
        """
        stub = conn.get_stub(ArenaServiceStub)
        resp: WorldToLocalResponse = await stub.WorldToLocal(
            WorldToLocalRequest(
                arena_id=_to_object_id(arena_id),
                world=sdk_to_proto(world_transform),
            ),
            timeout=2.0,
        )
        return proto_to_sdk(resp.local)

    @staticmethod
    @safe_async_rpc(default=False)
    async def destroy_actor(conn: GrpcConnection, actor_id: bytes | str | dict) -> bool:
        """
        Destroy an actor in the Demo RL scene.

        Returns:
            bool: True on success.
        """
        stub = conn.get_stub(DemoRLServiceStub)
        req = DestroyActorRequest(actor_id=_to_object_id(actor_id))
        await stub.DestroyActor(req, timeout=2.0)
        return True

    # Arena Load/Reset/Destroy now complete asynchronously on the server,
    # but remain awaitable for SDK clients (signatures and IDs stay unchanged).

    @staticmethod
    @safe_async_rpc(default=False)
    async def arena_destroy_actor(
        conn: GrpcConnection, arena_id: str, actor_id: str
    ) -> bool:
        """
        Remove an actor that was spawned inside the specified arena.

        Returns:
            bool: True on success.
        """
        stub = conn.get_stub(ArenaServiceStub)
        req = DestroyActorInArenaRequest(
            arena_id=_to_object_id(arena_id), actor_id=_to_object_id(actor_id)
        )
        await stub.DestroyActorInArena(req, timeout=2.0)
        return True

    @staticmethod
    @safe_async_rpc(default=(None, None))
    async def arena_simple_move_towards(
        conn: GrpcConnection,
        arena_id: str,
        target_local_location: Vector3,
        orientation_mode: int = 0,  # 0 KEEP_CURRENT, 1 FACE_MOVEMENT, 2 GIVEN
        given_forward: Vector3 | None = None,
        timeout: float = 3600.0,
    ) -> tuple[dict | None, dict | None]:
        """
        Move an arena-local actor toward a local target location.

        Args:
            arena_id (str): Arena identifier.
            target_local_location (Vector3): Destination expressed in arena-local coordinates.
            orientation_mode (int): Orientation mode (0 keep current, 1 face movement, 2 given).
            given_forward (Vector3 | None): Forward vector used when ``orientation_mode`` is 2.
            timeout (float): RPC timeout in seconds.

        Returns:
            tuple[Vector3 | None, dict | None]: Current location and optional hit metadata.
        """
        stub = conn.get_stub(ArenaServiceStub)
        req = SimpleMoveTowardsInArenaRequest(
            arena_id=_to_object_id(arena_id),
            target_local_location=sdk_to_proto(target_local_location),
            orientation_mode=orientation_mode,
        )
        if orientation_mode == 2 and given_forward is not None:
            req.given_forward.CopyFrom(sdk_to_proto(given_forward))

        resp: SimpleMoveTowardsInArenaResponse = await stub.SimpleMoveTowardsInArena(
            req, timeout=timeout
        )
        current_location = proto_to_sdk(resp.current_location)
        hit_result = (
            {"hit_actor": resp.hit_result.hit_actor}
            if resp.HasField("hit_result")
            else None
        )
        return current_location, hit_result

    @staticmethod
    @safe_async_rpc(default=[])
    async def single_line_trace_by_object(
        conn: GrpcConnection,
        jobs: list[dict],
        timeout: float = 5.0,
    ) -> list[dict]:
        """
        Run batch SingleLineTraceByObject requests and return hit summaries.

        Args:
            jobs (list[dict]): Each job describes ``start``/``end`` vectors, collision object types,
                optional ``trace_complex`` flag and ``actors_to_ignore`` collection.
            timeout (float): RPC timeout in seconds.

        Returns:
            list[dict]: Per-job results including ``job_index``, ``blocking_hit``, ``distance``, ``impact_point``
                and optional ``actor_state``.
        """
        req = BatchSingleLineTraceByObjectRequest()
        for j in jobs:
            job = req.jobs.add()
            job.start.CopyFrom(sdk_to_proto(j["start"]))
            job.end.CopyFrom(sdk_to_proto(j["end"]))
            for ot in j.get("object_types", []):
                job.object_types.append(int(ot))
            if "trace_complex" in j and j["trace_complex"] is not None:
                job.trace_complex = bool(j["trace_complex"])
            for ig in j.get("actors_to_ignore", []) or []:
                job.actors_to_ignore.add().CopyFrom(_to_object_id(ig))

        stub = conn.get_stub(DemoRLServiceStub)
        resp = await stub.BatchSingleLineTraceByObject(req, timeout=timeout)

        out: list[dict] = []
        for r in resp.results:
            item = {
                "job_index": int(r.job_index),
                "blocking_hit": bool(r.blocking_hit),
                "distance": float(r.distance),
                "impact_point": proto_to_sdk(r.impact_point),
            }
            if r.HasField("actor_state"):
                item["actor_state"] = _actor_state_to_dict(r.actor_state)
            out.append(item)
        return out

    @staticmethod
    @safe_async_rpc(default=[])
    async def multi_line_trace_by_object(
        conn: GrpcConnection,
        jobs: list[dict],
        timeout: float = 5.0,
        *,
        enable_debug_draw: bool = False,
    ) -> list[dict]:
        """
        Run batch MultiLineTraceByObject requests and collect ordered hit lists.

        Args:
            jobs (list[dict]): Each job describes ``start``/``end`` vectors, collision object types,
                optional ``trace_complex`` flag and ``actors_to_ignore`` collection.
            timeout (float): RPC timeout in seconds.
            enable_debug_draw (bool): Whether to render debug lines in UE.

        Returns:
            list[dict]: Per-job results with ``job_index`` and ``hits`` entries containing ``distance``,
                ``impact_point``, ``impact_normal`` and optional ``actor_state``.
        """
        req = BatchMultiLineTraceByObjectRequest()
        req.enable_debug_draw = bool(enable_debug_draw)
        for j in jobs:
            job = req.jobs.add()
            job.start.CopyFrom(sdk_to_proto(j["start"]))
            job.end.CopyFrom(sdk_to_proto(j["end"]))
            for ot in j.get("object_types", []):
                job.object_types.append(int(ot))
            if "trace_complex" in j and j["trace_complex"] is not None:
                job.trace_complex = bool(j["trace_complex"])
            for ig in j.get("actors_to_ignore", []) or []:
                job.actors_to_ignore.add().CopyFrom(_to_object_id(ig))

        stub = conn.get_stub(DemoRLServiceStub)
        resp = await stub.BatchMultiLineTraceByObject(req, timeout=timeout)

        out: list[dict] = []
        for r in resp.results:
            item = {"job_index": int(r.job_index), "hits": []}
            for h in r.hits:
                hit = {
                    "distance": float(h.distance),
                    "impact_point": proto_to_sdk(h.impact_point),
                    "impact_normal": proto_to_sdk(h.impact_normal),
                }
                if hasattr(h, "actor_state") and h.HasField("actor_state"):
                    hit["actor_state"] = _actor_state_to_dict(h.actor_state)
                item["hits"].append(hit)
            out.append(item)
        return out
