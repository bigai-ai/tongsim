## Getting Started

This project utilizes a hybrid setup combining **Conda** and **uv** to ensure a stable and reproducible environment, especially for dependencies with complex system-level requirements.

- **Conda** is used to bootstrap a base environment with a specific Python version and to manage system-level dependencies like MPI (via `mpi4py`).
- **uv**, a high-performance Python package manager, is used to create an isolated project-local virtual environment (`.venv`) and manage all Python packages listed in `pyproject.toml`.

### Prerequisites

Before you begin, ensure you have the following installed:

1.  **Conda**: [Miniconda](https://docs.conda.io/en/latest/miniconda.html) (recommended) or Anaconda.
2.  **uv**: If you don't have `uv` installed, run the appropriate command for your OS:
    - **macOS / Linux**:
      ```bash
      curl -LsSf https://astral.sh/uv/install.sh | sh
      ```
    - **Windows (PowerShell)**:
      ```powershell
      irm https://astral.sh/uv/install.ps1 | iex
      ```

### Installation Steps

Follow these steps carefully in your terminal to set up the development environment.

#### Step 1: Create the Conda Base Environment

This "bootstrap" environment provides the core Python interpreter and MPI support.

```bash
# 1. Create a Conda environment named "tongsim_env" with Python 3.12.
#    The "-y" flag automatically confirms the installation.
conda create -n tongsim_env python=3.12 -y

# 2. Activate the new environment.
conda activate tongsim_env

# 3. Install mpi4py.
#    This correctly installs both the Python package and its underlying MPI libraries.
conda install mpi4py -y
```

> **Note**: Your terminal prompt should now be prefixed with `(tongsim_env)`.

#### Step 2: Create and Sync the Project Virtual Environment

With the Conda environment active, we'll now use `uv` to build the final, isolated project environment inside the `.venv` directory.

Make sure you are in the project's root directory (where `pyproject.toml` is located).

```bash
# `uv` will automatically detect the Python from the active Conda environment.
# It will create a new virtual environment at `./.venv` and install all
# dependencies from the "dev" and "multi_agent" groups into it.
uv sync --group dev --group multi_agent
```

After this command completes, all required Python packages will be installed in the local `.venv` folder.

#### Step 3: Deactivate the Conda Base Environment

The bootstrap environment has served its purpose. You can now deactivate it.

```bash
conda deactivate
```

The `(tongsim_env)` prefix will disappear from your terminal prompt. If you are returned to the `(base)` environment, you can run `conda deactivate` again to exit. The setup is now complete.

## Daily Workflow

Whenever you want to work on this project, you only need to perform one step: **activate the local virtual environment**.

- **Windows (Command Prompt):**
  ```cmd
  .\.venv\Scripts\activate.bat
  ```

- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```

- **macOS / Linux (Bash/Zsh):**
  ```bash
  source .venv/bin/activate
  ```

### Generate Protobuf Files

After activating the environment, you need to generate the Python code from the Protobuf definitions:

```bash
uv run python scripts/generate_pb2.py
```


### Verification

To verify your installation, you can run a pre-trained model. Before executing the command, make sure the Unreal Editor already has the `L_MACS` main level open:

```bash
uv run examples/marl/example/train.py  --config examples/marl/example/config/mappo.yaml --test --method mappo
```
