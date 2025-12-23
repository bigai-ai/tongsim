"""
tongsim
"""

import typing
from importlib import import_module
from warnings import warn

from .version import VERSION

__version__ = VERSION

__all__ = (
    "AABB",
    "CaptureAPI",
    "Pose",
    "Quaternion",
    "TongSim",
    "Transform",
    "UnaryAPI",
    "Vector3",
    "__version__",
    "get_version_info",
    "initialize_logger",
    "math",
    "set_log_level",
)

if typing.TYPE_CHECKING:
    # Imported for IDE completion and type checking
    from . import math
    from .connection.grpc import CaptureAPI, UnaryAPI
    from .logger import initialize_logger, set_log_level
    from .math.geometry import AABB, Pose, Quaternion, Transform, Vector3
    from .tongsim import TongSim
    from .version import get_version_info

# Dynamic import map; package path is derived from `__spec__.parent`.
_dynamic_imports: dict[str, tuple[str, str]] = {
    # Math
    "Pose": (__spec__.parent, ".math.geometry"),
    "Quaternion": (__spec__.parent, ".math.geometry"),
    "Vector3": (__spec__.parent, ".math.geometry"),
    "AABB": (__spec__.parent, ".math.geometry"),
    "Transform": (__spec__.parent, ".math.geometry"),
    "math": (__spec__.parent, "."),
    # Core
    "TongSim": (__spec__.parent, ".tongsim"),
    # Logger
    "initialize_logger": (__spec__.parent, ".logger"),
    "set_log_level": (__spec__.parent, ".logger"),
    # gRPC
    "CaptureAPI": (__spec__.parent, ".connection.grpc"),
    "UnaryAPI": (__spec__.parent, ".connection.grpc"),
    # Version
    "get_version_info": (__spec__.parent, ".version"),
}

# Deprecated dynamic imports kept for backward compatibility.
_deprecated_imports = {}


def __getattr__(attr_name: str) -> object:
    """
    Lazily import module members and cache them on first access.
    """
    # Check deprecated names.
    if attr_name in _deprecated_imports:
        warn(
            f"Importing `{attr_name}` from `tongsim` is deprecated and will be removed in future versions.",
            DeprecationWarning,
            stacklevel=2,
        )

    # Check valid lazy members.
    dynamic_attr = _dynamic_imports.get(attr_name) or _deprecated_imports.get(attr_name)
    if dynamic_attr is None:
        raise AttributeError(f"Module 'tongsim' has no attribute '{attr_name}'")

    # Lazy import.
    package, module_path = dynamic_attr
    module = import_module(module_path, package=package)
    result = getattr(module, attr_name)

    # Cache into module globals to avoid repeated imports.
    globals()[attr_name] = result
    return result


def __dir__() -> list[str]:
    """Return a complete list of module members, including lazily imported ones."""
    return list(__all__)
