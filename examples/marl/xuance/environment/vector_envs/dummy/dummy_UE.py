"""
TongSim Vectorized Multi-Agent Environment Wrapper for XuanCe Framework.

This module provides a vectorized environment wrapper that integrates the MACS
multi-agent simulation with the XuanCe reinforcement learning framework.
"""

import gymnasium as gym
import numpy as np

from xuance.common import space2shape
from xuance.environment.multi_agent_env.macs_dummy import MACS
from xuance.environment.vector_envs.vector_env import AlreadySteppingError, NotSteppingError, VecEnv


class TongSimVecMultiAgentEnv(VecEnv):
    """
    Vectorized multi-agent environment wrapper for MACS simulation.

    This wrapper adapts the MACS environment to be compatible with XuanCe's
    vectorized environment interface. It manages parallel arenas internally
    through the MACS environment.

    Args:
        env_fns: List containing a single environment constructor function.
                 Only one constructor is supported as MACS manages parallelization internally.
        env_seed: Random seed for environment initialization.

    Raises:
        ValueError: If more than one environment constructor is provided.
        RuntimeError: If operations are attempted on a closed environment.
    """

    def __init__(self, env_fns, env_seed):
        self.waiting = False
        self.closed = False

        # Validate that only one environment constructor is provided
        if len(env_fns) != 1:
            raise ValueError(
                "TongSimVecMultiAgentEnv only supports a single environment constructor "
                "in env_fns, as MACS environment manages parallel arenas internally."
            )

        # Initialize the MACS environment
        self.env = env_fns[0](env_seed=env_seed)

        # Extract environment configuration
        num_envs = self.env.num_arenas
        observation_space = self.env.observation_space
        action_space = self.env.action_space

        VecEnv.__init__(self, num_envs, observation_space, action_space)

        # Agent configuration
        self.agents = self.env.agents
        self.num_agents = self.env.n_rescuers
        self.agent_ids = [f"agent_{i}" for i in range(self.num_agents)]

        # Construct global state space
        single_obs_dim = space2shape(observation_space)
        if isinstance(single_obs_dim, dict):
            single_obs_dim = single_obs_dim["pursuer_0"][0]
        state_dim = self.num_agents * single_obs_dim
        self.state_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(state_dim,), dtype=np.float32)

        # Initialize buffers for parallel environments
        self.buf_obs = [{} for _ in range(self.num_envs)]
        self.buf_state = [np.zeros(self.state_space.shape, dtype=np.float32) for _ in range(self.num_envs)]
        self.buf_avail_actions = [{} for _ in range(self.num_envs)]
        self.buf_info = [{} for _ in range(self.num_envs)]
        self.action_dim = 2

        self.actions = None
        self.max_episode_steps = self.env.max_cycles

    def _get_state(self, obs_dict: dict) -> np.ndarray:
        """
        Concatenate individual agent observations into a global state vector.

        Args:
            obs_dict: Dictionary mapping agent IDs to their observations.

        Returns:
            Concatenated state vector for all agents.
        """
        state = [obs_dict[agent] for agent in self.agents]
        return np.concatenate(state, axis=0)

    def _get_avail_actions(self) -> dict:
        """
        Get available actions for all agents.

        Returns:
            Dictionary mapping agent IDs to their available action masks.
        """
        return {agent: np.ones(shape=(self.action_dim,), dtype=np.int8) for agent in self.agents}

    def reset(self):
        """
        Reset all parallel environments to initial state.

        Returns:
            observations: List of observation dictionaries for each environment.
            infos: List of info dictionaries for each environment.

        Raises:
            RuntimeError: If environment is already closed.
        """
        if self.closed:
            raise RuntimeError("Cannot reset a closed VecEnv.")

        # Reset all environments
        batch_obs, batch_info = self.env.reset()

        # Initialize buffers with reset data
        for e in range(self.num_envs):
            self.buf_obs[e] = batch_obs[e]
            self.buf_info[e] = batch_info[e]
            self.buf_state[e] = self._get_state(batch_obs[e])
            self.buf_avail_actions[e] = self._get_avail_actions()
            self.buf_info[e]["state"] = self.buf_state[e]
            self.buf_info[e]["avail_actions"] = self.buf_avail_actions[e]
            self.buf_info[e]["episode_step"] = 0
            self.buf_info[e]["tem_episode_score"] = dict.fromkeys(self.agents, 0.0)

        return self.buf_obs.copy(), self.buf_info.copy()

    def step_async(self, actions):
        """
        Initiate asynchronous step with given actions.

        Args:
            actions: List of action dictionaries for each environment.

        Raises:
            AlreadySteppingError: If a step is already in progress.
        """
        if self.waiting:
            raise AlreadySteppingError
        self.actions = actions
        self.waiting = True

    def step_wait(self):
        """
        Wait for asynchronous step to complete and return results.

        Returns:
            observations: List of observation dictionaries for each environment.
            rewards: List of reward dictionaries for each environment.
            terminateds: List of termination dictionaries for each environment.
            truncateds: List of truncation flags for each environment.
            infos: List of info dictionaries for each environment.

        Raises:
            NotSteppingError: If no step is in progress.
            RuntimeError: If environment is closed.
        """
        if not self.waiting:
            raise NotSteppingError
        if self.closed:
            raise RuntimeError("Cannot step in a closed VecEnv.")

        # Execute step in all environments
        obs, rews, terminateds, truncateds, infos = self.env.step(self.actions)

        # Convert truncated dictionaries to boolean flags
        truncateds_list = [all(t.values()) for t in truncateds]

        # Update buffers with step results
        for e in range(self.num_envs):
            self.buf_obs[e] = obs[e]
            self.buf_info[e].update(infos[e])
            self.buf_state[e] = self._get_state(obs[e])
            self.buf_avail_actions[e] = self._get_avail_actions()
            self.buf_info[e]["state"] = self.buf_state[e]
            self.buf_info[e]["avail_actions"] = self.buf_avail_actions[e]
            self.buf_info[e]["episode_step"] += 1

            # Accumulate rewards
            for agent in self.agents:
                self.buf_info[e]["tem_episode_score"][agent] += rews[e][agent]
            self.buf_info[e]["episode_score"] = self.buf_info[e]["tem_episode_score"].copy()

            # Handle episode termination or truncation
            if all(terminateds[e].values()) or truncateds_list[e]:
                obs_reset, info_reset = self.env.reset_one_env(e)

                self.buf_info[e]["reset_obs"] = obs_reset
                self.buf_info[e]["reset_state"] = self._get_state(obs_reset)
                self.buf_info[e]["reset_avail_actions"] = self._get_avail_actions()
                self.buf_info[e]["episode_step"] = 0
                self.buf_info[e]["tem_episode_score"] = dict.fromkeys(self.agents, 0.0)

        self.waiting = False
        return (self.buf_obs.copy(), rews, terminateds, truncateds_list, self.buf_info.copy())

    def close_extras(self):
        """Clean up any additional resources. Currently not implemented."""
        pass

    def render(self, mode=None):
        """
        Render the environment. Currently not implemented.

        Args:
            mode: Rendering mode (not used).
        """
        pass

    def get_agent_mask(self) -> np.ndarray:
        """
        Get mask indicating which agents are active in each environment.

        Returns:
            Boolean mask of shape (num_envs, num_agents) with all True values.
        """
        return np.ones((self.num_envs, self.num_agents), dtype=np.bool_)


def make_env(env_seed):
    """
    Factory function to create a MACS environment instance.

    Args:
        env_seed: Random seed for environment initialization.

    Returns:
        Initialized MACS environment instance.
    """
    env_instance = MACS(env_seed=env_seed, num_arenas=9, max_cycles=500, n_rescuers=5, n_supplies=10, n_hazards=10)
    return env_instance


def main():
    """
    Demonstration of the TongSimVecMultiAgentEnv wrapper.

    Creates a vectorized environment and runs a training loop with
    random actions to verify functionality.
    """
    print("[INFO] Creating XuanCe-compatible vectorized environment...")

    try:
        # Initialize vectorized environment
        env_fns = [make_env]
        envs = TongSimVecMultiAgentEnv(env_fns=env_fns, env_seed=1)

        print("[INFO] Environment created successfully!")
        print(f"  - Number of parallel environments (num_envs): {envs.num_envs}")
        print(f"  - Number of agents (num_agents): {envs.num_agents}")
        print(f"  - State space (state_space): {envs.state_space}")

        # Initial reset
        observations, infos = envs.reset()

        # Training loop demonstrationd
        for step in range(300):
            if step % 1000 == 0:
                print(f"\n--- Training Step {step + 1} ---")

            # Sample random actions for all environments
            actions = []
            for _i in range(envs.num_envs):
                arena_actions = {agent: envs.action_space[agent].sample() for agent in envs.agents}
                actions.append(arena_actions)

            # Execute environment step
            next_observations, rewards, terminateds, truncateds, infos = envs.step(actions)

    except Exception as e:
        import traceback

        print(f"[ERROR] Fatal exception occurred during demonstration: {e}")
        traceback.print_exc()
    finally:
        if "envs" in locals():
            envs.close()
        print("[INFO] Demonstration completed.")


if __name__ == "__main__":
    main()
