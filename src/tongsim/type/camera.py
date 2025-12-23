"""
tongsim.type.camera
"""

from typing import NamedTuple


class CameraIntrinsic(NamedTuple):
    """
    Camera intrinsics.
    """

    fov: float
    width: int
    height: int


class VisibleObjectInfo(NamedTuple):
    """
    Information for a single visible object.
    """

    object_id: str
    segmentation_id: int
    distance_square: float
