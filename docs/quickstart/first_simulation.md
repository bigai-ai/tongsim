# :material-rocket-launch: First Simulation

Run **TongSIM Lite** in Unreal Editor and control it from the **Python SDK** over **gRPC**.

The quickstart demo uses `examples/quickstart_demo.py`, which will **automatically switch to the demo level** before running.

!!! tip ":material-check-circle: Goal"
    - Start a Play session (PIE) in Unreal Editor
    - Run `examples/quickstart_demo.py`
    - Observe the world respond (spawn/move/query)

---

## :material-clipboard-check: Prerequisites

- Finish the setup in [Environment Setup](environment.md)
- Unreal project can open and compile: `unreal/TongSim_Lite.uproject`
- Python dependencies are installed (`uv sync` or `pip install -e .`)

---

## :material-monitor: Start Unreal (PIE)

1. Open `unreal/TongSim_Lite.uproject` with **Unreal Engine 5.6**.
2. Click **Play** (recommended: **New Editor Window (PIE)**).

!!! note ":material-information-outline: gRPC availability"
    The UE-side gRPC server becomes available during **Play**. The default endpoint is `127.0.0.1:5726`.

---

## :material-console: Run the demo script

=== ":material-flash: uv"

    ```powershell
    uv run python examples/quickstart_demo.py
    ```

=== ":material-package-variant: venv + pip"

    ```powershell
    python examples/quickstart_demo.py
    ```

!!! note ":material-map-marker: Level switching"
    The script switches to `/Game/Developer/Maps/L_DemoRL` automatically. If you want to run on the current level instead, see the script header in `examples/quickstart_demo.py`.

---

## :material-eye-check: What you should see

- The terminal prints steps such as `ResetLevel`, `QueryState`, `SpawnActor`, and `SimpleMoveTowards`.
- In Unreal, the script spawns actors (coins / mannequins) and moves them toward target points.

---

## :material-test-tube: Try more demos (optional)

| Script | What it tests | Notes |
|---|---|---|
| `examples/voxel.py` | Voxel query + decoding + rendering | Saves images under `./voxel_frames/` |

---

## :material-bug: Troubleshooting

??? tip "Connection refused / timeout"
    - Confirm Unreal Editor is **playing**.
    - Allow Unreal Editor through the firewall.
    - Confirm your Python endpoint matches the UE port (default `127.0.0.1:5726`).
    - If you disabled the gRPC plugin, re-enable it and restart the editor.

??? tip "Port already in use / not listening"
    The UE server binds to `0.0.0.0:5726` by default. If the port is already in use, update
    `unreal/Plugins/TongSimGrpc/Source/TongosGrpc/Private/TSGrpcSubsystem.cpp` and rebuild.

    === ":material-microsoft-windows: Windows"

        ```powershell
        netstat -ano | findstr :5726
        ```

    === ":material-linux: Linux"

        ```bash
        ss -lntp | grep 5726
        ```

??? tip "Level switch did not happen"
    - Ensure you started **Play** before running the script.
    - Check whether `/Game/Developer/Maps/L_DemoRL` exists in your project content.
    - As a fallback, open `/Game/Developer/Maps/L_DemoRL` manually and re-run the script.

??? tip "SpawnActor failed / actors do not move"
    - Ensure Git LFS assets are present (`git lfs pull`).
    - The level must have a valid NavMesh (press **P** in the viewport to visualize navigation).

---

**Next:** [How TongSIM Works](client_server.md)
