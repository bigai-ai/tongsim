"""
Multi-arena (multi-level) parallel control demo.

This example shows how to:
- Load multiple arenas (sublevels) in parallel
- Spawn an agent + a few targets in each arena
- Move the agent with `UnaryAPI.simple_move_towards`
- Tear down arenas when finished

Run:
    uv run python examples/multilevel_parallel.py
"""

from __future__ import annotations

import asyncio
import random
import time

import tongsim as ts
from tongsim.core.world_context import WorldContext

GRPC_ENDPOINT = "127.0.0.1:5726"

# Your level assets (the same asset can be loaded multiple times).
LEVELS = [
    "/Game/Maps/Sublevels/SubLevel_005.SubLevel_005",
    "/Game/Maps/Sublevels/SubLevel_005.SubLevel_005",
    "/Game/Maps/Sublevels/SubLevel_005.SubLevel_005",
    "/Game/Maps/Sublevels/SubLevel_005.SubLevel_005",
    "/Game/Maps/Sublevels/SubLevel_005.SubLevel_005",
]

# Blueprint classes to spawn in each arena.
AGENT_BP = "/Game/TongSim/Characters/Weiguo_V01/BP_Weiguo.BP_Weiguo_C"
SPAWN_BLUEPRINT = "/Game/Developer/DemoCoin/BP_DemoCoin.BP_DemoCoin_C"


def arena_anchor_at(x: float) -> ts.Transform:
    # Offset each arena along X so that they don't overlap in world space.
    return ts.Transform(location=ts.Vector3(x, 0, 0))


async def run_one_arena(context: WorldContext, arena_id: str) -> None:
    # Spawn the agent in this arena (arena-local coordinates).
    spawned = await ts.UnaryAPI.spawn_actor_in_arena(
        context.conn,
        arena_id,
        AGENT_BP,
        ts.Transform(location=ts.Vector3(300, 580, 100)),
    )

    for _ in range(4):
        tgt = ts.Vector3(random.uniform(-100, 100), random.uniform(-100, 100), 0)
        await ts.UnaryAPI.spawn_actor_in_arena(
            context.conn,
            arena_id,
            SPAWN_BLUEPRINT,
            ts.Transform(location=ts.Vector3(300, 580, 100) + tgt),
        )

    if not spawned:
        print(f"[Arena {arena_id}] spawn failed.")
        return
    agent_id = spawned["id"]
    print(f"[Arena {arena_id}] agent:", spawned)

    # Run a small random-walk loop inside this arena.
    for _ in range(30):
        tgt = ts.Vector3(random.uniform(-100, 100), random.uniform(-100, 100), 0)
        cur_transform = await ts.UnaryAPI.get_actor_transform(context.conn, agent_id)
        _current_location, hit = await ts.UnaryAPI.simple_move_towards(
            context.conn,
            actor_id=agent_id,
            target_location=cur_transform.location + tgt,
            speed_uu_per_sec=120.0,
            timeout=3600.0,
        )
        if hit and hit["hit_actor"].tag == "RL_Coin":
            print(f"[Arena {arena_id}] hit RL_Coin, destroying it.")
            await ts.UnaryAPI.destroy_actor(
                context.conn, hit["hit_actor"].object_info.id.guid
            )
        # await asyncio.sleep(0.05)  # 20Hz


async def run(context: WorldContext) -> None:
    # 1) Load arenas (offset along X by 3000 units each).
    arena_ids: list[str] = []
    for i, level in enumerate(LEVELS):
        aid = await ts.UnaryAPI.load_arena(
            context.conn,
            level_asset_path=level,
            anchor=arena_anchor_at(3000 * i),
            make_visible=True,
        )
        if not aid:
            print(f"[load_arena] failed: {level}")
            continue
        arena_ids.append(aid)
    print("Arenas:", await ts.UnaryAPI.list_arenas(context.conn))

    # 2) Control arenas in parallel.
    await asyncio.gather(*(run_one_arena(context, aid) for aid in arena_ids))

    # 3) Tear down arenas (optional reset shown below).
    for aid in arena_ids:
        # await ts.UnaryAPI.reset_arena(context.conn, aid)
        await ts.UnaryAPI.destroy_arena(context.conn, aid)


def main() -> None:
    print("[INFO] Connecting to TongSim ...")
    with ts.TongSim(grpc_endpoint=GRPC_ENDPOINT) as ue:
        ue.context.sync_run(ts.UnaryAPI.reset_level(ue.context.conn))
        while True:
            ue.context.sync_run(run(ue.context))
            time.sleep(3.0)

    print("[INFO] Done.")


if __name__ == "__main__":
    main()
