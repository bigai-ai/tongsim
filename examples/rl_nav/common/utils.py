import cv2
import numpy as np
from PIL import Image

import tongsim as ts
from tongsim.core.world_context import WorldContext

# from common import para


def decode_voxel(
    voxel_bytes: bytes, voxel_resolution: tuple[int, int, int]
) -> np.ndarray:
    """
    Efficient voxel bitstream decoding (LSB-first):
    - Input: bytes (length should be ceil(X*Y*Z/8))
    - Output: bool ndarray of shape (x, y, z)
    - Automatically trims the excess bits at the end
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


async def request_global_map(
    context: WorldContext, wx: int = 512, wy: int = 512, h: int = 64
):
    start_transform = ts.Transform(location=ts.Vector3(para.ROOM_CENTER))
    box_extent = ts.Vector3(para.ROOM_EXT)
    voxel_bytes = await ts.UnaryAPI.query_voxel(
        context.conn,
        start_transform,
        wx,
        wy,
        h,
        box_extent,
    )
    vox = decode_voxel(voxel_bytes, (wx, wy, h))
    vox_flattened = np.any(vox, axis=-1, keepdims=False)
    vox_flattened_img = vox_flattened.astype(np.uint8) * 255
    Image.fromarray(vox_flattened_img).save(
        f"./examples/rl_nav/occupy_grid/global_map_{wx}.png"
    )
    return vox_flattened


def down_sample(file_path: str, destiny_res: int = 128):
    vox_flattened_img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)

    # must be uint8
    downsampled_img = cv2.resize(
        vox_flattened_img, (destiny_res, destiny_res), interpolation=cv2.INTER_AREA
    )

    downsampled_img = (downsampled_img != 0).astype(np.uint8) * 255
    cv2.imwrite(
        f"./examples/rl_nav/occupy_grid/global_map_{destiny_res}_cv2.png",
        downsampled_img,
    )


def fill_contours(source_path: str, destiny_path: str):
    source_img = cv2.imread(source_path, cv2.IMREAD_GRAYSCALE)
    contours, _ = cv2.findContours(
        source_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    mask = np.ones_like(source_img)
    cv2.drawContours(mask, contours, -1, 0, -1)
    result = source_img.copy()
    result[mask == 1] = 255
    cv2.imwrite(destiny_path, result)


if __name__ == "__main__":
    import para

    with ts.TongSim(grpc_endpoint="127.0.0.1:5726") as ue:
        ue.context.sync_run(request_global_map(ue.context, wx=512, wy=512, h=64))

    down_sample("./examples/rl_nav/occupy_grid/global_map_512.png", 128)

    fill_contours(
        "./examples/rl_nav/occupy_grid/global_map_128_cv2.png",
        "./examples/rl_nav/occupy_grid/global_map_128.png",
    )
