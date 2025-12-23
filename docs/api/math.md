# :material-axis-arrow: Math Types

The SDK ships a small math layer used across the runtime and gRPC APIs:

- `Vector3` / `Quaternion`: lightweight 3D vector and rotation types (provided by `pyglm`)
- `Transform` / `Pose` / `AABB`: convenience wrappers for common spatial data
- Helpers for conversion and geometry operations

!!! note ":material-information-outline: Units"
    TongSIM Lite follows Unreal Engine conventions: positions are in **centimeters** (UU).

---

## :material-shape-outline: Key Types

| Type | What it represents | Typical usage |
|---|---|---|
| `Vector3` | 3D vector | positions, extents, directions |
| `Quaternion` | rotation | orientation for cameras/actors |
| `Transform` | location + rotation + scale | gRPC transforms, coordinate conversion |
| `Pose` | location + rotation | simple pose passing |
| `AABB` | axis-aligned bounding box | bounding/overlap checks in Python |

---

## :material-function: Helper functions

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
