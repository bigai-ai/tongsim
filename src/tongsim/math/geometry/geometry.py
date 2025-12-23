import math

from pyglm import glm as _glm

from .type import Quaternion, Vector3

__all__ = [
    "calc_camera_look_at_rotation",
    "cross",
    "degrees_to_radians",
    "dot",
    "euler_to_quaternion",
    "length",
    "lerp",
    "normalize",
    "quaternion_to_euler",
    "radians_to_degrees",
]


# Functions re-exported from glm:
dot = _glm.dot
cross = _glm.cross
normalize = _glm.normalize
length = _glm.length
lerp = _glm.lerp


# Custom helpers:


def degrees_to_radians(value: float | Vector3) -> float | Vector3:
    """
    Convert degrees to radians.

    Args:
        value (float | Vector3): A scalar degree value or a degree-based `Vector3`.

    Returns:
        float | Vector3: The value converted to radians.
    """
    if isinstance(value, Vector3):
        return Vector3(
            math.radians(value.x),
            math.radians(value.y),
            math.radians(value.z),
        )
    return math.radians(value)


def radians_to_degrees(value: float | Vector3) -> float | Vector3:
    """
    Convert radians to degrees.

    Args:
        value (float | Vector3): A scalar radian value or a radian-based `Vector3`.

    Returns:
        float | Vector3: The value converted to degrees.
    """
    if isinstance(value, Vector3):
        return Vector3(
            math.degrees(value.x),
            math.degrees(value.y),
            math.degrees(value.z),
        )
    return math.degrees(value)


def euler_to_quaternion(euler: Vector3, is_degree: bool = False) -> Quaternion:
    """
    Convert Euler angles (roll, pitch, yaw) to a quaternion.

    Uses Unreal Engine's ZYX rotation order:
    - roll: rotate around X axis
    - pitch: rotate around Y axis
    - yaw: rotate around Z axis

    Args:
        euler (Vector3): Euler angles in (roll, pitch, yaw).
        is_degree (bool): Whether the input is in degrees. Defaults to False (radians).

    Returns:
        Quaternion: The corresponding rotation quaternion.
    """
    if is_degree:
        euler = degrees_to_radians(euler)

    roll, pitch, yaw = euler.x, euler.y, euler.z

    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy

    return Quaternion(w, x, y, z)


def quaternion_to_euler(q: Quaternion, is_degree: bool = False) -> Vector3:
    """
    Convert a quaternion to Euler angles (roll, pitch, yaw).

    Uses Unreal Engine's coordinate convention and ZYX rotation order:
    - Roll (X): rotate around X axis
    - Pitch (Y): rotate around Y axis
    - Yaw (Z): rotate around Z axis

    Args:
        q (Quaternion): Input quaternion.
        is_degree (bool): Whether to return degrees. Defaults to False (radians).

    Returns:
        Vector3: Euler angles in (roll, pitch, yaw).
    """
    w, x, y, z = q.w, q.x, q.y, q.z

    # pitch (Y axis)
    sinp = 2.0 * (w * y - z * x)
    pitch = math.copysign(math.pi / 2, sinp) if abs(sinp) >= 1 else math.asin(sinp)

    # yaw (Z axis)
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    # roll (X axis)
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    result = Vector3(roll, pitch, yaw)
    return radians_to_degrees(result) if is_degree else result


def calc_camera_look_at_rotation(pos: Vector3, target: Vector3) -> Quaternion:
    """
    Compute the camera rotation quaternion required to look from `pos` to `target`.

    Assumes the camera's local forward is +X and the world up is +Z.

    Args:
        pos (Vector3): Camera position.
        target (Vector3): Target position.

    Returns:
        Quaternion: The rotation that makes the camera look at the target.
    """
    world_up = Vector3(0.0, 0.0, 1.0)

    forward = normalize(target - pos)  # Camera forward (+X)
    right = cross(world_up, forward)

    # Handle degenerate cases where forward is parallel (or anti-parallel) to world_up.
    if length(right) < 1e-6:
        right = normalize(Vector3(0.0, 1.0, 0.0))  # Pick any orthogonal direction.
    else:
        right = normalize(right)

    up = cross(forward, right)

    # Build rotation matrix (column-major, right-handed).
    m00, m01, m02 = forward.x, right.x, up.x
    m10, m11, m12 = forward.y, right.y, up.y
    m20, m21, m22 = forward.z, right.z, up.z

    trace = m00 + m11 + m22

    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        w = 0.25 * s
        x = (m21 - m12) / s
        y = (m02 - m20) / s
        z = (m10 - m01) / s
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2.0
        w = (m21 - m12) / s
        x = 0.25 * s
        y = (m01 + m10) / s
        z = (m02 + m20) / s
    elif m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2.0
        w = (m02 - m20) / s
        x = (m01 + m10) / s
        y = 0.25 * s
        z = (m12 + m21) / s
    else:
        s = math.sqrt(1.0 + m22 - m00 - m11) * 2.0
        w = (m10 - m01) / s
        x = (m02 + m20) / s
        y = (m12 + m21) / s
        z = 0.25 * s

    return Quaternion(w, x, y, z)
