# :material-camera: TongSim Capture（RGB / Depth）

**TongSim Capture** 是 TongSIM Lite 的传感器模块，用于从 Unreal Engine 采集 **彩色图像** 与 **深度图**。它适用于：

- 视觉/感知评测（RGB-D）
- 以图像为输入的模仿学习 / 强化学习
- 调试智能体观测

Capture 能力通过 gRPC 的 `CaptureService` 暴露给 Python。

---

## :material-puzzle-outline: Capture 的实现结构

TongSIM Lite 的 Capture 由两部分组成：

| 模块 | 位置 | 职责 |
|---|---|---|
| UE 侧采集运行时 | `unreal/Plugins/TongSimCore/Source/TongSimCapture` | SceneCapture + GPU 回读 + 深度计算 |
| gRPC 接入层 | `unreal/Plugins/TongSimGrpc/Source/TongSimProto/Private/Capture/CaptureGrpcSubsystem.cpp` | 相机创建/挂载 + Snapshot 请求 |

UE 侧每个采集相机对应一个 `ATSCaptureCameraActor`，包含 `CaptureId` 与参数结构体。

---

## :material-api: gRPC 接口（Python 能做什么）

协议定义：

- `protobuf/tongsim_lite_protobuf/capture.proto`

Python 封装：

- `src/tongsim/connection/grpc/capture_api.py`（`CaptureAPI`）

支持的操作：

| 操作 | gRPC | 说明 |
|---|---|---|
| 列出相机 | `CaptureService/ListCaptureCameras` | 返回相机信息 + 最近一次状态 |
| 创建相机 | `CaptureService/CreateCaptureCamera` | 生成相机 actor，可选挂到父 actor |
| 更新参数 | `CaptureService/UpdateCaptureCameraParams` | 若相机正在捕获会失败 |
| 设置位姿 | `CaptureService/SetCaptureCameraPose` | 移动相机 actor |
| 挂载 | `CaptureService/AttachCaptureCamera` | 挂到父 actor，可指定 socket |
| Snapshot | `CaptureService/CaptureSnapshot` | 返回单帧（可选 color/depth） |
| 销毁 | `CaptureService/DestroyCaptureCamera` | 删除相机，可强制停止捕获 |

!!! note ":material-information-outline: Snapshot 为主的接口"
    当前 gRPC 侧以 **snapshot** 为主要使用方式。UE 运行时内部支持连续采集，如有需要可继续扩展为流式接口。

---

## :material-rocket-launch: 最小 Python 示例

```python
from tongsim import TongSim
from tongsim.connection.grpc.capture_api import CaptureAPI
from tongsim.math import Transform, Vector3
from tongsim_lite_protobuf import capture_pb2

CAPTURE_PARAMS = {
    "width": 640,
    "height": 480,
    "fov_degrees": 90.0,
    "qps": 10.0,
    "enable_depth": True,
    "depth_near": 10.0,
    "depth_far": 5000.0,
    "depth_mode": capture_pb2.CaptureDepthMode.CAPTURE_DEPTH_LINEAR,
    "color_source": capture_pb2.CaptureColorSource.COLOR_SOURCE_FINAL_COLOR_LDR,
    "color_format": capture_pb2.CaptureRenderTargetFormat.COLOR_FORMAT_RGBA8,
}

with TongSim("127.0.0.1:5726") as ts:
    cam_id = ts.context.sync_run(
        CaptureAPI.create_camera(
            ts.context.conn,
            transform=Transform(location=Vector3(200, 700, 200)),
            params=CAPTURE_PARAMS,
            capture_name="DemoCam",
        )
    )

    frame = ts.context.sync_run(
        CaptureAPI.capture_snapshot(
            ts.context.conn,
            cam_id,
            include_color=True,
            include_depth=True,
            timeout_seconds=1.0,
        )
    )

    ts.context.sync_run(CaptureAPI.destroy_camera(ts.context.conn, cam_id))
    print(frame.keys())
```

!!! tip ":material-script-text-outline: 完整示例"
    运行 `examples/capture_demo.py` 会将 color/depth 保存到 `logs/capture_demo_*` 目录下，便于检查。

---

## :material-tune: 相机参数（实践含义）

`CaptureCameraParams` 与 Unreal 的采集设置基本一一对应：

- `width`, `height`：输出分辨率
- `fov_degrees`：水平 FOV（度）
- `enable_depth`：是否输出深度
- `depth_near`, `depth_far`, `depth_mode`：深度范围与编码模式
- `color_source`, `color_format`：采集源与渲染目标格式
- `enable_post_process`, `enable_temporal_aa`：真实感 vs 可重复性

!!! tip ":material-balance: 可重复性与真实感取舍"
    训练场景通常建议关闭 TAA 与较重后处理以提高确定性；演示场景可提升画质。

---

## :material-file-eye-outline: 输出解码（color 与 depth）

### :material-palette: 颜色缓冲（`rgba8`）

虽然 proto 字段名叫 `rgba8`，但 UE 侧实现输出的是 **BGRA8 顺序**（Unreal 常见像素布局）。

使用 NumPy 转换到 RGB：

```python
import numpy as np

bgra = np.frombuffer(frame["rgba8"], dtype=np.uint8).reshape(frame["height"], frame["width"], 4)
rgb = bgra[..., [2, 1, 0]]  # B,G,R -> R,G,B
```

### :material-image-filter-hdr: 深度缓冲（`depth_r32`）

`depth_r32` 为 float32 的打包数组（`width * height` 个值），小端：

```python
import numpy as np

depth = np.frombuffer(frame["depth_r32"], dtype="<f4").reshape(frame["height"], frame["width"])
print(depth.min(), depth.max())
```

---

## :material-bug: 常见问题

??? tip "Snapshot 失败 / 超时"
    - 调大 `timeout_seconds`（复杂场景下 GPU 回读会更慢）。
    - 降低分辨率或关闭 depth 输出以提速。
    - 确认 UE 没有卡住（PIE 暂停、断点、shader 编译等）。

??? tip "颜色通道不对（红蓝互换）"
    - 将 `rgba8` 按 **BGRA** 解码，并按上面的方式重排通道。

??? tip "深度全是 0 / 全是 inf"
    - 确认 `enable_depth=True`。
    - 检查 `depth_near` / `depth_far` 与 `depth_mode` 设置是否合理。

---

**下一步：** [数据流与同步](../architecture/data_flow.md)
