# :material-hammer-wrench: 环境准备

本页将帮助你在本地完成 **TongSIM Lite** 的基础环境搭建，并验证 **Unreal 端**与**Python SDK** 可以通过 **gRPC** 正常通信。

!!! tip ":material-check-circle: 本页你将完成"
    - 能打开并运行 Unreal 工程：`unreal/TongSim_Lite.uproject`
    - 安装 Python SDK 依赖（`uv` 或 `pip`）
    - 从 Python 连接 UE 的 gRPC 服务（`127.0.0.1:5726`）

---

## :material-clipboard-check: 前置依赖

=== ":material-microsoft-windows: Windows 10/11（推荐）"

    - Unreal Engine `5.6`（Epic Games Launcher 安装）
    - Visual Studio `2022`（建议勾选工作负载）：
        - **使用 C++ 的桌面开发**
        - **使用 C++ 的游戏开发**
    - Python `>= 3.12`
    - Git + Git LFS
    - （可选）NVIDIA 驱动 / CUDA（仅在你的流程需要时）

=== ":material-linux: Ubuntu 22.04"

    - Unreal Engine `5.6`（Linux 安装方式差异较大，请参考 Epic 官方文档）
    - Python `>= 3.12`
    - Git + Git LFS

!!! warning ":material-alert: 路径命名规范"
    建议将工程放在 **不含中文、空格、特殊字符** 且 **目录层级不过深** 的路径下，以避免 Unreal 构建与资源加载问题。

---

## :material-download: 获取代码（Git + LFS）

```powershell
git clone https://github.com/bigai-ai/tongsim
cd tongsim
git lfs install
git lfs pull
```

!!! note ":material-information-outline: 为什么要用 LFS？"
    TongSIM 的大量资源通过 **Git LFS** 存储。若跳过 `git lfs pull`，打开 Unreal 工程时可能会出现资源缺失。

---

## :material-monitor: 构建并运行 Unreal 工程

1. 使用 **Unreal Engine 5.6** 打开 `unreal/TongSim_Lite.uproject`。
2. 若弹出提示，请允许 Unreal **生成工程文件**并**编译模块**。
3.（Windows 推荐）在 Visual Studio 中手动构建一次：
    - 打开 `unreal/TongSim_Lite.sln`
    - 配置：`Development Editor`
    - 平台：`Win64`
    - Build
4. 在 Editor 中确认插件已启用：
    - `TongSimCore`
    - `TongSimGrpc`

!!! warning ":material-alert: gRPC 地址与防火墙"
    UE 端默认监听 `0.0.0.0:5726`（见 `unreal/Plugins/TongSimGrpc/Source/TongosGrpc/Private/TSGrpcSubsystem.cpp`）。

    - Windows 上若弹出防火墙提示，请允许 **Unreal Editor** 访问网络
    - 本机连接时，Python 侧使用 `127.0.0.1:5726` 即可

---

## :material-language-python: 配置 Python SDK

=== ":material-flash: 方案 A：uv（推荐）"

    ```powershell
    uv venv
    uv sync
    ```

    运行示例（请先启动 Unreal）：

    ```powershell
    uv run python examples/quickstart_demo.py
    uv run python examples/voxel.py
    ```

=== ":material-package-variant: 方案 B：pip"

    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -e .
    ```

    运行示例：

    ```powershell
    python examples\quickstart_demo.py
    ```

!!! note ":material-information-outline: Python 版本要求"
    TongSIM Lite 需要 Python `>= 3.12`（见 `pyproject.toml`）。

---

## :material-file-code-outline: （可选）重新生成 protobuf 代码

仅在 `.proto` 发生变更或生成文件缺失时需要执行：

```powershell
uv run python scripts/generate_pb2.py
```

生成结果位于 `src/tongsim_lite_protobuf/`。

---

## :material-lan-connect: 连通性验证（Python ↔ UE）

1. 启动 Unreal Editor，并在任意地图点击 **Play**，确保 gRPC 服务已启动。
2. 在项目根目录执行：

=== "PowerShell（Windows）"

    ```powershell
    uv run python -c "from tongsim import TongSim; sim=TongSim('127.0.0.1:5726'); print('connected', sim.context.uuid); sim.close()"
    ```

=== "Bash（Linux/macOS）"

    ```bash
    uv run python -c "from tongsim import TongSim; sim=TongSim('127.0.0.1:5726'); print('connected', sim.context.uuid); sim.close()"
    ```

若输出 `connected <id>`，表示连接正常。

---

## :material-bug: 常见问题

??? tip "连接失败 / 超时"
    - 确认 Unreal 正在运行且已启用 `TongSimGrpc` 插件。
    - 确认 `5726` 端口未被占用，并已在防火墙中放行。
    - 若你修改过 UE 端监听地址，请同步修改 Python 侧 endpoint。

??? tip "Protobuf / API 不匹配"
    - 确保 Unreal 工程与 Python SDK 来自同一版本/同一 revision。
    - 若 `.proto` 发生变更，请重新执行 `uv run python scripts/generate_pb2.py`。

---

**下一步：** [首个仿真任务](first_simulation.zh.md) · [工作原理概览](client_server.zh.md)
