"""
tongsim.math.geometry.type
"""

# ruff: noqa: N812
from pyglm import glm as _glm
from pyglm.glm import mat4 as Mat4
from pyglm.glm import mat4_cast, translate
from pyglm.glm import quat as Quaternion
from pyglm.glm import scale as glm_scale
from pyglm.glm import vec3 as Vector3

__all__ = ["AABB", "Mat4", "Pose", "Quaternion", "Transform", "Vector3"]


class Pose:
    """
    A lightweight container that groups `location` and `rotation` as a pose.
    """

    __slots__ = ("location", "rotation")

    def __init__(
        self, location: Vector3 | None = None, rotation: Quaternion | None = None
    ):
        self.location = location if location is not None else Vector3(0.0, 0.0, 0.0)
        self.rotation = (
            rotation if rotation is not None else Quaternion(1.0, 0.0, 0.0, 0.0)
        )

    def __repr__(self) -> str:
        return f"Pose(location={self.location}, rotation={self.rotation})"

    def copy(self) -> "Pose":
        """
        Return a deep copy of this pose.
        """
        return Pose(Vector3(self.location), Quaternion(self.rotation))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Pose)
            and self.location == other.location
            and self.rotation == other.rotation
        )

    def to_transform(self) -> "Transform":
        """
        Convert this pose to a `Transform`.
        """
        return Transform(self.location, self.rotation, Vector3(1.0, 1.0, 1.0))


class Transform:
    """
    A spatial transform with `location`, `rotation`, and `scale`.

    This structure is aligned with Unreal Engine's Transform concept.
    """

    __slots__ = ("location", "rotation", "scale")

    def __init__(
        self,
        location: Vector3 | None = None,
        rotation: Quaternion | None = None,
        scale: Vector3 | None = None,
    ):
        self.location = location if location is not None else Vector3(0.0, 0.0, 0.0)
        self.rotation = (
            rotation if rotation is not None else Quaternion(1.0, 0.0, 0.0, 0.0)
        )
        self.scale = scale if scale is not None else Vector3(1.0, 1.0, 1.0)

    def __repr__(self) -> str:
        return (
            f"Transform(location={self.location}, "
            f"rotation={self.rotation}, scale={self.scale})"
        )

    def copy(self) -> "Transform":
        """
        Return a deep copy of this transform.
        """
        return Transform(
            Vector3(self.location),
            Quaternion(self.rotation),
            Vector3(self.scale),
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Transform)
            and self.location == other.location
            and self.rotation == other.rotation
            and self.scale == other.scale
        )

    def __mul__(self, other: "Transform") -> "Transform":
        """
        Compose two transforms (right-multiplication) and return a new transform.

        This is equivalent to applying `other` first, then `self`.

        Args:
            other (Transform): The other transform to compose with.

        Returns:
            Transform: The composed transform.
        """
        if not isinstance(other, Transform):
            return NotImplemented

        # Multiply transform matrices.
        m = self.to_matrix() * other.to_matrix()
        # print (m)

        # Extract translation from the matrix.
        loc = Vector3(m[3].x, m[3].y, m[3].z)

        # Extract scale.
        sx = _glm.length(Vector3(m[0].x, m[0].y, m[0].z))
        sy = _glm.length(Vector3(m[1].x, m[1].y, m[1].z))
        sz = _glm.length(Vector3(m[2].x, m[2].y, m[2].z))
        scale = Vector3(sx, sy, sz)

        # Extract rotation (remove scale first).
        rot_mat = Mat4(m)
        rot_mat[0] /= sx
        rot_mat[1] /= sy
        rot_mat[2] /= sz
        rot = _glm.quat_cast(rot_mat)

        return Transform(loc, rot, scale)

    def to_matrix(self) -> Mat4:
        """
        Return the 4x4 affine transformation matrix for this transform.

        The effective order is: scale → rotate → translate.
        """

        t = translate(Mat4(1.0), self.location)
        r = mat4_cast(self.rotation)
        s = glm_scale(Mat4(1.0), self.scale)
        return t * r * s  # Note the right-multiplication order.

    def transform_vector3(self, point: Vector3) -> Vector3:
        """
        Apply this transform to a 3D point and return the transformed result.
        """
        m = self.to_matrix()
        p = m * _glm.vec4(point, 1.0)  # Use homogeneous coordinates.
        return Vector3(p.x, p.y, p.z)

    def inverse(self) -> "Transform":
        """
        Return the inverse of this transform.

        Note: invert scale first, then rotation, then translation.
        """
        if self.scale.x == 0 or self.scale.y == 0 or self.scale.z == 0:
            raise ValueError(f"Cannot invert Transform with zero scale: {self.scale}")
        inv_scale = Vector3(
            1.0 / self.scale.x,
            1.0 / self.scale.y,
            1.0 / self.scale.z,
        )
        inv_rot = _glm.inverse(self.rotation)
        inv_loc = -(inv_rot * (inv_scale * self.location))
        return Transform(inv_loc, inv_rot, inv_scale)


class AABB:
    """
    Axis-Aligned Bounding Box (AABB) in 3D space.

    Attributes:
        min (Vector3): Minimum corner (smallest x, y, z).
        max (Vector3): Maximum corner (largest x, y, z).
    """

    __slots__ = ("max", "min")

    def __init__(self, min: Vector3, max: Vector3):
        self.min = min
        self.max = max

    def __repr__(self) -> str:
        return f"AABB(min={self.min}, max={self.max})"

    def deepcopy(self) -> "AABB":
        """
        Return a deep copy of this AABB.
        """
        return AABB(Vector3(self.min), Vector3(self.max))

    def center(self) -> Vector3:
        """
        Return the center point of the AABB.
        """
        return (self.min + self.max) * 0.5

    def extent(self) -> Vector3:
        """
        Return the size of the AABB (width, height, depth).
        """
        return self.max - self.min

    def contains_point(self, point: Vector3) -> bool:
        """
        Check whether a point lies inside the AABB.

        Args:
            point (Vector3): The point to test.

        Returns:
            bool: True if the point is inside; otherwise False.
        """
        return (
            self.min.x <= point.x <= self.max.x
            and self.min.y <= point.y <= self.max.y
            and self.min.z <= point.z <= self.max.z
        )
