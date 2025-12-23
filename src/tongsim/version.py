"""
TongSIM Lite version information.
"""

import platform
import sys

VERSION = "0.0.1"
"""The main version string of TongSIM Lite."""


def get_version_info() -> str:
    """
    Get version/runtime information for TongSIM Lite.

    Returns:
        str: A multi-line formatted string describing the current version state.
    """

    info = {
        "tongsim_lite version": VERSION,
        "python version": sys.version.replace("\n", " "),
        "platform": platform.platform(),
    }

    return "\n".join(f"{k:<20}: {v}" for k, v in info.items())
