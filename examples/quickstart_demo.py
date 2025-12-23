"""Quickstart demo (TongSIM Unary API / DemoRLService).

This is the "first simulation" script referenced by the docs. It demonstrates:

1. (Optional) switch to the demo level via a UE console command (`open <level>`)
2. Reset the level
3. Query global actor state
4. Spawn a few actors (a target + two mannequin agents)
5. Move actors towards target locations using different orientation modes
6. Run a line trace example

Set `AUTO_OPEN_LEVEL = False` if you want to run in the currently opened level.
"""

from __future__ import annotations

import asyncio
import time

import tongsim as ts
from tongsim.core.world_context import WorldContext
from tongsim.type.rl_demo import CollisionObjectType, RLDemoOrientationMode

GRPC_ENDPOINT = "127.0.0.1:5726"

# Optional: automatically switch to the demo level (so you don't need to open it manually in UE).
AUTO_OPEN_LEVEL = True
DEMO_LEVEL = "/Game/Developer/Maps/L_DemoRL"
OPEN_LEVEL_TIMEOUT_SEC = 30.0
OPEN_LEVEL_POLL_SEC = 0.5
OPEN_LEVEL_MIN_WAIT_SEC = 2.0

TARGET_BLUEPRINT = "/Game/Developer/DemoCoin/BP_DemoCoin.BP_DemoCoin_C"
AGENT_BLUEPRINT = (
    "/Game/Developer/Characters/UE4Mannequin/BP_UE4Mannequin.BP_UE4Mannequin_C"
)

# Targets for SimpleMoveTowards.
MOVE_TARGET_KEEP = ts.Vector3(1200, -2000, 0)
MOVE_TARGET_FACE = ts.Vector3(400, -1500, 0)
MOVE_TARGET_GIVEN = ts.Vector3(400, -2500, 0)

# Forward direction for ORIENTATION_GIVEN (only XY is used; Z is ignored by the server).
GIVEN_FORWARD = ts.Vector3(0, 1, 0)


async def _open_level_if_needed(context: WorldContext) -> None:
    if not AUTO_OPEN_LEVEL:
        return

    print(f"\n[0] OpenLevel -> {DEMO_LEVEL} ...")

    before = await ts.UnaryAPI.query_info(context.conn)
    before_count = len(before)

    accepted = await ts.UnaryAPI.exec_console_command(
        context.conn,
        command=f"open {DEMO_LEVEL}",
        write_to_log=True,
        timeout=2.0,
    )
    print("  - accepted:", accepted)
    if not accepted:
        return

    start = time.monotonic()
    deadline = start + OPEN_LEVEL_TIMEOUT_SEC
    saw_change = False
    prev_count: int | None = None
    stable = 0
    while time.monotonic() < deadline:
        actors = await ts.UnaryAPI.query_info(context.conn)
        count = len(actors)

        if count == 0:
            saw_change = True
            prev_count = None
            stable = 0
        else:
            if count != before_count:
                saw_change = True

            if saw_change:
                if prev_count == count:
                    stable += 1
                else:
                    prev_count = count
                    stable = 0

                if (
                    stable >= 2
                    and (time.monotonic() - start) >= OPEN_LEVEL_MIN_WAIT_SEC
                ):
                    break

        await asyncio.sleep(OPEN_LEVEL_POLL_SEC)


async def run_quickstart_demo(context: WorldContext) -> None:
    await _open_level_if_needed(context)

    # 1) ResetLevel
    print("\n[1] ResetLevel ...")
    ok = await ts.UnaryAPI.reset_level(context.conn)
    print("  - done:", ok)

    # 2) QueryState (global)
    print("\n[2] QueryState (global) ...")
    state_list = await ts.UnaryAPI.query_info(context.conn)
    print(f"  - actor count: {len(state_list)}")
    if state_list:
        print("  - first actor sample:")
        print(state_list[0])

    # 3) SpawnActor (with Transform / name / tags)
    print("\n[3] SpawnActor (target) ...")
    target_actor = await ts.UnaryAPI.spawn_actor(
        context.conn,
        blueprint=TARGET_BLUEPRINT,
        transform=ts.Transform(location=ts.Vector3(350, -2000, 200)),
        name="Quickstart_Target",
        tags=["RL_Target"],
        timeout=5.0,
    )
    if not target_actor:
        print("  - spawn failed!")
        return

    target_actor_id = target_actor["id"]
    print("  - spawned target:", target_actor)

    # 4) GetActorTransform
    print("\n[4] GetActorTransform ...")
    tf_before = await ts.UnaryAPI.get_actor_transform(context.conn, target_actor_id)
    print("  - transform (before set):")
    print(tf_before)

    # 5) SetActorTransform (teleport)
    print("\n[5] SetActorTransform (teleport) ...")
    set_ok = await ts.UnaryAPI.set_actor_transform(
        context.conn,
        target_actor_id,
        ts.Transform(location=ts.Vector3(450, -2000, 200)),
    )
    print("  - done:", set_ok)

    tf_after = await ts.UnaryAPI.get_actor_transform(context.conn, target_actor_id)
    print("  - transform (after set):")
    print(tf_after)

    # 6) GetActorState
    print("\n[6] GetActorState ...")
    actor_state = await ts.UnaryAPI.get_actor_state(context.conn, target_actor_id)
    print("  - actor_state:")
    print(actor_state)

    # Spawn two mannequin agents.
    agent_1 = await ts.UnaryAPI.spawn_actor(
        context.conn,
        blueprint=AGENT_BLUEPRINT,
        transform=ts.Transform(location=ts.Vector3(250, -2000, 200)),
        name="Quickstart_Agent1",
        timeout=5.0,
    )
    agent_2 = await ts.UnaryAPI.spawn_actor(
        context.conn,
        blueprint=AGENT_BLUEPRINT,
        transform=ts.Transform(location=ts.Vector3(1050, -2000, 200)),
        name="Quickstart_Agent2",
        timeout=5.0,
    )
    if not agent_1 or not agent_2:
        print("  - failed to spawn mannequin agents.")
        return

    # 7) SimpleMoveTowards — ORIENTATION_KEEP_CURRENT
    print("\n[7] SimpleMoveTowards (KEEP_CURRENT) ->", MOVE_TARGET_KEEP)
    current_location, hit = await ts.UnaryAPI.simple_move_towards(
        context.conn,
        actor_id=agent_1["id"],
        target_location=MOVE_TARGET_KEEP,
        orientation_mode=RLDemoOrientationMode.ORIENTATION_KEEP_CURRENT,
        timeout=3600.0,
    )
    print("  - current_location:", current_location)
    print("  - hit_result:", hit if hit else "None")

    if hit and hit["hit_actor"].tag == "RL_Coin":
        await ts.UnaryAPI.destroy_actor(
            context.conn, hit["hit_actor"].object_info.id.guid
        )

    # 8) SimpleMoveTowards — ORIENTATION_FACE_MOVEMENT
    print("\n[8] SimpleMoveTowards (FACE_MOVEMENT) ->", MOVE_TARGET_FACE)
    current_location, hit = await ts.UnaryAPI.simple_move_towards(
        context.conn,
        actor_id=agent_2["id"],
        target_location=MOVE_TARGET_FACE,
        orientation_mode=RLDemoOrientationMode.ORIENTATION_FACE_MOVEMENT,
        timeout=3600.0,
    )
    print("  - current_location:", current_location)
    print("  - hit_result:", hit if hit else "None")

    # 9) SimpleMoveTowards — ORIENTATION_GIVEN (only XY components of given_forward are used)
    print(
        "\n[9] SimpleMoveTowards (GIVEN forward=",
        GIVEN_FORWARD,
        ") ->",
        MOVE_TARGET_GIVEN,
    )
    current_location, hit = await ts.UnaryAPI.simple_move_towards(
        context.conn,
        actor_id=agent_1["id"],
        target_location=MOVE_TARGET_GIVEN,
        orientation_mode=RLDemoOrientationMode.ORIENTATION_GIVEN,
        given_forward=GIVEN_FORWARD,
        speed_uu_per_sec=100.0,
        timeout=3600.0,
    )
    print("  - current_location:", current_location)
    print("  - hit_result:", hit if hit else "None")

    # 10) single_line_trace_by_object
    print("\n[10] SingleLineTraceByObject ...")
    trace = await ts.UnaryAPI.single_line_trace_by_object(
        context.conn,
        jobs=[
            {
                "start": ts.Vector3(450, -2000, 200),
                "end": ts.Vector3(450, 0, 200),
                "object_types": [
                    CollisionObjectType.OBJECT_WORLD_STATIC,
                    CollisionObjectType.OBJECT_WORLD_DYNAMIC,
                    CollisionObjectType.OBJECT_PAWN,
                ],
            },
            {
                "start": ts.Vector3(450, -2000, 200),
                "end": ts.Vector3(450, -4000, 200),
                "object_types": [
                    CollisionObjectType.OBJECT_WORLD_STATIC,
                    CollisionObjectType.OBJECT_WORLD_DYNAMIC,
                    CollisionObjectType.OBJECT_PAWN,
                ],
            },
        ],
    )
    print(trace)


def main() -> None:
    print("[INFO] Connecting to TongSim ...")
    with ts.TongSim(grpc_endpoint=GRPC_ENDPOINT) as ue:
        ue.context.sync_run(run_quickstart_demo(ue.context))
    print("[INFO] Done.")


if __name__ == "__main__":
    main()
