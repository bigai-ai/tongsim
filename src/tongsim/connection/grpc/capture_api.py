"""High level gRPC helpers for TongSim capture cameras."""

from __future__ import annotations

from typing import Any

from tongsim.math import Transform
from tongsim_lite_protobuf import capture_pb2, capture_pb2_grpc, common_pb2, object_pb2

from .core import GrpcConnection
from .utils import proto_to_sdk, safe_async_rpc, sdk_to_proto


def _transform_to_proto(transform: Transform) -> common_pb2.Transform:
    return sdk_to_proto(transform)


def _dict_to_params(params: dict[str, Any]) -> capture_pb2.CaptureCameraParams:
    msg = capture_pb2.CaptureCameraParams()
    msg.width = int(params.get("width", msg.width))
    msg.height = int(params.get("height", msg.height))
    msg.fov_degrees = float(params.get("fov_degrees", msg.fov_degrees))
    msg.qps = float(params.get("qps", msg.qps))
    msg.enable_depth = bool(params.get("enable_depth", msg.enable_depth))
    if "color_source" in params:
        msg.color_source = int(params["color_source"])
    if "color_format" in params:
        msg.color_format = int(params["color_format"])
    msg.enable_post_process = bool(
        params.get("enable_post_process", msg.enable_post_process)
    )
    msg.enable_temporal_aa = bool(
        params.get("enable_temporal_aa", msg.enable_temporal_aa)
    )
    msg.depth_near = float(params.get("depth_near", msg.depth_near))
    msg.depth_far = float(params.get("depth_far", msg.depth_far))
    if "depth_mode" in params:
        msg.depth_mode = int(params["depth_mode"])
    if "rgb_codec" in params:
        msg.rgb_codec = int(params["rgb_codec"])
    if "depth_codec" in params:
        msg.depth_codec = int(params["depth_codec"])
    msg.jpeg_quality = int(params.get("jpeg_quality", msg.jpeg_quality))
    return msg


def _frame_to_dict(frame: capture_pb2.CaptureFrame) -> dict[str, Any]:
    out: dict[str, Any] = {
        "camera_id": frame.camera_id.guid,
        "frame_id": frame.frame_id,
        "game_time": frame.game_time_seconds,
        "gpu_ready": frame.gpu_ready_timestamp,
        "width": frame.width,
        "height": frame.height,
        "world_pose": proto_to_sdk(frame.world_pose),
        "intrinsics": {
            "fx": frame.intrinsics.fx,
            "fy": frame.intrinsics.fy,
            "cx": frame.intrinsics.cx,
            "cy": frame.intrinsics.cy,
        },
        "has_color": frame.has_color,
        "has_depth": frame.has_depth,
        "depth_near": frame.depth_near,
        "depth_far": frame.depth_far,
        "depth_mode": frame.depth_mode,
    }
    if frame.has_color:
        out["rgba8"] = frame.rgba8
    if frame.has_depth:
        out["depth_r32"] = frame.depth_r32
    return out


class CaptureAPI:
    """Async helpers bridging gRPC capture service."""

    @staticmethod
    @safe_async_rpc()
    async def list_cameras(conn: GrpcConnection) -> list[dict[str, Any]]:
        stub = conn.get_stub(capture_pb2_grpc.CaptureServiceStub)
        resp = await stub.ListCaptureCameras(capture_pb2.ListCaptureCamerasRequest())
        out: list[dict[str, Any]] = []
        for desc in resp.cameras:
            item = {
                "camera": {
                    "id": desc.camera.id.guid,
                    "name": desc.camera.name,
                    "class_path": desc.camera.class_path,
                },
                "params": desc.params,
                "status": desc.status,
            }
            out.append(item)
        return out

    @staticmethod
    @safe_async_rpc(default=None)
    async def create_camera(
        conn: GrpcConnection,
        *,
        transform: Transform,
        params: dict[str, Any],
        capture_name: str | None = None,
        attach_parent: bytes | None = None,
        attach_socket: str = "",
        keep_world: bool = True,
    ) -> bytes | None:
        stub = conn.get_stub(capture_pb2_grpc.CaptureServiceStub)
        req = capture_pb2.CreateCaptureCameraRequest()
        if capture_name:
            req.capture_name = capture_name
        req.world_transform.CopyFrom(_transform_to_proto(transform))
        req.params.CopyFrom(_dict_to_params(params))
        if attach_parent:
            req.attach_parent.guid = attach_parent
        req.attach_socket = attach_socket
        req.keep_world = keep_world
        resp = await stub.CreateCaptureCamera(req)
        return resp.camera.id.guid

    @staticmethod
    @safe_async_rpc(default=False)
    async def destroy_camera(
        conn: GrpcConnection,
        camera_id: bytes,
        force_stop: bool = True,
    ) -> bool:
        stub = conn.get_stub(capture_pb2_grpc.CaptureServiceStub)
        req = capture_pb2.DestroyCaptureCameraRequest(
            camera_id=object_pb2.ObjectId(guid=camera_id)
        )
        req.force_stop_capture = force_stop
        await stub.DestroyCaptureCamera(req)
        return True

    @staticmethod
    @safe_async_rpc(default=False)
    async def set_camera_pose(
        conn: GrpcConnection, camera_id: bytes, transform: Transform
    ) -> bool:
        stub = conn.get_stub(capture_pb2_grpc.CaptureServiceStub)
        req = capture_pb2.SetCaptureCameraPoseRequest(
            camera_id=object_pb2.ObjectId(guid=camera_id),
            world_transform=_transform_to_proto(transform),
        )
        await stub.SetCaptureCameraPose(req)
        return True

    @staticmethod
    @safe_async_rpc(default=False)
    async def update_camera_params(
        conn: GrpcConnection, camera_id: bytes, params: dict[str, Any]
    ) -> bool:
        stub = conn.get_stub(capture_pb2_grpc.CaptureServiceStub)
        req = capture_pb2.UpdateCaptureCameraParamsRequest(
            camera_id=object_pb2.ObjectId(guid=camera_id),
            params=_dict_to_params(params),
        )
        await stub.UpdateCaptureCameraParams(req)
        return True

    @staticmethod
    @safe_async_rpc(default=False)
    async def attach_camera(
        conn: GrpcConnection,
        camera_id: bytes,
        parent_id: bytes,
        socket_name: str = "",
        keep_world: bool = True,
    ) -> bool:
        stub = conn.get_stub(capture_pb2_grpc.CaptureServiceStub)
        req = capture_pb2.AttachCaptureCameraRequest(
            camera_id=object_pb2.ObjectId(guid=camera_id),
            parent_actor_id=object_pb2.ObjectId(guid=parent_id),
            socket_name=socket_name,
            keep_world=keep_world,
        )
        await stub.AttachCaptureCamera(req)
        return True

    @staticmethod
    @safe_async_rpc(default=None)
    async def capture_snapshot(
        conn: GrpcConnection,
        camera_id: bytes,
        *,
        include_color: bool = True,
        include_depth: bool = True,
        timeout_seconds: float = 0.5,
    ) -> dict[str, Any] | None:
        stub = conn.get_stub(capture_pb2_grpc.CaptureServiceStub)
        req = capture_pb2.CaptureSnapshotRequest(
            camera_id=object_pb2.ObjectId(guid=camera_id),
            include_color=include_color,
            include_depth=include_depth,
            timeout_seconds=timeout_seconds,
        )
        resp = await stub.CaptureSnapshot(req)
        return _frame_to_dict(resp)

    @staticmethod
    @safe_async_rpc(default=None)
    async def get_status(
        conn: GrpcConnection, camera_id: bytes
    ) -> dict[str, Any] | None:
        stub = conn.get_stub(capture_pb2_grpc.CaptureServiceStub)
        req = capture_pb2.GetCaptureStatusRequest(
            camera_id=object_pb2.ObjectId(guid=camera_id)
        )
        resp = await stub.GetCaptureStatus(req)
        return {
            "capturing": resp.status.capturing,
            "queue_count": resp.status.queue_count,
            "compressed_queue_count": resp.status.compressed_queue_count,
            "width": resp.status.width,
            "height": resp.status.height,
            "fov_degrees": resp.status.fov_degrees,
            "depth_mode": resp.status.depth_mode,
        }
