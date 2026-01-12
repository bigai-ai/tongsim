import math
import os
import random
import time
from typing import ClassVar

import cv2
import gymnasium as gym
import numpy as np
import pygame
from common import para
from common.high_level_policy import HighLevelPolicy, is_safe_frontier
from common.manual import InputWrapper
from gymnasium import spaces

import tongsim as ts
from tongsim.connection.grpc.unary_api import _fguid_bytes_to_str
from tongsim.math import Transform, euler_to_quaternion


class CollectTask(gym.Env):
    metadata: ClassVar[dict[str, object]] = {
        "render_modes": ["human"],
        "render_fps": 30,
    }

    def __init__(
        self,
        ue: ts.TongSim,
        anchor,
        grid_size: int = para.GRID_SIZE,
        view_size: int = para.VIEW_SIZE,
        max_steps: int = 1024,
        render_mode=None,
    ):
        super().__init__()
        self.anchor = anchor
        self.ue = ue
        self.arena_id = None

        self.grid_size = grid_size
        self.view_size = view_size
        self.max_steps = max_steps
        self.step_count = 0

        self.upper_policy = HighLevelPolicy(map_size=(grid_size, grid_size))

        self.render_mode = render_mode
        self.window = None

        self.action_space = spaces.MultiDiscrete([4, 2])
        self.step_lens = [1, 2]

        tgt_dir_max = 25
        self.observation_space = spaces.Dict(
            {
                "grid_tensor": spaces.Box(
                    low=0,
                    high=1,
                    shape=(3, view_size, view_size),
                    dtype=np.uint8,
                ),
                "target_direction": spaces.Box(
                    low=np.array([-tgt_dir_max, -tgt_dir_max]),
                    high=np.array([tgt_dir_max, tgt_dir_max]),
                    shape=(2,),
                    dtype=np.int8,
                ),
            }
        )

    def _get_obs(self):
        observation = np.zeros((3, self.view_size, self.view_size), dtype=np.uint8)
        local_view = self._get_local_view(pos=self.agent_pos, view_size=self.view_size)

        # obstacle
        observation[0] = (local_view == para.OBS).astype(np.uint8)

        # target
        observation[1] = (local_view == para.GOAL).astype(np.uint8)
        goal_coords = np.argwhere(local_view == para.GOAL)
        for x, y in goal_coords:
            x_min = max(0, x - para.GOAL_PIX)
            x_max = min(local_view.shape[0], x + para.GOAL_PIX + 1)
            y_min = max(0, y - para.GOAL_PIX)
            y_max = min(local_view.shape[1], y + para.GOAL_PIX + 1)
            observation[1][x_min:x_max, y_min:y_max] = 1

        # agent
        observation[2] = (local_view == para.AGENT).astype(np.uint8)
        center_x, center_y = self.view_size // 2, self.view_size // 2
        x_min = max(0, center_x - para.AGENT_PIX)
        x_max = min(self.view_size, center_x + para.AGENT_PIX + 1)
        y_min = max(0, center_y - para.AGENT_PIX)
        y_max = min(self.view_size, center_y + para.AGENT_PIX + 1)
        observation[2][x_min:x_max, y_min:y_max] = 1

        if self.current_global_goal:
            target_direction = np.array(self.current_global_goal) - np.array(
                self.agent_pos
            )
            if (
                abs(target_direction[0]) <= para.VIEW_SIZE // 2
                and abs(target_direction[1]) <= para.VIEW_SIZE // 2
            ):
                observation[1][
                    target_direction[0] + self.view_size // 2,
                    target_direction[1] + self.view_size // 2,
                ] = 1

        else:
            target_direction = np.array([0, 0])

        clipped_target_direction = np.clip(
            target_direction,
            self.observation_space["target_direction"].low,
            self.observation_space["target_direction"].high,
        )

        return {
            "grid_tensor": observation.astype(np.uint8),
            "target_direction": clipped_target_direction,
        }

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            np.random.seed(seed)

        self.step_count = 0
        self.move_request_time_total = 0

        if self.arena_id:
            # reset
            self.ue.context.sync_run(
                ts.UnaryAPI.reset_arena(self.ue.context.conn, self.arena_id)
            )
        else:
            # load
            arena_id = self.ue.context.sync_run(
                ts.UnaryAPI.load_arena(
                    self.ue.context.conn,
                    level_asset_path=para.SUB_LEVEL,
                    anchor=ts.Transform(location=ts.Vector3(self.anchor)),
                    make_visible=True,
                )
            )
            # todo Check if the loading is successful
            self.arena_id = arena_id

        self.global_map = self.get_global_map()
        self.gen_goal()
        self.gen_agent()
        self.upper_policy = HighLevelPolicy(map_size=(self.grid_size, self.grid_size))
        local_view = self._get_local_view(self.agent_pos, self.view_size)
        self.upper_policy.update(local_view, tuple(self.agent_pos))
        self.current_global_goal = self.upper_policy.get_global_goal(force_update=True)
        obs = self._get_obs()
        return obs, {}

    def step(self, action):
        return self.step_ue(action)
        # return self.step_grid(action)

    def step_ue(self, action):  # noqa: C901
        reward = -0.1
        terminated = False
        truncated = False
        self.step_count += 1
        force_update_goal = False

        old_agent_pos = self.agent_pos
        x_idx_new, y_idx_new = self.agent_pos
        direction_idx, steplengh_idx = action

        match direction_idx:
            case 0:
                x_idx_new += self.step_lens[steplengh_idx]
            case 1:
                x_idx_new -= self.step_lens[steplengh_idx]
            case 2:
                y_idx_new += self.step_lens[steplengh_idx]
            case 3:
                y_idx_new -= self.step_lens[steplengh_idx]

        x_idx_new = np.clip(x_idx_new, 0, self.grid_size - 1)
        y_idx_new = np.clip(y_idx_new, 0, self.grid_size - 1)

        old_agent_loc: ts.Vector3 = ts.Vector3(self.agent_loc)
        target_loc: ts.Vector3 = ts.Vector3(old_agent_loc)

        target_loc.x = (x_idx_new + 0.5) * para.GRID_RES - para.TRANS_X + self.anchor[0]
        target_loc.y = (y_idx_new + 0.5) * para.GRID_RES + self.anchor[1]

        start = time.perf_counter()
        cur_loc, hit = self.ue.context.sync_run(
            ts.UnaryAPI.simple_move_towards(
                self.ue.context.conn,
                actor_id=self.agent_id,
                target_location=target_loc,
                orientation_mode=1,  # ORIENTATION_FACE_MOVEMENT = 1
                tolerance_uu=0.5,
            )
        )
        self.move_request_time_total += time.perf_counter() - start

        cur_loc = cur_loc - ts.Vector3(self.anchor)
        self.agent_loc = ts.Vector3(cur_loc)

        if hit:
            if hit["hit_actor"].tag == "RL_Coin":
                reward += 50.0
                goal_id = hit["hit_actor"].object_info.id.guid
                destoryok = self.ue.context.sync_run(
                    ts.UnaryAPI.arena_destroy_actor(
                        self.ue.context.conn, self.arena_id, goal_id
                    )
                )
                pos = self.id_to_pos[_fguid_bytes_to_str(goal_id)]
                self.global_map[pos[0], pos[1]] = para.FREE
            else:
                reward -= 0.5

            det_pix = (cur_loc - old_agent_loc) / para.GRID_RES
            det_x = int(det_pix.x)
            det_y = int(det_pix.y)
            match direction_idx:
                case 0:  # x up
                    if is_safe_frontier(
                        self.global_map,
                        (old_agent_pos[0] + det_x + 1, old_agent_pos[1]),
                        para.AGENT_PIX,
                    ):
                        x_idx_new = old_agent_pos[0] + det_x + 1
                    else:
                        x_idx_new = old_agent_pos[0] + det_x
                case 1:  # x down
                    if is_safe_frontier(
                        self.global_map,
                        (old_agent_pos[0] + det_x - 1, old_agent_pos[1]),
                        para.AGENT_PIX,
                    ):
                        x_idx_new = old_agent_pos[0] + det_x - 1
                    else:
                        x_idx_new = old_agent_pos[0] + det_x
                case 2:  # y up
                    if is_safe_frontier(
                        self.global_map,
                        (old_agent_pos[0], old_agent_pos[1] + det_y + 1),
                        para.AGENT_PIX,
                    ):
                        y_idx_new = old_agent_pos[1] + det_y + 1
                    else:
                        y_idx_new = old_agent_pos[1] + det_y
                case 3:  # y down
                    if is_safe_frontier(
                        self.global_map,
                        (old_agent_pos[0], old_agent_pos[1] + det_y - 1),
                        para.AGENT_PIX,
                    ):
                        y_idx_new = old_agent_pos[1] + det_y - 1
                    else:
                        y_idx_new = old_agent_pos[1] + det_y

        surrounding = self._get_local_view(
            pos=(x_idx_new, y_idx_new), view_size=(para.AGENT_PIX * 2) + 1
        )
        coords = np.argwhere(surrounding == para.OBS)
        if len(coords) > 0:
            reward -= 0.5

        self.agent_pos = (x_idx_new, y_idx_new)
        expected_loc = ts.Vector3(
            (x_idx_new + 0.5) * para.GRID_RES - para.TRANS_X,
            (y_idx_new + 0.5) * para.GRID_RES,
            cur_loc.z,
        )
        det_loc = cur_loc - expected_loc
        d = math.sqrt(det_loc.x * det_loc.x + det_loc.y * det_loc.y)
        if d > 2.0:
            self.ue.context.sync_run(
                ts.UnaryAPI.set_actor_pose_local(
                    self.ue.context.conn,
                    arena_id=self.arena_id,
                    actor_id=self.agent_id,
                    local_transform=ts.Transform(location=expected_loc),
                )
            )

        self.global_map[old_agent_pos[0], old_agent_pos[1]] = para.FREE
        self.global_map[self.agent_pos[0], self.agent_pos[1]] = para.AGENT

        x1, y1 = self.current_global_goal
        x2, y2 = self.agent_pos
        dist = para.AGENT_PIX + para.GOAL_PIX
        if abs(x2 - x1) <= dist and abs(y2 - y1) <= dist:
            if (
                self.global_map[
                    self.current_global_goal[0], self.current_global_goal[1]
                ]
                == para.GOAL
            ):
                for goal_id, pos in self.id_to_pos.items():
                    if pos == self.current_global_goal:
                        destoryok = self.ue.context.sync_run(
                            ts.UnaryAPI.arena_destroy_actor(
                                self.ue.context.conn, self.arena_id, goal_id
                            )
                        )
                        if destoryok:
                            self.global_map[
                                self.current_global_goal[0],
                                self.current_global_goal[1],
                            ] = para.FREE
                            reward += 50.0
                        break
            else:
                reward += 20.0
            force_update_goal = True
        else:
            manhattan_dis = abs(x2 - x1) + abs(y2 - y1)
            x2, y2 = old_agent_pos
            manhattan_dis_old = abs(x2 - x1) + abs(y2 - y1)
            reward += (manhattan_dis_old - manhattan_dis) * 0.2

        local_view = self._get_local_view(self.agent_pos, self.view_size)

        self.upper_policy.update(local_view, self.agent_pos)

        self.current_global_goal = self.upper_policy.get_global_goal(
            force_update=force_update_goal
        )

        if self.step_count >= self.max_steps:
            truncated = True
        if self.current_global_goal is None:
            terminated = True

        obs = self._get_obs()
        self.render()
        info = {}
        if truncated or terminated:
            avg = self.move_request_time_total / self.step_count
            info["avg_move_request_time_ms"] = avg * 1000  # unit:ms

        return obs, reward, terminated, truncated, info

    def render(self):  # noqa: C901
        if self.render_mode is None:
            return None
        self.window_size = 1024

        if self.window is None and self.render_mode == "human":
            pygame.init()
            pygame.display.init()
            self.window = pygame.display.set_mode((self.window_size, self.window_size))
            self.clock = pygame.time.Clock()

        canvas = pygame.Surface((self.window_size, self.window_size))
        canvas.fill((255, 255, 255))

        pix_square_size = self.window_size / self.grid_size

        for x in range(self.grid_size):
            for y in range(self.grid_size):
                # cell_type = self.global_map[x, y]
                cell_type = self.upper_policy.internal_map[x, y]

                if cell_type == para.AGENT:
                    color = (0, 0, 255)  # 蓝色

                    # agent
                    x_start = max(0, x - para.AGENT_PIX)
                    y_start = max(0, y - para.AGENT_PIX)
                    x_end = min(self.grid_size, x + para.AGENT_PIX + 1)
                    y_end = min(self.grid_size, y + para.AGENT_PIX + 1)

                    pygame.draw.rect(
                        canvas,
                        color,
                        pygame.Rect(
                            pix_square_size * y_start,
                            pix_square_size * x_start,
                            pix_square_size * (y_end - y_start),
                            pix_square_size * (x_end - x_start),
                        ),
                        # width=2,
                    )
                else:
                    if cell_type == para.OBS:
                        color = (255, 0, 0)
                    elif cell_type == para.GOAL:
                        color = (0, 255, 0)
                    elif cell_type == para.FREE:
                        color = (240, 240, 240)
                        continue
                    else:  # unknow
                        color = (128, 128, 128)

                    pygame.draw.rect(
                        canvas,
                        color,
                        pygame.Rect(
                            pix_square_size * y,
                            pix_square_size * x,
                            pix_square_size,
                            pix_square_size,
                        ),
                    )

        if (
            hasattr(self, "current_global_goal")
            and self.current_global_goal is not None
        ):
            # curr global goal
            goal_x, goal_y = self.current_global_goal
            pygame.draw.rect(
                canvas,
                (0, 0, 0),
                pygame.Rect(
                    pix_square_size * goal_y,
                    pix_square_size * goal_x,
                    pix_square_size,
                    pix_square_size,
                ),
                width=3,
            )

        # grid line
        for x in range(self.grid_size + 1):
            pygame.draw.line(
                canvas,
                (0, 0, 0),
                (0, pix_square_size * x),
                (self.window_size, pix_square_size * x),
                width=1,
            )
        for y in range(self.grid_size + 1):
            pygame.draw.line(
                canvas,
                (0, 0, 0),
                (pix_square_size * y, 0),
                (pix_square_size * y, self.window_size),
                width=1,
            )

        # flip vertically so the display matches the world frame (avoid upside-down view)
        canvas_to_display = pygame.transform.flip(canvas, False, True)

        if self.render_mode == "human":
            self.window.blit(canvas_to_display, canvas_to_display.get_rect())
            pygame.event.pump()
            pygame.display.update()
            self.clock.tick(self.metadata["render_fps"])
        else:  # rgb_array
            return np.transpose(
                np.array(pygame.surfarray.pixels3d(canvas_to_display)), axes=(1, 0, 2)
            )
        return None

    def close(self):
        pass

    def gen_goal(self):
        self.goal_num = random.randint(3, 8)
        self.id_to_pos = {}
        spawn_errors = 0
        for _ in range(self.goal_num):
            area_id = np.random.randint(0, 7)
            area = para.AREA_LIST[area_id]
            x = np.random.uniform(area[0][0], area[1][0])
            y = np.random.uniform(area[0][1], area[1][1])
            z = 5.0

            x_idx = int((x + para.TRANS_X) / para.GRID_RES)
            y_idx = int(y / para.GRID_RES)
            x = (x_idx + 0.5) * para.GRID_RES - para.TRANS_X
            y = (y_idx + 0.5) * para.GRID_RES
            location = ts.Vector3(x, y, z)
            paper_used_tf = Transform(location=location)

            spawned = self.ue.context.sync_run(
                ts.UnaryAPI.spawn_actor_in_arena(
                    self.ue.context.conn,
                    arena_id=self.arena_id,
                    class_path=para.BP_PAPER_USED,
                    local_transform=paper_used_tf,
                )
            )

            if spawned is not None:
                id = spawned["id"]
                if (
                    x_idx >= 0
                    and x_idx < self.grid_size
                    and y_idx >= 0
                    and y_idx < self.grid_size
                ):
                    # add goal to global_map
                    self.global_map[x_idx, y_idx] = para.GOAL
                    # record goal：id->pos
                    self.id_to_pos[id] = (x_idx, y_idx)
            else:
                spawn_errors += 1
                print("spawn failed!")

        self.goal_num -= spawn_errors

    def gen_agent(self):
        area_id = np.random.randint(0, 7)
        area = para.AREA_LIST[area_id]
        x = np.random.uniform(area[0][0], area[1][0])
        y = np.random.uniform(area[0][1], area[1][1])
        z = 58.0

        x_idx = int((x + para.TRANS_X) / para.GRID_RES)
        y_idx = int(y / para.GRID_RES)
        x = (x_idx + 0.5) * para.GRID_RES - para.TRANS_X
        y = (y_idx + 0.5) * para.GRID_RES
        location = ts.Vector3(x, y, z)

        nums = [0.0, -180.0, 90.0, -90.0]  # x+ x-  y+ y-
        idx = random.randrange(len(nums))
        euler = nums[idx]
        self.orientation = idx
        rotation = euler_to_quaternion(ts.Vector3(0.0, 0.0, euler), is_degree=True)

        agent_tf = Transform(location=location, rotation=rotation)

        spawned = self.ue.context.sync_run(
            ts.UnaryAPI.spawn_actor_in_arena(
                self.ue.context.conn, self.arena_id, para.BP_AGENT, agent_tf
            )
        )

        if not spawned:
            print(f"[Arena {self.arena_id}] spawn failed.")
            return
        agent_id = spawned["id"]
        # print(f"[Arena {self.arena_id}] agent:", spawned)
        self.agent_id = agent_id

        if (
            x_idx >= 0
            and x_idx < self.grid_size
            and y_idx >= 0
            and y_idx < self.grid_size
        ):
            # add agent to global_map
            self.global_map[x_idx, y_idx] = para.AGENT
            self.agent_pos = [x_idx, y_idx]
            self.agent_loc = location

    def get_global_map(self):
        map_path = f"./examples/rl_nav/occupy_grid/global_map_{para.ROOM_RES[0]}.png"
        global_map = None
        if os.path.exists(map_path):
            source_img = np.array(cv2.imread(map_path, cv2.IMREAD_GRAYSCALE))
            global_map = np.where(source_img == 255, para.OBS, para.FREE)
        return global_map

    def _get_local_view(self, pos, view_size, fill_value=para.OBS):
        global_map = self.global_map
        center_x, center_y = pos

        if not isinstance(view_size, int) or view_size <= 0 or view_size % 2 == 0:
            raise ValueError("view_size must be an odd positive number")

        half_view = view_size // 2

        start_x = center_x - half_view
        end_x = center_x + half_view + 1
        start_y = center_y - half_view
        end_y = center_y + half_view + 1

        local_view = np.full((view_size, view_size), fill_value, dtype=global_map.dtype)

        actual_start_x = max(start_x, 0)
        actual_end_x = min(end_x, global_map.shape[0])
        actual_start_y = max(start_y, 0)
        actual_end_y = min(end_y, global_map.shape[1])

        result_start_x = actual_start_x - start_x
        result_end_x = result_start_x + (actual_end_x - actual_start_x)
        result_start_y = actual_start_y - start_y
        result_end_y = result_start_y + (actual_end_y - actual_start_y)

        if (actual_start_x < actual_end_x) and (actual_start_y < actual_end_y):
            local_view[result_start_x:result_end_x, result_start_y:result_end_y] = (
                global_map[actual_start_x:actual_end_x, actual_start_y:actual_end_y]
            )

        return local_view


def test():
    env_num = 1
    row_num = 5
    GRPC_ENDPOINT = "127.0.0.1:5726"  # noqa: N806
    with ts.TongSim(grpc_endpoint=GRPC_ENDPOINT) as ue:
        ue.context.sync_run(ts.UnaryAPI.reset_level(ue.context.conn))

        envs = [
            CollectTask(
                ue=ue,
                grid_size=para.GRID_SIZE,
                view_size=para.VIEW_SIZE,
                anchor=(x * 2000, y * 2000, 0),
            )
            for i in range(env_num)
            for x, y in [divmod(i, row_num)]
        ]

        env = envs[0]
        env.render_mode = "human"
        env = InputWrapper(env)

        for _ in range(10):
            obs, _ = env.reset()
            done = False
            total_reward = 0
            steps = 0
            while not done:
                steps += 1
                obs, reward, terminated, truncated, info = env.step()
                done = terminated or truncated
                total_reward += reward
                env.render()
                time.sleep(0.01)
            print(f"steps={steps}", f"total_reward={total_reward}")
        env.close()


if __name__ == "__main__":
    test()
