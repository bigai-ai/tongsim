# :material-axis-arrow: 数学类型（Math Types）

SDK 内置了一套轻量的数学层，用于运行时与 gRPC API 的数据表达：

- `Vector3` / `Quaternion`：3D 向量与旋转（由 `pyglm` 提供）
- `Transform` / `Pose` / `AABB`：常用空间数据的便捷封装
- 一组常用的几何与转换工具函数

!!! note ":material-information-outline: 单位"
    TongSIM Lite 采用 Unreal Engine 约定：位置单位为 **厘米**（UU）。

---

## :material-shape-outline: 关键类型

| 类型 | 含义 | 常见用途 |
|---|---|---|
| `Vector3` | 三维向量 | 位置、范围、方向 |
| `Quaternion` | 旋转 | 相机/角色朝向 |
| `Transform` | 位置 + 旋转 + 缩放 | gRPC Transform、坐标变换 |
| `Pose` | 位置 + 旋转 | 简化 pose 传递 |
| `AABB` | 轴对齐包围盒 | Python 侧的包围/包含判断 |

---

## :material-function: 常用工具函数

- `dot`, `cross`, `normalize`, `length`, `lerp`
- `degrees_to_radians`, `radians_to_degrees`
- `euler_to_quaternion`, `quaternion_to_euler`
- `calc_camera_look_at_rotation`

---

## API References

::: tongsim.math.geometry.type.Pose

::: tongsim.math.geometry.type.Transform

::: tongsim.math.geometry.type.AABB

::: tongsim.math.geometry.geometry.degrees_to_radians

::: tongsim.math.geometry.geometry.radians_to_degrees

::: tongsim.math.geometry.geometry.euler_to_quaternion

::: tongsim.math.geometry.geometry.quaternion_to_euler

::: tongsim.math.geometry.geometry.calc_camera_look_at_rotation

::: tongsim.math.geometry.geometry.dot

::: tongsim.math.geometry.geometry.cross

::: tongsim.math.geometry.geometry.normalize

::: tongsim.math.geometry.geometry.length

::: tongsim.math.geometry.geometry.lerp
