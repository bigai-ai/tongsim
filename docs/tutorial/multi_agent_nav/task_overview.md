# Multi-Agent Navigation with MACS Environment

[![Python Version](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![PyTorch Version](https://img.shields.io/badge/PyTorch-2.8+-ee4c2c.svg)](https://pytorch.org/)
<!-- [![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE.txt) -->

This project is a reinforcement learning codebase featuring a lightweight adaptation of the powerful [XuanCe](https://github.com/agi-brain/xuance) framework, specifically configured for the Multi-Agent Cooperative Search (MACS) environment within the `tongsim` simulator. It aims to provide researchers and developers with an out-of-the-box solution for environment setup, model training, and performance evaluation.

![MACS Environment Overview](environment.png)
*Figure: Multi-Agent Cooperative Search (MACS) environment visualization*


## The MACS Benchmark

The **Multi-Agent Cooperative Search (MACS)** benchmark is a multi-agent cooperative task designed to evaluate agent collaboration capabilities in complex, dynamic environments. Built on the TongSim platform and Unreal Engine (UE), this benchmark provides a testing scenario for multi-agent reinforcement learning algorithms.

### Task Overview

In a dynamic flood disaster scenario, a multi-agent team must cooperatively gather valuable supplies while evading mobile hazards. This environment serves as a high-challenge testbed for evaluating decentralized decision-making and emergent behaviors under the constraints of partial observability, enforced cooperation, and multiple resource limits.

**Key Challenges:**

- **Local Perception & Dynamic Adaptation**: Operating with only local sensor data and no global view, agents must navigate and make real-time decisions within an unknown environment populated by mobile hazards.
- **Cooperative Games & Competitive Dynamics**: Supply collection is enforced by requiring the cooperation of n_coop agents. This, combined with finite resources and the tunable local_ratio parameter, introduces a complex game of cooperation and competition between individual and collective interests.
- **Resource Management**: While executing the collection task, agents must meticulously manage their operational costs. This is manifested in two core aspects: first, minimizing energy expenditure from movement (governed by thrust_penalty); and second, avoiding severe performance penalties (defined by hazard_reward) by proactively evading mobile hazards.

### Environment Specifications

| Parameter          | Description                                  | Default Value |
| ------------------ | -------------------------------------------- | ------------- |
| `n_rescuers`       | Number of rescue agents                      | 5             |
| `n_supplies`       | Number of valuable supply items              | 10            |
| `n_hazards`        | Number of hazard items                       | 5            |
| `n_coop`           | Agents required for successful cooperation   | 2             |
| `n_sensors`        | Number of sensors per agent                  | 30            |
| `sensor_range`     | Maximum sensing range                        | 500.0         |
| `supply_reward`    | Reward for successfully collecting supplies  | 10.0          |
| `hazard_reward`    | Penalty for encountering hazards             | -1.0          |
| `encounter_reward` | Small reward for touching a supply without a capture.  | 0.01            |
| `thrust_penalty`   | Per-step movement cost multiplier, simulating energy use  | -0.01        |
| `max_cycles`       | Maximum steps per episode                    | 500           |
| `local_ratio`      | Ratio of local rewards to global rewards     | 0.9           |

### Action and Observation Space

**Action Space:**

Each agent's action space is continuous and 2-dimensional, represented as `Box(low=-1.0, high=1.0, shape=(2,))`. The two action values control:

- **Horizontal movement** (x-axis): Value ranges from -1.0 to 1.0
- **Vertical movement** (y-axis): Value ranges from -1.0 to 1.0

These normalized action values are scaled by an action multiplier to determine the actual displacement in the environment.

**Observation Space:**

The observation for each agent is constructed using a sensor-based perception system. Each agent is equipped with `n_sensors` (default: 30) radial sensors distributed uniformly around the agent in a circular pattern, with a maximum sensing range of `sensor_range` (default: 500.0).

For each sensor ray, the observation includes:

- **Agent detection** (3 features): Normalized distance, orientation_x, orientation_y
- **Supply detection** (2 features): Normalized distance, velocity projection along ray direction
- **Hazard detection** (2 features): Normalized distance, velocity projection along ray direction
- **Wall detection** (1 feature): Normalized distance to environment boundary
- **Obstacle detection** (1 feature): Normalized distance to static obstacles

Additionally, each observation includes 2 binary flags indicating whether the agent:

- Recently encountered a supply item (last dimension - 2)
- Recently encountered a hazard (last dimension - 1)

The total observation dimension is: `(n_sensors * 9) + 2`, where 9 is the sum of all feature dimensions per sensor ray.

For implementation details, please refer to [`macs_dummy.py`](https://github.com/bigai-ai/tongsim/blob/main/examples/marl/xuance/environment/multi_agent_env/macs_dummy.py).

Launch TongSim, and open the `L_MACS` scene map. You can create the MACS environment using the following code.

```python
def make_env(env_seed):
    """
    Factory function to create a MACS environment instance.

    Args:
        env_seed: Random seed for environment initialization.

    Returns:
        Initialized MACS environment instance.
    """
    env_instance = MACS(
        env_seed=env_seed,
        num_arenas=4,
        max_cycles=500,
        n_rescuers=5,
        n_supplies=10,
        n_hazards=5
    )
    return env_instance
```

You can drive the agents to perform random movements in the environment using the following code. For details, please refer to [`dummy_UE.py`](https://github.com/bigai-ai/tongsim/blob/main/examples/marl/xuance/environment/vector_envs/dummy/dummy_UE.py).

```python
env_fns = [make_env]
envs = TongSimVecMultiAgentEnv(env_fns=env_fns, env_seed=1)

print("[INFO] Environment created successfully!")
print(f"  - Number of parallel environments (num_envs): {envs.num_envs}")
print(f"  - Number of agents (num_agents): {envs.num_agents}")
print(f"  - State space (state_space): {envs.state_space}")

# Initial reset
observations, infos = envs.reset()

# Training loop demonstration
for step in range(300000):
    if step % 1000 == 0:
        print(f"\n--- Training Step {step + 1} ---")

    # Sample random actions for all environments
    actions = []
    for i in range(envs.num_envs):
        arena_actions = {
            agent: envs.action_space[agent].sample()
            for agent in envs.agents
        }
        actions.append(arena_actions)

    # Execute environment step
    next_observations, rewards, terminateds, truncateds, infos = envs.step(actions)
```

## Acknowledgements

This project is built upon the fantastic work of the [XuanCe](https://github.com/agi-brain/xuance) team.
