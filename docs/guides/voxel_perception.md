# :material-cube-scan: Voxel Perception Pipeline

TongSIM Lite provides a voxel occupancy query API for **3D geometry perception** around a given transform. This is useful for:

- local collision-aware planning
- 3D occupancy features for RL policies
- debugging “what the agent thinks is occupied”

The voxel query is exposed via `VoxelService/QueryVoxel`.

---

## :material-form-textbox: Inputs & constraints

The Python SDK wrapper is:

- `tongsim.connection.grpc.unary_api.UnaryAPI.query_voxel(...)`

Inputs:

- `transform`: the **world-space** center transform of the voxel box
- `voxel_num_x/y/z`: voxel resolution (**must be even**, UE validates this)
- `box_extent`: half-extent in world units (cm)
- `actors_to_ignore`: optional actor ids excluded from sampling

!!! warning ":material-alert: Resolution requirements"
    - UE requires `voxel_num_x`, `voxel_num_y`, `voxel_num_z` to be **even**.
    - For easier decoding and better packing efficiency, prefer `voxel_num_z` to be a **multiple of 8**.

Implementation reference:

- `unreal/Plugins/TongSimGrpc/Source/TongSimProto/Private/DemoRL/DemoRLSubsystem.cpp` (`UDemoRLSubsystem::QueryVoxel`)

---

## :material-database-outline: Output format (bit-packed bytes)

The service returns one field:

- `Voxel.voxel_buffer: bytes`

Packing rules (TongSIM Lite implementation):

- Z is bit-packed **LSB-first** (bit 0 → z=0, bit 7 → z=7)
- Z is padded to the next multiple of 8: `aligned_z = ceil(z/8)*8`
- Buffer length is `x * y * (aligned_z / 8)` bytes

Implementation reference:

- `unreal/Plugins/TongSimCore/Source/TongSimVoxelGrid/Public/TSVoxelGridFuncLib.h`
- `unreal/Plugins/TongSimCore/Source/TongSimVoxelGrid/Private/TSVoxelGridFuncLib.cpp`

---

## :material-language-python: Decode in Python (robust to Z padding)

```python
import numpy as np

def decode_voxel(buffer: bytes, x: int, y: int, z: int) -> np.ndarray:
    aligned_z = ((z + 7) // 8) * 8
    expected_bytes = x * y * (aligned_z // 8)
    arr = np.frombuffer(buffer, dtype=np.uint8, count=expected_bytes)
    bits = np.unpackbits(arr, bitorder="little")
    grid = bits.reshape((x, y, aligned_z), order="C")
    return grid[:, :, :z].astype(bool, copy=False)
```

!!! tip ":material-script-text-outline: Reference implementation"
    See `examples/voxel.py` for an end-to-end demo (query + decode + render).

---

## :material-speedometer: Performance tips

- Use a resolution that matches your model needs (voxel queries are CPU-heavy on the UE side).
- Sample at a lower frequency for training (for example 1–5 Hz) unless you truly need per-frame voxels.
- Use `actors_to_ignore` to remove self-actors or large irrelevant objects from sampling.

---

## :material-bug: Troubleshooting

??? tip "Buffer length mismatch while decoding"
    - Ensure you account for **Z padding** (`aligned_z = ceil(z/8)*8`).
    - Prefer `voxel_num_z` as a multiple of 8 to avoid padding.

??? tip "Voxel grid looks empty / all occupied"
    - Verify `box_extent` matches your scene scale (UE uses centimeters).
    - Ensure the query box actually overlaps collidable geometry.

---

**Next:** [TongSim Capture](capture.md)
