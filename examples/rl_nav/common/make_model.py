import os

import torch
import torch.nn as nn
from stable_baselines3 import PPO
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor

# from stable_baselines3.common.utils import LinearSchedule


# for cnn features extractor
class FeaturesExtractor(BaseFeaturesExtractor):
    def __init__(self, observation_space, features_dim=256):
        super().__init__(observation_space, features_dim)

        # 1. (grid_tensor)
        n_input_channels = observation_space["grid_tensor"].shape[0]
        self.cnn = nn.Sequential(
            nn.Conv2d(
                n_input_channels, 64, kernel_size=5, stride=1, padding=2
            ),  # 64x19x19
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1),  # 64x19x19
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2),  # 64x9x9 (19/2=9.5->9)
            nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1),  # 128x9x9
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),  # 128x1x1
            nn.Flatten(),
        )

        with torch.no_grad():
            sample = torch.as_tensor(
                observation_space["grid_tensor"].sample()[None]
            ).float()
            n_cnn_features = self.cnn(sample).shape[1]

        # 2. (target_direction)
        self.vector_dim = observation_space["target_direction"].shape[0]
        self.process_vector = nn.Sequential(nn.Linear(self.vector_dim, 16), nn.ReLU())
        n_vector_features = 16

        # 3. linear fusion
        self.fusion_linear = nn.Sequential(
            nn.Linear(n_cnn_features + n_vector_features, features_dim), nn.ReLU()
        )

    def forward(self, observations):
        grid_features = self.cnn(observations["grid_tensor"])
        vector_features = self.process_vector(observations["target_direction"])
        combined_features = torch.cat([grid_features, vector_features], dim=1)
        return self.fusion_linear(combined_features)


policy_kwargs = {
    "features_extractor_class": FeaturesExtractor,
    "features_extractor_kwargs": {"features_dim": 256},
}


def make_model(envs, last_path, tsboard_log_path):
    if last_path is not None and os.path.exists(last_path):
        print(f"[INFO] load already trained model: {last_path}")
        model = PPO.load(last_path, env=envs)
    else:
        print("[INFO] not found trained model, create a new model.")
        # lr_schedule = LinearSchedule(start=2e-4, end=2e-5, end_fraction=0.7)
        model = PPO(
            "MultiInputPolicy",
            envs,
            learning_rate=2e-4,  # lr_schedule
            n_steps=1024,
            batch_size=128,
            n_epochs=8,
            gamma=0.99,
            gae_lambda=0.98,
            clip_range=0.15,
            ent_coef=0.03,
            vf_coef=0.6,
            verbose=1,
            tensorboard_log=tsboard_log_path,
            # policy_kwargs=policy_kwargs,
            device="cpu",
        )

    return model
