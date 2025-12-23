# :material-camera: TongSim Capture (RGB / Depth)

**TongSim Capture** is TongSIM Lite’s sensor module for capturing **color** and **depth** images from Unreal Engine. It is designed for:

- perception benchmarks (RGB-D)
- imitation / RL policies that consume images
- debugging agent observations

The capture feature is exposed to Python via the gRPC `CaptureService`.

---

## :material-puzzle-outline: How capture is implemented

TongSIM Lite capture consists of two parts:

| Part | Location | Role |
|---|---|---|
| UE capture runtime | `unreal/Plugins/TongSimCore/Source/TongSimCapture` | SceneCapture + GPU readback + depth compute |
| gRPC bridge | `unreal/Plugins/TongSimGrpc/Source/TongSimProto/Private/Capture/CaptureGrpcSubsystem.cpp` | Create/attach cameras and request snapshots |

On the UE side, each capture camera is represented as an `ATSCaptureCameraActor` with a `CaptureId` and parameter struct.

---

## :material-api: gRPC surface (what Python can call)

Protocol definition:

- `protobuf/tongsim_lite_protobuf/capture.proto`

Python wrapper:

- `src/tongsim/connection/grpc/capture_api.py` (`CaptureAPI`)

Supported operations:

| Operation | gRPC | Notes |
|---|---|---|
| List cameras | `CaptureService/ListCaptureCameras` | Returns camera metadata + last known status |
| Create camera | `CaptureService/CreateCaptureCamera` | Spawns a camera actor; optional attach to a parent actor |
| Update params | `CaptureService/UpdateCaptureCameraParams` | Fails if the camera is currently capturing |
| Set pose | `CaptureService/SetCaptureCameraPose` | Moves the camera actor |
| Attach | `CaptureService/AttachCaptureCamera` | Attach to parent actor + optional socket |
| Snapshot | `CaptureService/CaptureSnapshot` | Returns one frame (color/depth optional) |
| Destroy | `CaptureService/DestroyCaptureCamera` | Removes camera; can force-stop capture |

!!! note ":material-information-outline: Snapshot-focused API"
    The current gRPC interface is designed around **snapshot capture**. The UE runtime supports continuous capture internally, and can be extended to expose streaming APIs if needed.

---

## :material-rocket-launch: Minimal Python example

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

!!! tip ":material-script-text-outline: End-to-end demo"
    Run `examples/capture_demo.py` to save color/depth outputs under `logs/capture_demo_*`.

---

## :material-tune: Camera parameters (practical meaning)

`CaptureCameraParams` maps closely to Unreal capture settings:

- `width`, `height`: output resolution
- `fov_degrees`: horizontal FOV in degrees
- `enable_depth`: enable depth output
- `depth_near`, `depth_far`, `depth_mode`: depth encoding and range
- `color_source`, `color_format`: scene capture source and render target format
- `enable_post_process`, `enable_temporal_aa`: realism vs determinism tradeoffs

!!! tip ":material-balance: Determinism vs realism"
    For training you may want to disable temporal AA and heavy post process. For demos you may prefer higher visual quality.

---

## :material-file-eye-outline: Output decoding (color & depth)

### :material-palette: Color buffer (`rgba8`)

The proto field is named `rgba8`, but the UE implementation writes bytes in **BGRA8 order** (Unreal’s common pixel layout).

Convert to RGB with NumPy:

```python
import numpy as np

bgra = np.frombuffer(frame["rgba8"], dtype=np.uint8).reshape(frame["height"], frame["width"], 4)
rgb = bgra[..., [2, 1, 0]]  # B,G,R -> R,G,B
```

### :material-image-filter-hdr: Depth buffer (`depth_r32`)

`depth_r32` is a packed float32 array (`width * height` values), little-endian:

```python
import numpy as np

depth = np.frombuffer(frame["depth_r32"], dtype="<f4").reshape(frame["height"], frame["width"])
print(depth.min(), depth.max())
```

---

## :material-bug: Troubleshooting

??? tip "Snapshot failed / timeout"
    - Increase `timeout_seconds` (GPU readback can take longer on heavy scenes).
    - Reduce resolution or disable depth for faster snapshots.
    - Ensure the UE process is not stalled (PIE paused, breakpoint, heavy shader compilation).

??? tip "Colors look swapped (blue/red)"
    - Treat `rgba8` as **BGRA** and reorder channels as shown above.

??? tip "Depth is all zeros / all inf"
    - Verify `enable_depth=True`.
    - Check `depth_near` / `depth_far` and `depth_mode` settings.

---

**Next:** [Data Flow](../architecture/data_flow.md)
