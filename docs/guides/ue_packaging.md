# :material-package: UE Packaging & Deployment

This guide explains how to package **TongSIM Lite** as a standalone Unreal application and connect to it from the Python SDK.

!!! note ":material-lan-connect: gRPC endpoint"
    TongSIM Lite’s gRPC server binds to `0.0.0.0:5726` by default (see `unreal/Plugins/TongSimGrpc/Source/TongosGrpc/Private/TSGrpcSubsystem.cpp`).

---

## :material-hammer-wrench: Prerequisites

- Unreal Engine **5.6** installed (matches `unreal/TongSim_Lite.uproject`)
- Project builds successfully in editor
- If you plan to connect remotely: open TCP port `5726` in the host firewall

---

## :material-rocket-launch: Package from Unreal Editor (recommended)

1. Open `unreal/TongSim_Lite.uproject`.
2. Configure `Project Settings → Packaging` (typical options: enable Pak file, set build configuration).
3. Use `File → Package Project` and select the target platform (for example Windows 64-bit).

!!! tip ":material-check-circle: Quick sanity check after packaging"
    - The packaged folder contains the executable and `Content/Paks/*.pak`.
    - Launch the executable and ensure it stays running.
    - From Python, connect to `<host_ip>:5726`.

---

## :material-console: Connect from Python to a packaged server

If the packaged UE app runs on another machine:

```python
from tongsim import TongSim

with TongSim("YOUR_SERVER_IP:5726") as ts:
    # Run any RPC you need
    print(ts.context.uuid)
```

=== ":material-microsoft-windows: Windows firewall"

    Allow inbound TCP `5726` for the packaged executable (or open the port for your private network).

=== ":material-linux: Linux firewall (example)"

    ```bash
    sudo ufw allow 5726/tcp
    ```

---

## :material-tune: Runtime considerations

- **Headless / no rendering**: You may run without rendering for speed, but note that **Capture** features require a rendering backend.
- **Port customization**: the port is currently hard-coded; change it in `TSGrpcSubsystem.cpp` and rebuild if you need a different port.

---

## :material-bug: Troubleshooting

??? tip "Python cannot connect (connection refused / timeout)"
    - Confirm the packaged application is running and listening on `5726`.
    - Check firewalls/security software on the host machine.
    - Ensure you use the correct endpoint: `<server_ip>:5726` (not `127.0.0.1` when connecting remotely).

??? tip "Packaged build runs, but scenes/assets are missing"
    - Confirm the assets are included in the packaging cook.
    - If you use external assets, ensure they are located under `unreal/Content/` and referenced by packaged maps.

---

**Next:** [System Overview](../architecture/platform_overview.md)
