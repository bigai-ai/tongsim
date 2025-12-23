"""Navigation query example.

This script demonstrates two common utilities exposed by the TongSIM Python SDK:

1. Running a UE console command via `UnaryAPI.exec_console_command`
2. Querying a navigation path via `UnaryAPI.query_navigation_path`

Update `START` / `END` to points that are on (or near) a valid NavMesh in your map.
"""

from __future__ import annotations

import tongsim as ts
from tongsim.core.world_context import WorldContext

# ====== Config ======
GRPC_ENDPOINT = "127.0.0.1:5726"

# Pick two points known to be on/near your navmesh
START = ts.Vector3(200, -2000, 0)
END = ts.Vector3(1200, -2000, 0)


async def test_exec_console_command(context: WorldContext) -> None:
    print("\n[1] ExecConsoleCommand: 'stat fps'")
    ok = await ts.UnaryAPI.exec_console_command(
        context.conn, "stat fps", write_to_log=True, timeout=3.0
    )
    print("  - executed:", ok)


async def test_query_navigation_path(context: WorldContext) -> None:
    print("\n[2] QueryNavigationPath: default options")
    resp = await ts.UnaryAPI.query_navigation_path(
        context.conn,
        start=START,
        end=END,
        allow_partial=True,
        require_navigable_end_location=False,
        timeout=5.0,
    )
    if not resp:
        print("  - path not found")
        return

    points = resp["points"]
    print(f"  - points: {len(points)}")
    print(f"  - is_partial: {resp['is_partial']}")
    print(f"  - path_cost: {resp['path_cost']:.3f}")
    print(f"  - path_length: {resp['path_length']:.3f}")
    if points:
        print(f"  - first: {points[0]}")
        print(f"  - last : {points[-1]}")

    # (Optional) stricter query to demonstrate flags:
    print("\n[2.1] QueryNavigationPath: require_navigable_end_location + cost_limit")
    resp2 = await ts.UnaryAPI.query_navigation_path(
        context.conn,
        start=START,
        end=END,
        allow_partial=False,
        require_navigable_end_location=True,
        cost_limit=500.0,
        timeout=5.0,
    )
    if not resp2:
        print("  - path not found (strict)")
        return

    print(f"  - strict.is_partial: {resp2['is_partial']}")
    print(f"  - strict.path_length: {resp2['path_length']:.3f}")


async def run_all(context: WorldContext) -> None:
    await test_exec_console_command(context)
    await test_query_navigation_path(context)


def main() -> None:
    print("[INFO] Connecting to TongSim ...")
    with ts.TongSim(grpc_endpoint=GRPC_ENDPOINT) as ue:
        ue.context.sync_run(run_all(ue.context))
    print("[INFO] Done.")


if __name__ == "__main__":
    main()
