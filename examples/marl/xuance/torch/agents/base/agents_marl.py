import os.path
import socket
from argparse import Namespace
from operator import itemgetter
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.distributed as dist
import wandb
import yaml
from gymnasium.spaces import Space
from torch import nn
from torch.distributed import destroy_process_group
from torch.utils.tensorboard import SummaryWriter

from xuance.common import Dict, List, Optional, Union, create_directory, get_time_string, space2shape
from xuance.torch import Module, ModuleDict, REGISTRY_Learners, REGISTRY_Representation
from xuance.torch.learners import learner
from xuance.torch.utils import ActivationFunctions, NormalizeFunctions, init_distributed_mode

from .callback import MultiAgentBaseCallback


def array_to_mp4_cv2(arr: np.ndarray, output_path: str, fps: int = 15):
    if arr.ndim != 5 or arr.shape[0] != 1 or arr.shape[2] != 3:
        raise ValueError("输入数组形状必须为 (1, N_frames, 3, H, W)")
    N, _C, H, W = arr.shape[1], arr.shape[2], arr.shape[3], arr.shape[4]

    newH, newW = H - (H % 2), W - (W % 2)
    if newH != H or newW != W:
        arr = arr[:, :, :, :newH, :newW]
        H, W = newH, newW
        print(f"[info] 尺寸裁剪为偶数: H={H}, W={W}")

    fourcc_candidates = [
        ("avc1", "H.264 (需要系统/FFmpeg支持)"),
        ("H264", "H.264 (部分平台可用)"),
        ("mp4v", "MPEG-4 Part 2 (兼容性一般)"),
    ]
    writer = None
    chosen = None
    for code, desc in fourcc_candidates:
        fourcc = cv2.VideoWriter_fourcc(*code)
        writer = cv2.VideoWriter(output_path, fourcc, fps, (W, H))
        if writer.isOpened():
            chosen = (code, desc)
            break
    if writer is None or not writer.isOpened():
        raise RuntimeError("无法打开 VideoWriter，请检查编码器/路径/权限。")

    print(f"[info] 使用编码器: {chosen[0]} - {chosen[1]}  @ {fps}fps, size=({W},{H})")

    written = 0
    try:
        for i in range(N):
            frame = arr[0, i]  # (3,H,W) RGB

            if frame.dtype != np.uint8:
                fmin, fmax = frame.min(), frame.max()

                if fmax <= 1.0 and fmin >= 0.0:
                    frame = (frame * 255.0).round()
                frame = np.clip(frame, 0, 255).astype(np.uint8)

            frame = np.transpose(frame, (1, 2, 0))
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            writer.write(frame_bgr)
            written += 1
    finally:
        writer.release()
        cv2.destroyAllWindows()

    size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
    print(f"[info] 写入帧数: {written}/{N}, 文件大小: {size / 1024:.1f} KB, 输出: {output_path}")
    if size < 5 * 1024:
        print("[warn] 文件体积异常小，可能编码失败或帧为空。尝试切换 fourcc 或检查输入数据。")


class MARLAgents:
    """Base class of agents for MARL.

    Args:
        config: the Namespace variable that provides hyperparameters and other settings.
        envs: the vectorized environments.
        callback: A user-defined callback function object to inject custom logic during training.
    """

    def __init__(self, config: Namespace, envs, callback: Optional[MultiAgentBaseCallback] = None):
        # Training settings.
        self.config = config
        self.use_rnn = getattr(config, "use_rnn", False)
        self.use_parameter_sharing = config.use_parameter_sharing
        self.use_actions_mask = getattr(config, "use_actions_mask", False)
        self.use_global_state = getattr(config, "use_global_state", False)
        self.distributed_training = config.distributed_training or False
        if self.distributed_training:
            self.world_size = int(os.environ["WORLD_SIZE"])
            self.rank = int(os.environ["RANK"])
            master_port = getattr(config, "master_port", None)
            init_distributed_mode(master_port=master_port)
        else:
            self.world_size = 1
            self.rank = 0

        self.gamma = config.gamma
        self.start_training = getattr(config, "start_training", 1)
        self.training_frequency = getattr(config, "training_frequency", 1)
        self.n_epochs = getattr(config, "n_epochs", 1)
        self.device = config.device

        # Environment attributes.
        self.envs = envs
        try:
            self.envs.reset()
        except Exception:
            pass
        self.n_agents = self.config.n_agents = envs.num_agents
        self.render = config.render
        self.fps = config.fps
        self.n_envs = envs.num_envs
        self.agent_keys = envs.agents
        self.state_space = envs.state_space if self.use_global_state else None
        self.observation_space = envs.observation_space
        self.action_space = envs.action_space
        self.episode_length = getattr(config, "episode_length", envs.max_episode_steps)
        self.config.episode_length = self.episode_length
        self.current_step = 0
        self.current_episode = np.zeros((self.n_envs,), np.int32)

        # Prepare directories.
        if self.distributed_training and self.world_size > 1:
            if self.rank == 0:
                time_string = get_time_string()
                time_string_tensor = torch.tensor(list(time_string.encode("utf-8")), dtype=torch.uint8).to(self.rank)
            else:
                time_string_tensor = torch.zeros(16, dtype=torch.uint8).to(self.rank)

            dist.broadcast(time_string_tensor, src=0)
            time_string = bytes(time_string_tensor.cpu().tolist()).decode("utf-8").rstrip("\x00")
        else:
            time_string = get_time_string()
        seed = f"seed_{config.seed}_"
        self.model_dir_load = config.model_dir
        self.model_dir_save = os.path.join(os.getcwd(), config.model_dir, seed + time_string)

        # Create logger.
        if config.logger == "tensorboard":
            log_dir = os.path.join(os.getcwd(), config.log_dir, seed + time_string)
            if self.rank == 0:
                create_directory(log_dir)
            else:
                while not os.path.exists(log_dir):
                    pass  # Wait until the master process finishes creating directory.
            self.writer = SummaryWriter(log_dir)
            self.use_wandb = False
        elif config.logger == "wandb":
            config_dict = vars(config)
            log_dir = config.log_dir
            wandb_dir = Path(os.path.join(os.getcwd(), config.log_dir))
            if self.rank == 0:
                create_directory(str(wandb_dir))
            else:
                while not os.path.exists(str(wandb_dir)):
                    pass  # Wait until the master process finishes creating directory.
            wandb.init(
                config=config_dict,
                project=config.project_name,
                entity=config.wandb_user_name,
                notes=socket.gethostname(),
                dir=wandb_dir,
                group=config.env_id,
                job_type=config.agent,
                name=time_string,
                reinit=True,
                settings=wandb.Settings(start_method="fork"),
            )
            # os.environ["WANDB_SILENT"] = "True"
            self.use_wandb = True
        else:
            raise AttributeError("No logger is implemented.")
        self.log_dir = log_dir
        yaml_config_path = config.log_dir
        yaml_config_path = os.path.join(os.getcwd(), yaml_config_path, seed + time_string, "config.yaml")

        with open(yaml_config_path, "w") as f:
            yaml.dump(vars(config), f)

        # predefine necessary components
        self.model_keys = [self.agent_keys[0]] if self.use_parameter_sharing else self.agent_keys
        self.policy: Optional[nn.Module] = None
        self.learner: Optional[learner] = None
        self.memory: Optional[object] = None
        self.callback = callback or MultiAgentBaseCallback()

    def store_experience(self, *args, **kwargs):
        raise NotImplementedError

    def save_model(self, model_name):
        if self.distributed_training:
            if self.rank > 0:
                return

        # save the neural networks
        if not os.path.exists(self.model_dir_save):
            os.makedirs(self.model_dir_save)
        model_path = os.path.join(self.model_dir_save, model_name)
        self.learner.save_model(model_path)

    def load_model(self, path, model=None, filter_prefix=None):
        # load neural networks
        if filter_prefix is None:
            filter_prefix = []
        self.learner.load_model(path, model, filter_prefix=filter_prefix)

    def log_infos(self, info: dict, x_index: int):
        """
        info: (dict) information to be visualized
        n_steps: current step
        """
        if self.use_wandb:
            for k, v in info.items():
                if v is None:
                    continue
                wandb.log({k: v}, step=x_index)
        else:
            for k, v in info.items():
                if v is None:
                    continue
                try:
                    self.writer.add_scalar(k, v, x_index)
                except Exception:
                    self.writer.add_scalars(k, v, x_index)

    def log_videos(self, info: dict, fps: int, x_index: int = 0):
        if self.use_wandb:
            for k, v in info.items():
                if v is None:
                    continue
                wandb.log({k: wandb.Video(v, fps=fps, format="gif")}, step=x_index)
        else:
            for k, v in info.items():
                if v is None:
                    continue
                array_to_mp4_cv2(v, f"/home/bigai/桌面/videos/{k}_{x_index}.mp4", fps=15)
                # self.writer.add_video(k, v, fps=fps, global_step=x_index)

    def _build_representation(
        self, representation_key: str, input_space: Union[Dict[str, Space], Dict[str, tuple]], config: Namespace
    ) -> Module:
        """
        Build representation for policies.

        Parameters:
            representation_key (str): The selection of representation, e.g., "Basic_MLP", "Basic_RNN", etc.
            config: The configurations for creating the representation module.

        Returns:
            representation (Module): The representation Module.
        """

        # build representations
        representation = ModuleDict()
        for key in self.model_keys:
            if self.use_rnn:
                hidden_sizes = {
                    "fc_hidden_sizes": self.config.fc_hidden_sizes,
                    "recurrent_hidden_size": self.config.recurrent_hidden_size,
                }
            else:
                hidden_sizes = getattr(config, "representation_hidden_size", None)
            input_representations = {
                "input_shape": space2shape(input_space[key]),
                "hidden_sizes": hidden_sizes,
                "normalize": NormalizeFunctions[config.normalize] if hasattr(config, "normalize") else None,
                "initialize": nn.init.orthogonal_,
                "activation": ActivationFunctions[config.activation],
                "kernels": getattr(config, "kernels", None),
                "strides": getattr(config, "strides", None),
                "filters": getattr(config, "filters", None),
                "fc_hidden_sizes": getattr(config, "fc_hidden_sizes", None),
                "N_recurrent_layers": getattr(config, "N_recurrent_layers", None),
                "rnn": getattr(config, "rnn", None),
                "dropout": getattr(config, "dropout", None),
                "device": self.device,
            }
            representation[key] = REGISTRY_Representation[representation_key](**input_representations)
            if representation_key not in REGISTRY_Representation:
                raise AttributeError(f"{representation_key} is not registered in REGISTRY_Representation.")
        return representation

    def _build_policy(self) -> Module:
        raise NotImplementedError

    def _build_learner(self, *args):
        return REGISTRY_Learners[self.config.learner](*args)

    def _build_inputs(self, obs_dict: List[dict], avail_actions_dict: Optional[List[dict]] = None):
        """
        Build inputs for representations before calculating actions.

        Parameters:
            obs_dict (List[dict]): Observations for each agent in self.agent_keys.
            avail_actions_dict (Optional[List[dict]]): Actions mask values, default is None.

        Returns:
            obs_input: The represented observations.
            agents_id: The agent id (One-Hot variables).
        """
        batch_size = len(obs_dict)
        bs = batch_size * self.n_agents if self.use_parameter_sharing else batch_size
        avail_actions_input = None

        if self.use_parameter_sharing:
            key = self.agent_keys[0]
            obs_array = np.array([itemgetter(*self.agent_keys)(data) for data in obs_dict])  # 1,3,115
            agents_id = torch.eye(self.n_agents).unsqueeze(0).expand(batch_size, -1, -1).to(self.device)  # 1,3,3
            avail_actions_array = (
                np.array([itemgetter(*self.agent_keys)(data) for data in avail_actions_dict])
                if self.use_actions_mask
                else None
            )
            if self.use_rnn:
                obs_input = {key: obs_array.reshape([bs, 1, -1])}
                agents_id = agents_id.reshape(bs, 1, -1)
                if self.use_actions_mask:
                    avail_actions_input = {key: avail_actions_array.reshape([bs, 1, -1])}
            else:
                obs_input = {key: obs_array.reshape([bs, -1])}
                agents_id = agents_id.reshape(bs, -1)
                if self.use_actions_mask:
                    avail_actions_input = {key: avail_actions_array.reshape([bs, -1])}
        else:
            agents_id = None
            if self.use_rnn:
                obs_input = {k: np.stack([data[k] for data in obs_dict]).reshape([bs, 1, -1]) for k in self.agent_keys}
                if self.use_actions_mask:
                    avail_actions_input = {
                        k: np.stack([data[k] for data in avail_actions_dict]).reshape([bs, 1, -1])
                        for k in self.agent_keys
                    }
            else:
                obs_input = {k: np.stack([data[k] for data in obs_dict]).reshape(bs, -1) for k in self.agent_keys}
                if self.use_actions_mask:
                    avail_actions_input = {
                        k: np.array([data[k] for data in avail_actions_dict]).reshape([bs, -1]) for k in self.agent_keys
                    }
        return obs_input, agents_id, avail_actions_input

    def action(self, **kwargs):
        raise NotImplementedError

    def train_epochs(self, *args, **kwargs):
        raise NotImplementedError

    def train(self, **kwargs):
        raise NotImplementedError

    def test(self, **kwargs):
        raise NotImplementedError

    def finish(self):
        if self.use_wandb:
            wandb.finish()
        else:
            self.writer.close()
        if self.distributed_training:
            if dist.get_rank() == 0:
                if os.path.exists(self.learner.snapshot_path):
                    if os.path.exists(os.path.join(self.learner.snapshot_path, "snapshot.pt")):
                        os.remove(os.path.join(self.learner.snapshot_path, "snapshot.pt"))
                    os.removedirs(self.learner.snapshot_path)
            destroy_process_group()


class RandomAgents:
    def __init__(self, args, envs, device=None):
        self.args = args
        self.n_agents = self.args.n_agents
        self.agent_keys = args.agent_keys
        self.action_space = self.args.action_space
        self.nenvs = envs.num_envs

    def action(self, obs_n, episode, test_mode, noise=False):
        rand_a = [[self.action_space[agent].sample() for agent in self.agent_keys] for e in range(self.nenvs)]
        random_actions = np.array(rand_a)
        return random_actions

    def load_model(self, model_dir):
        return
