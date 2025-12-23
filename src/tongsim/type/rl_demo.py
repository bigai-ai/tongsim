from enum import IntEnum


class RLDemoOrientationMode(IntEnum):
    """_summary_

    Args:
        IntEnum (_type_): _description_
    """

    ORIENTATION_KEEP_CURRENT = 0
    ORIENTATION_FACE_MOVEMENT = 1
    ORIENTATION_GIVEN = 2


class CollisionObjectType(IntEnum):
    """_summary_

    Args:
        IntEnum (_type_): _description_
    """

    OBJECT_WORLD_STATIC = 0
    OBJECT_WORLD_DYNAMIC = 1
    OBJECT_PAWN = 2
    OBJECT_PHYSICS_BODY = 3
    OBJECT_VEHICLE = 4
    OBJECT_DESTRUCTIBLE = 5


class RLDemoHandType(IntEnum):
    """Hand selection for DemoRL manipulation actions."""

    HAND_RIGHT = 0
    HAND_LEFT = 1
