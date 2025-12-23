# :material-camera: Capture

The **Capture API** provides snapshot-based RGB/Depth capture from Unreal.

- Protocol: `protobuf/tongsim_lite_protobuf/capture.proto`
- SDK wrapper: `tongsim.connection.grpc.capture_api.CaptureAPI`

!!! tip ":material-book-open-variant: Usage guide"
    See [TongSim Capture](../guides/capture.md) for end-to-end examples and decoding notes.

---

## Key Functions

- `list_cameras`: List capture cameras created in the current session.
- `create_camera`: Spawn a capture camera actor and apply capture parameters.
- `set_camera_pose` / `attach_camera`: Move the camera or attach it to a parent actor.
- `update_camera_params`: Update parameters (fails if the camera is capturing).
- `capture_snapshot`: Capture a single frame (color/depth optional).
- `get_status`: Query capture status.
- `destroy_camera`: Cleanup a camera.

---

## API References

::: tongsim.connection.grpc.capture_api.CaptureAPI.list_cameras

::: tongsim.connection.grpc.capture_api.CaptureAPI.create_camera

::: tongsim.connection.grpc.capture_api.CaptureAPI.destroy_camera

::: tongsim.connection.grpc.capture_api.CaptureAPI.set_camera_pose

::: tongsim.connection.grpc.capture_api.CaptureAPI.update_camera_params

::: tongsim.connection.grpc.capture_api.CaptureAPI.attach_camera

::: tongsim.connection.grpc.capture_api.CaptureAPI.capture_snapshot

::: tongsim.connection.grpc.capture_api.CaptureAPI.get_status
