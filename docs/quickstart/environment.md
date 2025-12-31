# :material-hammer-wrench: Environment Setup

This guide helps you set up **TongSIM Lite** locally and verify that the **Unreal server** and the **Python SDK** can communicate over **gRPC**.

!!! tip ":material-check-circle: What you’ll achieve"
    - Open and run the Unreal project: `unreal/TongSim_Lite.uproject`
    - Install the Python SDK dependencies (via `uv` or `pip`)
    - Connect from Python to the UE gRPC server (`127.0.0.1:5726`)

---

## :material-clipboard-check: Prerequisites

=== ":material-microsoft-windows: Windows 10/11 (recommended)"

    - Unreal Engine `5.6` (Epic Games Launcher)
    - Visual Studio `2022` with workloads:
        - **Desktop development with C++**
        - **Game development with C++**
    - Python `>= 3.12`
    - Git
    - (Optional) NVIDIA driver / CUDA (only if your workflow requires it)

=== ":material-linux: Ubuntu 22.04"

    - Unreal Engine `5.6` (Linux setup varies; follow Epic’s official guidance)
    - Python `>= 3.12`
    - Git

!!! warning ":material-alert: Path naming"
    Keep your project path **free of spaces, non-ASCII characters, and overly long directory names** to avoid Unreal build and asset issues.

---

## :material-download: Get the repository

```powershell
git clone https://github.com/bigai-ai/tongsim
cd tongsim
```

## :material-package-down: Download Unreal Engine assets (`unreal/Content`)

`unreal/Content` is intentionally not stored in Git. Download it from:

- https://huggingface.co/datasets/bigai/tongsim-unreal-content

```powershell
python -m pip install -U huggingface_hub
python scripts/fetch_unreal_content.py
```

---

## :material-archive: Install TongSimGrpc gRPC dependencies (first-time)

The `TongSimGrpc` plugin depends on prebuilt gRPC binaries and tools. To keep the Git repository lightweight, these large files are distributed as a GitHub **Release asset** (download once after cloning).

- `TongSimGrpc_deps.zip`: https://github.com/bigai-ai/tongsim/releases/download/tongsimgrpc-deps-v1.0/TongSimGrpc_deps.zip
- `TongSimGrpc_deps.zip.sha256`: https://github.com/bigai-ai/tongsim/releases/download/tongsimgrpc-deps-v1.0/TongSimGrpc_deps.zip.sha256

=== ":material-microsoft-windows: Windows (PowerShell)"

    ```powershell
    $base = "https://github.com/bigai-ai/tongsim/releases/download/tongsimgrpc-deps-v1.0"
    Invoke-WebRequest "$base/TongSimGrpc_deps.zip" -OutFile TongSimGrpc_deps.zip
    Invoke-WebRequest "$base/TongSimGrpc_deps.zip.sha256" -OutFile TongSimGrpc_deps.zip.sha256

    # (Optional) Verify checksum
    Get-FileHash .\TongSimGrpc_deps.zip -Algorithm SHA256
    Get-Content .\TongSimGrpc_deps.zip.sha256

    # Extract to repo root
    Expand-Archive .\TongSimGrpc_deps.zip -DestinationPath . -Force
    ```

=== ":material-linux: Linux (Bash)"

    ```bash
    base="https://github.com/bigai-ai/tongsim/releases/download/tongsimgrpc-deps-v1.0"
    curl -L -o TongSimGrpc_deps.zip "$base/TongSimGrpc_deps.zip"
    curl -L -o TongSimGrpc_deps.zip.sha256 "$base/TongSimGrpc_deps.zip.sha256"

    # (Optional) Verify checksum
    sha256sum -c TongSimGrpc_deps.zip.sha256

    # Extract to repo root
    unzip -o TongSimGrpc_deps.zip
    ```

After extraction, ensure these folders exist:

- `unreal/Plugins/TongSimGrpc/DynamicLibraries`
- `unreal/Plugins/TongSimGrpc/GrpcLibraries`
- `unreal/Plugins/TongSimGrpc/GrpcPrograms`

!!! note ":material-information-outline: Third-party binaries"
    This bundle includes third-party components (e.g., gRPC/Protobuf). Their respective licenses apply.

---

## :material-monitor: Build & run the Unreal project

1. Open `unreal/TongSim_Lite.uproject` in **Unreal Engine 5.6**.
2. If prompted, let Unreal **generate project files** and **compile modules**.
3. (Windows, recommended) Build once in Visual Studio:
    - Open `unreal/TongSim_Lite.sln`
    - Configuration: `Development Editor`
    - Platform: `Win64`
    - Build
4. In the editor, ensure plugins are enabled:
    - `TongSimCore`
    - `TongSimGrpc`

!!! warning ":material-alert: gRPC endpoint & firewall"
    The UE server binds to `0.0.0.0:5726` by default (see `unreal/Plugins/TongSimGrpc/Source/TongosGrpc/Private/TSGrpcSubsystem.cpp`).

    - On Windows, allow **Unreal Editor** through the firewall
    - From the same machine, connect with `127.0.0.1:5726`

---

## :material-language-python: Set up the Python SDK

=== ":material-flash: Option A: uv (recommended)"

    ```powershell
    uv venv
    uv sync
    ```

    Run examples (start Unreal first):

    ```powershell
    uv run python examples/quickstart_demo.py
    uv run python examples/voxel.py
    ```

=== ":material-package-variant: Option B: pip"

    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -e .
    ```

    Run an example:

    ```powershell
    python examples\quickstart_demo.py
    ```

!!! note ":material-information-outline: Python version"
    TongSIM Lite requires Python `>= 3.12` (see `pyproject.toml`).

---

## :material-file-code-outline: (Optional) Regenerate protobuf stubs

Only needed when `.proto` files change or generated files are missing.

```powershell
uv run python scripts/generate_pb2.py
```

Generated code is written to `src/tongsim_lite_protobuf/`.

---

## :material-lan-connect: Smoke test (Python ↔ UE)

1. Start Unreal Editor and **Play** any map so the gRPC server is running.
2. In a terminal at the repo root, run:

=== "PowerShell (Windows)"

    ```powershell
    uv run python -c "from tongsim import TongSim; sim=TongSim('127.0.0.1:5726'); print('connected', sim.context.uuid); sim.close()"
    ```

=== "Bash (Linux/macOS)"

    ```bash
    uv run python -c "from tongsim import TongSim; sim=TongSim('127.0.0.1:5726'); print('connected', sim.context.uuid); sim.close()"
    ```

If it prints `connected <id>`, the connection is working.

---

## :material-bug: Troubleshooting

??? tip "Connection refused / timeout"
    - Confirm Unreal is running and `TongSimGrpc` is enabled.
    - Check that port `5726` is free and allowed through the firewall.
    - If you changed the server bind address, update your Python endpoint accordingly.

??? tip "Protobuf / API mismatch"
    - Ensure your Unreal project and Python SDK come from the same revision.
    - Re-run `uv run python scripts/generate_pb2.py` if `.proto` files changed.

---

**Next:** [First Simulation](first_simulation.md) · [How TongSIM Works](client_server.md)
