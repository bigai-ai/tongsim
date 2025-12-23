# 🚀 Single Agent Navigation

## Overview

This repository is a reinforcement learning codebase for evaluating **exploration** and **navigation** capabilities. The benchmark centers on a challenging task: **cleaning all paper balls** scattered across a multi-room indoor environment with obstacles in each room. The agent must collect all targets under randomized initial positions and target distributions.

## Installation

1. **Set up TongSIM**

   Follow the [TongSIM/Quickstart](../../docs/quickstart/overview.md) to install and configure the TongSIM simulator.
   After installation, **verify** that the `demo_rl` example runs successfully.

2. **Install `uv` (package & environment manager)**

   We recommend using **uv** to manage the environment and dependencies.
   See the docs: [https://hellowac.github.io/uv-zh-cn/](https://hellowac.github.io/uv-zh-cn/)

3. **Install project dependencies**

   Change the working directory to **root directory of the project**, then run:
   ```bash
   # Install the RL task-specific group
   uv sync --group rl_nav
   ```
## Usage

Make sure your current working directory is **root directory of the project**.

**Baseline Inference**

```bash
uv run python examples/rl_nav/run.py test --model_name="search_ppo_10000000_steps.zip"
```

**Human Evaluation (Manual Control)**

```bash
uv run python examples/rl_nav/run.py manual
```

**Train a Model**

```bash
uv run python examples/rl_nav/run.py train
```

---

**Notes**

* If you are on Windows, forward slashes work in most Python tooling; otherwise, replace with backslashes as needed.
* Ensure TongSIM services are running and reachable before launching any script.
