# 🚀 Multi-Agent Collaborative Navigation (MACS)

## Overview

This project is a reinforcement learning codebase featuring a lightweight adaptation of the [XuanCe](https://github.com/agi-brain/xuance) framework, specifically configured for the **Multi-Agent Collaborative Search (MACS)** task within the TongSim simulator.

In a dynamic flood disaster scenario, a team of agents must **cooperatively collect supplies** while **avoiding moving hazards**. This task evaluates decentralized decision-making and collaborative capabilities under constraints such as partial observability, mandatory cooperation.

### Key Challenges
- **Local Perception & Dynamic Adaptation**: Agents operate with only local sensor data and no global view.
- **Cooperative Games**: Supply collection is enforced by requiring the cooperation of multiple agents.
- **Resource Management**: Minimizing energy expenditure and avoiding hazards.

## Installation

This project utilizes a hybrid setup combining **Conda** (for system-level dependencies like MPI) and **uv** (for high-performance Python package management).

### 1. Set up TongSIM
Follow the official instructions to install and configure the TongSIM simulator. Verify that the `quickstart_demo.py` example runs successfully.

### 2. Create the Conda Base Environment
This environment provides the core Python interpreter and MPI support.

```bash
# 1. Create a Conda environment named "tongsim_env" with Python 3.12.
conda create -n tongsim_env python=3.12 -y

# 2. Activate the new environment.
conda activate tongsim_env

# 3. Install mpi4py.
conda install mpi4py -y
```

### 3. Install Project Dependencies
With the Conda environment active, use `uv` to install all required Python packages into a local virtual environment.

```bash
# Run this from the project root.
# uv will create a .venv directory and install dependencies.
uv sync --group dev --group multi_agent
```

### 4. Generate Protobuf Files
After installation, you must generate the Python code from the Protobuf definitions:

```bash
uv run python scripts/generate_pb2.py
```

## Usage

### Training a New Model
Before executing the command, make sure the Unreal Editor already has the **`L_MACS`** main level open.

```bash
# Train the MAPPO algorithm using the configuration from mappo.yaml
uv run examples/marl/example/train.py --config examples/marl/example/config/mappo.yaml --method mappo
```

You can train other algorithms by changing the `--config` parameter (e.g., `ippo.yaml`).

### Evaluating a Pre-trained Model
```bash
# Load and test the latest MAPPO model
uv run examples/marl/example/train.py --config examples/marl/example/config/mappo.yaml --test --method mappo
```

### Monitoring Training Progress
You can use TensorBoard to visualize training curves and metrics.

```bash
tensorboard --logdir logs
```
