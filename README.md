# TongSIM

A high-fidelity platform for multimodal embodied agent training (Unreal Engine + Python SDK)

![TongSIM Preview](docs/assets/tongsim-main.jpg)

**Links**

- Homepage: https://tongsim-platform.github.io/tongsim
- Documentation: https://bigai-ai.github.io/tongsim/
- Asset Library (Hugging Face): https://huggingface.co/datasets/bigai/TongSIM-Asset

TongSIM is a high-fidelity, general-purpose platform for embodied agent training and testing built on Unreal Engine, supporting tasks from low-level single-agent skills (e.g., navigation) to high-level scenarios such as multi-agent social simulation and human–AI collaboration. TongSIM constructs 100+ diverse multi-room indoor scenarios alongside an open-ended, interaction-rich outdoor simulated town, and incorporates thousands of interactive 3D object models spanning 500+ categories.

On top of the environment, TongSIM provides a comprehensive evaluation system and a suite of benchmarks covering major agent capabilities: perception, cognition, decision-making, learning, execution, and social collaboration. The platform also offers high-fidelity and customizable scenes, rich annotations, and parallel training to accelerate research and development of general embodied intelligence.

This repository contains:

- Unreal Engine project (`unreal/`)
- Python SDK and examples (`src/`, `examples/`)
- Documentation site sources (`docs/`, `mkdocs.yml`)

## Highlights

- High-fidelity indoor + outdoor worlds: 100+ multi-room indoor scenes and an open-ended outdoor town
- Large-scale interactive assets: thousands of objects spanning 500+ categories
- Benchmarks and evaluation: perception, cognition, decision-making, learning, execution, and social collaboration
- Multimodal perception: built-in vision and audio; extensible to other modalities
- Physics-consistent simulation with causal world dynamics and rich annotations
- Parallel simulation for scalable training
- Easy integration: Python SDK over gRPC with practical examples
- Extensible, plugin-oriented architecture

## Requirements

- OS: Windows 10/11 or Ubuntu 22.04
- Unreal Engine: 5.6 (install via Epic Games Launcher)
- Python: 3.12+

## Getting Started

### Install UE 5.6

1. Install Unreal Engine 5.6 via Epic Games Launcher (Editor build matching your platform).
2. Install and enable Git LFS:
   ```powershell
   winget install Git.Git -s winget
   git lfs install
   ```

### Run the UE Project

1. Clone the repo and pull LFS assets:
   ```powershell
   git clone https://github.com/bigai-ai/tongsim
   cd tongsim
   git lfs pull
   ```
2. Generate project files (either):
   - File Explorer: right-click `unreal/TongSIM_Lite.uproject` -> "Generate Visual Studio project files"
   - Or open the `.uproject` to let UE generate and compile modules
3. Open `unreal/TongSIM_Lite.sln` in Visual Studio and select:
   - Configuration: Development Editor
   - Platform: Win64
   Then Build (first build compiles TongSIM_* modules and plugins).
4. Double-click `unreal/TongSIM_Lite.uproject` to open UE 5.6 and ensure plugins (TongSIMCore, TongSIMGrpc, Puerts, etc.) are enabled.
5. If Windows Firewall prompts, allow UE Editor network access (gRPC defaults to `127.0.0.1:5726`).

### Python Installation

Use either `uv` (recommended) or plain `pip`.

#### Option A: uv (recommended)

1. Install [`uv`](https://docs.astral.sh/uv/)
2. Create and sync a virtual environment (defaults to installing `dev` and `docs` groups as configured):
   ```powershell
   uv venv
   uv sync
   ```

3. Run examples (start the UE project first; gRPC at `127.0.0.1:5726`):
   ```powershell
   uv run examples/quickstart_demo.py
   uv run examples/voxel.py
   ```

#### Option B: pip

1. Install the package in editable mode:
   ```powershell
   pip install -e .
   ```
2. Optional: dev/docs tooling (for contributing or building docs):
   ```powershell
   pip install pre-commit black ruff mkdocs mkdocs-material mkdocstrings-python mkdocs-static-i18n mkdocs-redirects pytest pytest-asyncio
   pre-commit install
   ```
3. Run examples (start the UE project first):
   ```powershell
   python examples\quickstart_demo.py
   python examples\voxel.py
   ```

## Quick Check

Verify Python SDK connectivity to a local UE instance (default gRPC `5726`):

```powershell
uv run python - <<'PY'
from tongsim import TongSim
sim = TongSim("127.0.0.1:5726")
print("connected", sim.context.uuid)
sim.close()
PY
```

If a UUID prints with "connected", the connection is working.

## Documentation

- Sources in `docs/`, configured by `mkdocs.yml`
- Build/serve locally:
  ```powershell
  uv run mkdocs build
  uv run mkdocs serve
  ```
- See: `docs/quickstart/*`, `docs/guides/*`, `docs/architecture/*`, `docs/api/*`

## Project Layout

```
├─ src/tongsim/                  # Python SDK core
├─ examples/                     # Examples (RL, voxel, etc.)
├─ docs/                         # Documentation sources (MkDocs)
├─ unreal/                       # Unreal project (TongSIM_Lite.uproject)
├─ scripts/                      # Utility scripts
├─ pyproject.toml                # Python project configuration (uv-compatible)
└─ uv.lock                       # Dependency lockfile
```

## Support

- Report issues with system info, UE/SDK versions
- Feature requests are welcome via Issues; PRs are appreciated

## Contributing

See `CONTRIBUTING.md`.

## Security

See `SECURITY.md`.

## License

See `LICENSE`.

## Citation

If you use TongSIM in your research, please cite:

```bibtex
@article{sun2025tongsim,
  title={TongSIM: A General Platform for Simulating Intelligent Machines},
  author={Sun, Zhe and Wu, Kunlun and ... Zhang, Zhenliang},
  journal={Technical Report},
  year={2025},
  institution={State Key Laboratory of General Artificial Intelligence, BIGAI}
}
```

Happy simulating with TongSIM!
