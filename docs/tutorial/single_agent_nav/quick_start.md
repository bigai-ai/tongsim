# Quick Start

## Installation

 **Prerequisites**

1. Refer to [Environment Setup](../../quickstart/environment.md) and [First Simulation](../../quickstart/first_simulation.md) for installing and configuring the TongSIM simulation environment. After confirming you can successfully run `examples/quickstart_demo.py`, follow the steps below to install and configure the single-agent navigation task.
2. This project uses **uv** as the project management tool. It is recommended to use **uv** to install and manage dependencies. Please refer to the [uv website](https://docs.astral.sh/uv/) for installation.


**Install Dependencies**

The required libraries and versions are as follows:

```toml
[dependency-groups]
rl_nav = [
    "gymnasium>=1.2.1",
    "pygame>=2.6.1",
    "stable-baselines3[extra]>=2.7.0",
    "tensorboard>=2.20.0",
    "pillow>=10.0.0",
    "opencv-python>=4.10.0.84",
]
```

The related configuration is recorded under the `rl_nav` group in `./pyproject.toml`. Switch your working directory to **root directory of the project**, then run:

```bash
uv sync --group rl_nav
```

## Verification

Project layout:

```bash
./examples/rl_nav
│  collect_task.py # task env
│  run.py # tain/evaluation/manual
│
├─common # common module
│
├─model # baseline model
│
└─occupy_grid # occupy grid png data
```

Start TongSIM and open an empty scene map. Then run:

```bash
uv run python ./examples/rl_nav/run.py test --model_name="search_ppo_10000000_steps.zip"
```

TongSIM successfully loads the task scenario, and the simplified occupancy grid map is displayed correctly in the pygame window. The running result is shown in the figure below:

![Task Launched Successfully](run.png)
***Figure 1**. Task Launched Successfully*
