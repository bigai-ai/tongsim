"""Capture API demonstration.

This script exercises the simplified gRPC capture interface by:
1. Creating a capture camera
2. Triggering synchronous snapshot captures with different payload options
3. Persisting the outputs under ``logs/capture_demo_*`` for inspection

The code is intentionally lightweight so it can be run alongside other
examples in ``examples/``.  It only relies on the standard
library and the SDK provided in this repository.
"""

from __future__ import annotations

import binascii
import struct
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any

import tongsim as ts
from tongsim.core.world_context import WorldContext
from tongsim_lite_protobuf import capture_pb2

GRPC_ENDPOINT = "127.0.0.1:5726"

LOG_ROOT = Path(__file__).resolve().parents[1] / "logs"
# Choose color image format: "png" (no loss) or "jpg" (smaller, lossy)
COLOR_FORMAT = "png"

CAPTURE_PARAMS: dict[str, Any] = {
    "width": 640,
    "height": 480,
    "fov_degrees": 90.0,
    "qps": 10.0,
    "enable_depth": True,
    "depth_near": 10.0,
    "depth_far": 5000.0,
    "depth_mode": capture_pb2.CaptureDepthMode.CAPTURE_DEPTH_LINEAR,
    "color_source": capture_pb2.CaptureColorSource.COLOR_SOURCE_FINAL_COLOR_LDR,
    "color_format": capture_pb2.CaptureRenderTargetFormat.COLOR_FORMAT_RGBA8,
    "rgb_codec": capture_pb2.CaptureRgbCodec.CAPTURE_RGB_CODEC_NONE,
    "depth_codec": capture_pb2.CaptureDepthCodec.CAPTURE_DEPTH_CODEC_NONE,
    "jpeg_quality": 95,
}


def _camera_tag(camera_id: Any) -> str:
    if isinstance(camera_id, bytes | bytearray):
        return camera_id.hex()
    if isinstance(camera_id, str):
        return camera_id
    return str(camera_id)


def _ensure_run_dir() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = LOG_ROOT / f"capture_demo_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _save_color_png(
    frame: dict[str, Any], path: Path, fmt: str | None = None
) -> Path | None:
    rgba = frame.get("rgba8")
    if not rgba:
        return None
    width = int(frame.get("width", 0))
    height = int(frame.get("height", 0))
    if width <= 0 or height <= 0:
        return None

    # Try Pillow for convenience (UE LDR render targets are typically BGRA8).
    try:
        from PIL import Image  # type: ignore

        # Interpret the source bytes as BGRA and convert to RGBA for saving.
        img = Image.frombytes("RGBA", (width, height), bytes(rgba), "raw", "BGRA")
        ext = (fmt or COLOR_FORMAT).lower()
        if ext == "jpg" or ext == "jpeg":
            # Convert to RGB for JPEG
            img = img.convert("RGB")
            out = path.with_suffix(".jpg")
            img.save(out, quality=95)
            return out
        out = path.with_suffix(".png")
        img.save(out)
        return out
    except Exception:
        pass

    # Minimal PNG encoder (convert BGRA -> RGBA, row-by-row, filter=0).
    def _crc(chunk_type: bytes, data: bytes) -> bytes:
        c = binascii.crc32(chunk_type)
        c = binascii.crc32(data, c)
        return struct.pack(">I", (c & 0xFFFFFFFF))

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + chunk_type + data + _crc(chunk_type, data)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    # each row: filter byte 0 + RGBA bytes
    raw = bytearray()
    mv = memoryview(rgba)
    row_bytes = width * 4
    for y in range(height):
        raw.append(0)
        start = y * row_bytes
        row = mv[start : start + row_bytes]
        # BGRA -> RGBA
        for x in range(width):
            b = row[x * 4 + 0]
            g = row[x * 4 + 1]
            r = row[x * 4 + 2]
            a = row[x * 4 + 3] if len(row) >= (x * 4 + 4) else 255
            raw += bytes((r, g, b, a))
    idat = zlib.compress(bytes(raw))
    png = sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")
    out = path.with_suffix(".png")
    out.write_bytes(png)
    return out


def _save_depth_exr(frame: dict[str, Any], path: Path) -> Path | None:
    depth_bytes = frame.get("depth_r32")
    if not depth_bytes:
        return None
    width = int(frame.get("width", 0))
    height = int(frame.get("height", 0))
    if width <= 0 or height <= 0:
        return None

    # Try OpenEXR if available
    try:
        import Imath  # type: ignore
        import OpenEXR  # type: ignore

        header = OpenEXR.Header(width, height)
        # single-channel float32 EXR (Z)
        ch = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
        header["channels"] = {"Z": ch}
        exr = OpenEXR.OutputFile(str(path.with_suffix(".exr")), header)
        exr.writePixels({"Z": bytes(depth_bytes)})
        exr.close()
        out = path.with_suffix(".exr")
    except Exception:
        # Fallback: write PFM (portable float map), many viewers can open it
        out = path.with_suffix(".pfm")
        with out.open("wb") as f:
            f.write(b"Pf\n")
            f.write(f"{width} {height}\n".encode("ascii"))
            # negative scale = little-endian floats per PFM spec
            f.write(b"-1.0\n")
            f.write(depth_bytes)

    # Also write quick stats
    minimum = float("inf")
    maximum = float("-inf")
    sample: list[float] = []
    for idx, (value,) in enumerate(struct.iter_unpack("<f", depth_bytes)):
        if value < minimum:
            minimum = value
        if value > maximum:
            maximum = value
        if idx < 10:
            sample.append(value)
    stats_path = out.with_suffix(out.suffix + ".txt")
    with stats_path.open("w", encoding="utf-8") as handle:
        count = len(depth_bytes) // 4
        handle.write(f"count={count}\nmin={minimum}\nmax={maximum}\nfirst10={sample}\n")
    return out


async def capture_demo(context: WorldContext) -> None:
    run_dir = _ensure_run_dir()
    print(f"[Capture] Logging to {run_dir}")

    conn = context.conn

    print("[Capture] Existing cameras:")
    for desc in await ts.CaptureAPI.list_cameras(conn):
        info = desc["camera"]
        print(
            "  -",
            info["name"],
            info["id"].hex() if isinstance(info["id"], bytes) else info["id"],
        )

    camera_id = await ts.CaptureAPI.create_camera(
        conn,
        transform=ts.Transform(location=ts.Vector3(200, 700, 200)),
        params=CAPTURE_PARAMS,
        capture_name="CaptureDemoCam",
    )

    if not camera_id:
        print("[Capture] Failed to create capture camera.")
        return

    camera_hex = _camera_tag(camera_id)
    print(f"[Capture] Created camera {camera_hex}")

    try:
        snapshot_full = await ts.CaptureAPI.capture_snapshot(
            conn,
            camera_id,
            include_color=True,
            include_depth=True,
            timeout_seconds=1.0,
        )
        if snapshot_full:
            full_color = run_dir / f"{camera_hex}_snapshot_full"
            full_depth = run_dir / f"{camera_hex}_snapshot_full.depth"
            color_path = _save_color_png(snapshot_full, full_color)
            depth_path = _save_depth_exr(snapshot_full, full_depth)
            print(
                "[Capture] Saved snapshot with color/depth to",
                (color_path.name if color_path else "<none>"),
                "and",
                (depth_path.name if depth_path else "<none>"),
            )

        snapshot_color = await ts.CaptureAPI.capture_snapshot(
            conn,
            camera_id,
            include_color=True,
            include_depth=False,
            timeout_seconds=1.0,
        )
        if snapshot_color:
            color_path = _save_color_png(
                snapshot_color, run_dir / f"{camera_hex}_snapshot_color"
            )
            if color_path:
                print("[Capture] Saved color-only snapshot to", color_path.name)

        snapshot_depth = await ts.CaptureAPI.capture_snapshot(
            conn,
            camera_id,
            include_color=False,
            include_depth=True,
            timeout_seconds=1.0,
        )
        if snapshot_depth:
            depth_path = _save_depth_exr(
                snapshot_depth, run_dir / f"{camera_hex}_snapshot_depth.depth"
            )
            if depth_path:
                print("[Capture] Saved depth-only snapshot to", depth_path.name)

        # Status is only meaningful for continuous capture; skip in snapshot-only demo

    finally:
        await ts.CaptureAPI.destroy_camera(conn, camera_id)
        print("[Capture] Capture camera cleaned up.")


def main() -> None:
    print("[Capture] Connecting to TongSim ...")
    with ts.TongSim(grpc_endpoint=GRPC_ENDPOINT) as ue:
        ue.context.sync_run(capture_demo(ue.context))
    print("[Capture] Demo finished. Check logs/capture_demo_* for outputs.")


if __name__ == "__main__":
    main()
