import time  # noqa: I001
import os
import argparse
import sys
import numpy as np

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor

import tongsim as ts
from collect_task import CollectTask
from common import para
from common.make_model import make_model
from common.manual import InputWrapper


class EnvStatsLogger(BaseCallback):
    def _on_step(self) -> bool:
        infos = self.locals.get("infos", [])
        for info in infos:
            if "avg_move_request_time_ms" in info:
                avg_ms = info["avg_move_request_time_ms"]
                self.logger.record("env/avg_move_request_time_ms", avg_ms)
        return True


log_dir = "./examples/rl_nav/logs/"
checkpoints_dir = f"{log_dir}/checkpoints/"
model_dir = "./examples/rl_nav/model/"


def make_env(grpc_endpoint, anchor, max_steps=1024, render_mode=None):
    """Creates a function that initializes a CollectTask environment with the specified anchor point."""

    def _init():
        ue = ts.TongSim(grpc_endpoint=grpc_endpoint)
        return CollectTask(
            ue=ue,
            anchor=anchor,
            grid_size=para.GRID_SIZE,
            view_size=para.VIEW_SIZE,
            max_steps=max_steps,
            render_mode=render_mode,
        )

    return _init


def train(model_name=None):
    """Trains the RL navigation model using multiple parallel environments."""
    with ts.TongSim(grpc_endpoint=para.GRPC_ENDPOINT) as ue:
        # reset level
        ue.context.sync_run(ts.UnaryAPI.reset_level(ue.context.conn))
        env_num = 25
        row_num = 5
        envs = SubprocVecEnv(
            [
                make_env(
                    grpc_endpoint=para.GRPC_ENDPOINT,
                    anchor=(x * 2000, y * 2000, 0),
                    max_steps=1024,
                    render_mode=None,
                )
                for i in range(env_num)
                for x, y in [divmod(i, row_num)]
            ]
        )
        envs = VecMonitor(envs, log_dir + "/vecmonitor_log")
        model = make_model(
            envs=envs,
            last_path=None if model_name is None else model_dir + model_name,
            tsboard_log_path=log_dir + "/tsboard_log",
        )

        checkpoint_callback = CheckpointCallback(
            save_freq=50_000 // env_num,
            save_path=model_dir,
            name_prefix="search_ppo",
        )
        try:
            model.learn(
                total_timesteps=1e9,
                callback=[checkpoint_callback, EnvStatsLogger()],
            )
        except Exception as e:
            print(f"[ERROR] error occurred while training: {e}")
            model.save(model_dir + "/search_ppo_crash")
            raise
        finally:
            model.save(model_dir + "search_ppo_final")


def test(model_name=None):
    model_path = None if model_name is None else model_dir + model_name
    if model_path is None or not os.path.exists(model_path):
        print("Error: model file not found.")
        return

    with ts.TongSim(grpc_endpoint=para.GRPC_ENDPOINT) as ue:
        # ts.initialize_logger(logging.INFO, True) #for debug
        ue.context.sync_run(ts.UnaryAPI.reset_level(ue.context.conn))
        max_steps = 1024
        env = make_env(
            grpc_endpoint=para.GRPC_ENDPOINT,
            anchor=(0, 0, 0),
            max_steps=max_steps,
            render_mode="human",
        )()
        model = PPO.load(
            path=model_path,
            env=env,
            deterministic=False,
        )
        total_steps = []
        episodes_num = 10
        for _ in range(episodes_num):
            obs, _ = env.reset()
            done = False
            total_reward = 0
            steps = 0
            while not done:
                steps += 1
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                done = terminated or truncated
                total_reward += reward
                env.render()
                time.sleep(0.001)
            print(f"steps={steps}", f"total_reward={total_reward}")
            total_steps.append(steps)

        # succeed = [s for s in total_steps if s < max_steps]
        # succeed_count = len(succeed)
        # sr = succeed_count / episodes_num
        # e = (
        #     sum((max_steps - s) / max_steps for s in succeed) / succeed_count
        #     if succeed_count > 0
        #     else 0.0
        # )
        # print(f"SR={sr}", f"E={e}")
        evl(total_steps, max_steps)
        env.close()


def manual():
    with ts.TongSim(grpc_endpoint=para.GRPC_ENDPOINT) as ue:
        ue.context.sync_run(ts.UnaryAPI.reset_level(ue.context.conn))
        max_steps = 1024
        env = make_env(
            grpc_endpoint=para.GRPC_ENDPOINT,
            anchor=(0, 0, 0),
            max_steps=max_steps,
            render_mode="human",
        )()
        env = InputWrapper(env)
        total_steps = []
        episodes_num = 10
        for _ in range(episodes_num):
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
            print(f"total_steps={steps}", f"total_reward={total_reward}")
            total_steps.append(steps)

        # succeed = [s for s in total_steps if s < max_steps]
        # succeed_count = len(succeed)
        # sr = succeed_count / episodes_num
        # e = (
        #     sum((max_steps - s) / max_steps for s in succeed) / succeed_count
        #     if succeed_count > 0
        #     else 0.0
        # )
        # print(f"SR={sr}", f"E={e}")
        evl(total_steps, max_steps)
        env.close()


def evl(total_steps: list, max_steps: int):
    """Evaluate the model performance."""
    if total_steps is None or len(total_steps) == 0:
        print("Error! No steps recorded.")
        return
    episodes_num = len(total_steps)
    succeed = [s for s in total_steps if s < max_steps]
    succeed_count = len(succeed)
    sr = succeed_count / episodes_num
    e = (
        sum((max_steps - s) / max_steps for s in succeed) / succeed_count
        if succeed_count > 0
        else 0.0
    )
    print(f"SR={sr}", f"E={e}")


def test_sps():
    """test steps per second"""

    with ts.TongSim(grpc_endpoint=para.GRPC_ENDPOINT) as ue:
        ue.context.sync_run(ts.UnaryAPI.reset_level(ue.context.conn))
        num_steps = 40960000000
        num_envs_list = [
            1,
            # 4,
            8,
            # 12,
            16,
            # 20,
            24,
            # 28,
            32,
            # 36,
            # 40,
            # 44,
            48,
            # 52,
            # 56,
            # 60,
            64,
            # 68,
            # 72,
            80,
            88,
            96,
            # 104,
            112,
            116,
            120,
            124,
            128,
        ]
        results = []
        row_num = 8
        WARMUP_STEPS = 512  # noqa: N806
        MEASURE_SECONDS = 30.0  # noqa: N806
        for n_envs in num_envs_list:
            ue.context.sync_run(ts.UnaryAPI.reset_level(ue.context.conn))
            env = SubprocVecEnv(
                [
                    make_env(
                        grpc_endpoint=para.GRPC_ENDPOINT,
                        anchor=(x * 2000, y * 2000, 0),
                        max_steps=num_steps,
                        render_mode=None,
                    )
                    for i in range(n_envs)
                    for x, y in [divmod(i, row_num)]
                ],
            )

            obs = env.reset()
            action_space = env.action_space
            for _ in range(WARMUP_STEPS):
                actions = np.array([action_space.sample() for _ in range(n_envs)])
                obs, rewards, dones, infos = env.step(actions)

            steps_total = 0
            t0 = time.perf_counter()
            while True:
                actions = np.array([action_space.sample() for _ in range(n_envs)])
                obs, rewards, dones, infos = env.step(actions)
                steps_total += n_envs

                if (time.perf_counter() - t0) >= MEASURE_SECONDS:
                    break

            elapsed = time.perf_counter() - t0
            sps = steps_total / elapsed
            print(f"N={n_envs:3d} | SPS={sps:8.2f} | elapsed={elapsed:.2f}s")
            results.append((n_envs, sps))
            env.close()
        print("Results (n_envs, FPS):")
        for n_envs, fps in results:
            print(f"n_envs: {n_envs}, FPS: {fps:.2f}")
        return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="run.py")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # train
    p_train = subparsers.add_parser("train", help="Run training")
    p_train.add_argument("--model_name", type=str, default=None)

    # test
    p_test = subparsers.add_parser("test", help="Run testing")
    p_test.add_argument("--model_name", type=str, default=None)

    # manual
    p_manual = subparsers.add_parser("manual", help="Run manual testing")

    args = parser.parse_args()

    args = parser.parse_args(["manual"]) if len(sys.argv) == 1 else parser.parse_args()

    if args.cmd == "train":
        print("begin train...")
        train(model_name=args.model_name)
    elif args.cmd == "test":
        print("begin test...")
        test(model_name=args.model_name)
    elif args.cmd == "manual":
        print("begin manual...")
        manual()
