import copy
import os

import numpy as np

from xuance.environment import make_envs
from xuance.torch.agents import REGISTRY_Agents
from xuance.torch.runners import RunnerBase


class RunnerMARL(RunnerBase):
    def __init__(self, config):
        super().__init__(config)
        self.agents = REGISTRY_Agents[config.agent](config, self.envs)
        self.config = config

        if self.agents.distributed_training:
            self.rank = int(os.environ["RANK"])

    def run(self, filter_prefix=None):
        if filter_prefix is None:
            filter_prefix = []
        if self.config.test_mode:

            def env_fn():
                config_test = copy.deepcopy(self.config)
                config_test.parallels = 1
                config_test.render = True
                return make_envs(config_test)

            self.agents.render = True
            self.agents.load_model(
                self.agents.model_dir_load, filter_prefix=filter_prefix
            )  # only determine the folder of model checkpoint
            scores = self.agents.test(env_fn, self.config.test_episode)
            print(f"Mean Score: {np.mean(scores)}, Std: {np.std(scores)}")
            print("Finish testing.")
        else:
            n_train_steps = self.config.running_steps // self.n_envs
            self.agents.train(n_train_steps)
            print("Finish training.")
            self.agents.save_model("final_train_model.pth")

        self.agents.finish()
        self.envs.close()

    def benchmark(self):
        def env_fn():
            config_test = copy.deepcopy(self.config)
            config_test.parallels = 1  # config_test.test_episode
            return make_envs(config_test)

        train_steps = self.config.running_steps // self.n_envs
        eval_interval = self.config.eval_interval // self.n_envs
        test_episode = self.config.test_episode
        num_epoch = int(train_steps / eval_interval)  # total 200 epochs

        test_scores = self.agents.test(env_fn, test_episode) if self.rank == 0 else 0.0  # render will create an window
        best_scores_info = {"mean": np.mean(test_scores), "std": np.std(test_scores), "step": self.agents.current_step}
        for i_epoch in range(num_epoch):
            print(f"Epoch: {i_epoch}/{num_epoch}")
            # self.agents.save_model(model_name="test_model.pth")
            self.agents.train(eval_interval)
            if self.rank == 0:
                test_scores = self.agents.test(env_fn, test_episode)

                if np.mean(test_scores) > best_scores_info["mean"]:
                    best_scores_info = {
                        "mean": np.mean(test_scores),
                        "std": np.std(test_scores),
                        "step": self.agents.current_step,
                    }
                    # save best model
                    print(
                        "New Best Model: mean={:.2f}, std={:.2f}, step={}".format(
                            best_scores_info["mean"], best_scores_info["std"], best_scores_info["step"]
                        )
                    )
                    self.agents.save_model(model_name="best_model.pth")

        # end benchmarking
        print("Best Model Score: {:.2f}, std={:.2f}".format(best_scores_info["mean"], best_scores_info["std"]))
        self.agents.finish()
        self.envs.close()
