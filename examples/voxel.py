"""Voxel query & rendering demo (TongSIM).

Run:
    uv run --with numpy, matplotlib ./examples/voxel.py

If matplotlib is not installed, the script prints a small ASCII preview instead.
"""

from __future__ import annotations

import asyncio
import random
import time
from pathlib import Path

import numpy as np

import tongsim as ts
from tongsim.core.world_context import WorldContext

# ====== Config ======
GRPC_ENDPOINT = "127.0.0.1:5726"
START_LOC = ts.Vector3(200, -2000, 0)
STOP_LOC = ts.Vector3(2000, -2000, 0)
VELOCITY = 200.0  # world units per second
QUERY_PERIOD = 1.0  # seconds; voxel query + render period
RES = (128, 128, 128)  # voxel resolution (X, Y, Z)
EXT = ts.Vector3(512, 512, 512)  # query box half extent
FRAMES_DIR = Path("./voxel_frames")  # output directory for rendered frames
MAX_DIM_TO_RENDER = 32  # downsample each axis to <= this value for rendering speed
SAVE_EVERY_N = 1  # save one frame every N queries
RUN_SECONDS = 300.0  # keep the script alive so the background task can run
# =====================


# ===== voxel decoding =====
def decode_voxel_byte(byte: int) -> list[bool]:
    """Return 8 bits (LSB -> MSB) as booleans."""
    return [((byte >> i) & 1) == 1 for i in range(8)]


def decode_voxel(
    voxel_bytes: bytes, voxel_resolution: tuple[int, int, int]
) -> np.ndarray:
    """
    Decode a packed voxel bitstream (LSB-first).

    - Input: `bytes` (length should be `ceil(X*Y*Z/8)`)
    - Output: bool ndarray with shape `(X, Y, Z)`
    - Extra tail bits (if any) are ignored
    """
    x, y, z = voxel_resolution
    num_voxel = x * y * z
    need_bytes = (num_voxel + 7) // 8
    if len(voxel_bytes) != need_bytes:
        raise ValueError(
            f"voxel_bytes length mismatch: expected {need_bytes}, got {len(voxel_bytes)}"
        )

    buf = np.frombuffer(voxel_bytes, dtype=np.uint8, count=need_bytes)
    bits = np.unpackbits(buf, bitorder="little")  # LSB-first
    bits = bits[:num_voxel].astype(bool, copy=False)
    return bits.reshape((x, y, z), order="C")


# ===== helpers & rendering =====
def _rand_nearby(
    center: ts.Vector3, radius_xy: float = 300.0, z_jitter: float = 0.0
) -> ts.Vector3:
    """Sample a random point near `center` (within a circular XY radius)."""
    ang = random.random() * 2.0 * np.pi
    r = (0.3 + 0.7 * random.random()) * radius_xy  # avoid being too close
    return ts.Vector3(
        center.x + float(r * np.cos(ang)),
        center.y + float(r * np.sin(ang)),
        center.z + (random.uniform(-z_jitter, z_jitter) if z_jitter > 0 else 0.0),
    )


def _v3_to_np(v: ts.Vector3) -> np.ndarray:
    return np.array([float(v.x), float(v.y), float(v.z)], dtype=np.float64)


def _np_to_v3(a: np.ndarray) -> ts.Vector3:
    return ts.Vector3(float(a[0]), float(a[1]), float(a[2]))


def _downsample_vox(vox: np.ndarray, max_dim: int = MAX_DIM_TO_RENDER) -> np.ndarray:
    """Downsample each axis so that `shape <= max_dim` and keep a boolean grid."""
    sx = max(1, int(np.ceil(vox.shape[0] / max_dim)))
    sy = max(1, int(np.ceil(vox.shape[1] / max_dim)))
    sz = max(1, int(np.ceil(vox.shape[2] / max_dim)))
    return vox[::sx, ::sy, ::sz]


def render_voxels_ascii(vox: np.ndarray, max_dim: int = MAX_DIM_TO_RENDER) -> str:
    """Render a small ASCII preview using an XY max-projection."""
    dv = _downsample_vox(vox, max_dim)
    if dv.size == 0:
        return "<empty voxel grid>"

    projection = dv.max(axis=2)  # (X, Y)
    lines: list[str] = []
    for row in projection:
        lines.append("".join("#" if cell else "." for cell in row))
    return "\n".join(lines)


def render_voxels(
    vox: np.ndarray, save_path: Path, title: str | None = None
) -> Path | None:
    """Render voxels with matplotlib (when available) and save to `save_path`."""

    try:
        import matplotlib

        # Use a headless backend to avoid window / GUI dependencies.
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    except Exception:
        print("[INFO] matplotlib not available; printing ASCII preview.")
        print(render_voxels_ascii(vox))
        return None

    dv = _downsample_vox(vox, MAX_DIM_TO_RENDER)
    if dv.size == 0:
        print("[WARN] Empty voxel grid; skip rendering.")
        return None

    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, projection="3d")
    # Keep the default style to avoid visual distractions.
    ax.voxels(dv)  # If this is slow, consider `ax.scatter(*np.where(dv))`.
    if title:
        ax.set_title(title)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    fig.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    return save_path


# ===== voxel demo task =====
async def show_voxel(context: WorldContext) -> None:
    """
    Periodically query a voxel grid around the agent and render it.

    You can replace the Python-side rendering with an in-engine DebugDraw if needed.
    """
    # Move between START_LOC and STOP_LOC (ping-pong).
    p0 = _v3_to_np(START_LOC)
    p1 = _v3_to_np(STOP_LOC)
    seg = p1 - p0
    total_dist = float(np.linalg.norm(seg)) if np.linalg.norm(seg) > 1e-6 else 1.0
    dir_unit = seg / total_dist

    cur = p0.copy()
    direction = +1.0  # +1 towards p1, -1 towards p0
    start_transform = ts.Transform(location=_np_to_v3(cur))

    tick = 0

    while True:
        step = VELOCITY * QUERY_PERIOD * direction
        cur = cur + dir_unit * step

        # Clamp to segment ends and flip direction.
        to_p0 = float(np.dot(cur - p0, dir_unit))
        if to_p0 <= 0.0:
            cur = p0.copy()
            direction = +1.0
        elif to_p0 >= total_dist:
            cur = p1.copy()
            direction = -1.0

        start_transform.location = _np_to_v3(cur)

        # === Query voxels ===
        voxel_bytes = await ts.UnaryAPI.query_voxel(
            context.conn, start_transform, RES[0], RES[1], RES[2], EXT
        )
        vox = decode_voxel(voxel_bytes, RES)

        # === Render ===
        tick += 1
        if tick % SAVE_EVERY_N == 0:
            fname = FRAMES_DIR / f"voxel_{tick:05d}.png"
            title = (
                f"Tick {tick}  Loc=({cur[0]:.1f},{cur[1]:.1f},{cur[2]:.1f})  Res={RES}"
            )
            saved = render_voxels(vox, fname, title)
            if saved:
                print(f"[RENDER] Saved: {saved}")

        await asyncio.sleep(QUERY_PERIOD)


# ===== entrypoint =====
def main() -> None:
    print("[INFO] Connecting to TongSim ...")
    with ts.TongSim(grpc_endpoint=GRPC_ENDPOINT) as ue:
        # Reset the level for a clean start.
        ue.context.sync_run(ts.UnaryAPI.reset_level(ue.context.conn))
        # Start the demo as a background task.
        ue.context.async_task(show_voxel(ue.context), "voxel")

        # Keep the main thread alive (so the background task can run).
        time.sleep(RUN_SECONDS)

    print("[INFO] Done.")


if __name__ == "__main__":
    main()
