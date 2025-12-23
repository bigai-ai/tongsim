# :material-cube-scan: 体素感知管线

TongSIM Lite 提供体素占用查询接口，用于围绕某个 transform 获取周围几何的 **3D 占用信息**。常见用途包括：

- 结合碰撞的局部规划
- RL 策略的 3D occupancy 特征
- 调试“智能体感知到的占用空间”

体素查询通过 `VoxelService/QueryVoxel` 暴露给 Python。

---

## :material-form-textbox: 输入与约束

Python SDK 的封装接口为：

- `tongsim.connection.grpc.unary_api.UnaryAPI.query_voxel(...)`

输入参数：

- `transform`：体素盒中心的 **world-space** transform
- `voxel_num_x/y/z`：体素分辨率（UE 侧要求 **必须为偶数**）
- `box_extent`：半尺寸（world units，cm）
- `actors_to_ignore`：可选，需要忽略的 actor id 列表

!!! warning ":material-alert: 分辨率要求"
    - UE 要求 `voxel_num_x`、`voxel_num_y`、`voxel_num_z` 必须为 **偶数**。
    - 为便于解码且减少 padding，建议 `voxel_num_z` 取 **8 的倍数**。

实现参考：

- `unreal/Plugins/TongSimGrpc/Source/TongSimProto/Private/DemoRL/DemoRLSubsystem.cpp`（`UDemoRLSubsystem::QueryVoxel`）

---

## :material-database-outline: 输出格式（按 bit 压缩的 bytes）

服务端返回一个字段：

- `Voxel.voxel_buffer: bytes`

打包规则（TongSIM Lite 当前实现）：

- Z 轴按 bit 打包，且 **LSB-first**（bit0 → z=0，bit7 → z=7）
- Z 会补齐到 8 的倍数：`aligned_z = ceil(z/8)*8`
- buffer 字节长度为 `x * y * (aligned_z / 8)`

实现参考：

- `unreal/Plugins/TongSimCore/Source/TongSimVoxelGrid/Public/TSVoxelGridFuncLib.h`
- `unreal/Plugins/TongSimCore/Source/TongSimVoxelGrid/Private/TSVoxelGridFuncLib.cpp`

---

## :material-language-python: Python 端解码（兼容 Z padding）

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

!!! tip ":material-script-text-outline: 参考脚本"
    可参考 `examples/voxel.py`（查询 + 解码 + 渲染的完整流程）。

---

## :material-speedometer: 性能建议

- 分辨率按需设置（UE 侧体素化计算开销较大）。
- 训练中可降低采样频率（例如 1–5 Hz），除非确实需要每帧体素。
- 用 `actors_to_ignore` 排除自身体或大体积无关物体，减少开销。

---

## :material-bug: 常见问题

??? tip "解码时报 buffer 长度不匹配"
    - 确认考虑了 **Z padding**（`aligned_z = ceil(z/8)*8`）。
    - 建议直接让 `voxel_num_z` 为 8 的倍数，避免 padding。

??? tip "体素全空 / 全满"
    - 检查 `box_extent` 是否与场景尺度匹配（UE 使用厘米）。
    - 确认查询盒体与可碰撞几何体确实发生重叠。

---

**下一步：** [TongSim Capture](capture.md)
