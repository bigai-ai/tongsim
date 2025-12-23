# :material-camera: Capture

**Capture API** 提供基于 Snapshot 的 RGB/Depth 采集能力。

- 协议：`protobuf/tongsim_lite_protobuf/capture.proto`
- SDK 封装：`tongsim.connection.grpc.capture_api.CaptureAPI`

!!! tip ":material-book-open-variant: 使用指南"
    可参考 [TongSim Capture](../guides/capture.md) 获取端到端示例与解码说明。

---

## Key Functions

- `list_cameras`：列出当前会话中创建的采集相机。
- `create_camera`：生成采集相机 actor，并应用参数。
- `set_camera_pose` / `attach_camera`：移动相机或挂到父 actor。
- `update_camera_params`：更新参数（相机捕获中会失败）。
- `capture_snapshot`：采集单帧（color/depth 可选）。
- `get_status`：查询采集状态。
- `destroy_camera`：销毁相机并清理资源。

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
