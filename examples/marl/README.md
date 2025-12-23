# 🚀 Multi-Agent Collaborative Navigation

## Overview

This project is a reinforcement learning codebase designed for the **Multi-Agent Collaborative Search (MACS)** task. At its core, this benchmark features a challenging multi-agent collaborative mission: in a dynamic flood disaster scenario, a team of agents must **cooperatively collect supplies** while **avoiding moving hazards**. This task is designed to evaluate the decentralized decision-making and collaborative capabilities of agents under complex constraints such as partial observability, mandatory cooperation, and limited resources.

## Installation

### 1. Set up TongSIM
   Follow the official instructions XXX to install and configure the TongSIM simulator.
   After installation, **verify** that the `demo_rl` example runs successfully.

### 2. Install Conda and `uv`

Ensure that [Miniconda](https://docs.conda.io/en/latest/miniconda.html) and [`uv`](https://github.com/astral-sh/uv) are installed on your system. `uv` is a high-performance Python package manager.

### 3. Create Environment and Install MPI

This project relies on MPI, which we manage using Conda.

```bash
# Create and activate a Conda environment named tongsim_env
conda create -n tongsim_env python=3.12 -y
conda activate tongsim_env

# Install mpi4py in the environment
conda install -c conda-forge mpi4py -y
```

### 4. Install Project Dependencies

With the `tongsim_env` environment activated, use `uv` to install all required Python packages.

```bash
# uv will automatically use the Python interpreter from the active Conda environment
# Install all dependencies for development and the multi-agent task
uv sync --group dev --group multi_agent
```

## Usage

### Training a New Model

```bash
# Train the MAPPO algorithm using the configuration from mappo.yaml
uv run examples/marl/example/train.py  --config examples/marl/example/config/mappo.yaml
```

You can train other algorithms by changing the `--config` parameter to point to a different `.yaml` file (e.g., `ippo.yaml`).

- Trained models are saved by default in the `models/` directory.
- Logs are stored in the `logs/` directory.

### Evaluating a Pre-trained Model

```bash
# Load and test the latest MAPPO model
uv run examples/marl/example/train.py  --config examples/marl/example/config/mappo.yaml --test
```

### Monitoring Training Progress

You can use TensorBoard to visualize training curves and metrics.

```bash
tensorboard --logdir logs
```

## Notes

- Before executing the command, make sure the Unreal Editor already has the `L_MACS` main level open.
