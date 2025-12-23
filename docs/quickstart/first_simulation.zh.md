# :material-rocket-launch: 首个仿真任务

本页演示如何在 **Unreal Editor** 中运行 **TongSIM Lite**，并通过 **Python SDK** 使用 **gRPC** 与仿真进行交互。

快速开始将使用 `examples/quickstart_demo.py`，脚本会在运行前 **自动切换到示例关卡**。

!!! tip ":material-check-circle: 本页目标"
    - 在 Unreal Editor 中启动 Play（PIE）会话
    - 运行 `examples/quickstart_demo.py`
    - 观察仿真反馈（生成/移动/查询等）

---

## :material-clipboard-check: 前置条件

- 已完成 [环境准备](environment.zh.md)
- Unreal 工程可正常打开与编译：`unreal/TongSim_Lite.uproject`
- Python 依赖已安装（`uv sync` 或 `pip install -e .`）

---

## :material-monitor: 启动 Unreal（PIE）

1. 使用 **Unreal Engine 5.6** 打开 `unreal/TongSim_Lite.uproject`。
2. 点击 **Play**（推荐：**New Editor Window (PIE)**）。

!!! note ":material-information-outline: gRPC 可用性"
    UE 端 gRPC 服务通常会在 **Play** 期间可用。默认连接地址为 `127.0.0.1:5726`。

---

## :material-console: 运行示例脚本

=== ":material-flash: uv"

    ```powershell
    uv run python examples/quickstart_demo.py
    ```

=== ":material-package-variant: venv + pip"

    ```powershell
    python examples/quickstart_demo.py
    ```

!!! note ":material-map-marker: 关卡切换"
    脚本会自动切换到 `/Game/Developer/Maps/L_DemoRL`。如果你希望在当前关卡中运行，请查看 `examples/quickstart_demo.py` 文件头部说明。

---

## :material-eye-check: 预期效果

- 终端会输出 `ResetLevel`、`QueryState`、`SpawnActor`、`SimpleMoveTowards` 等步骤日志。
- Unreal 场景中会生成新的 Actor（例如 coin / mannequin），并执行移动等交互。

---

## :material-test-tube: 更多示例（可选）

| 脚本 | 覆盖能力 | 备注 |
|---|---|---|
| `examples/voxel.py` | 体素查询 + 解码 + 渲染 | 图片输出在 `./voxel_frames/` |

---

## :material-bug: 常见问题

??? tip "连接失败 / 超时"
    - 确认 Editor 处于 **Play** 状态。
    - Windows 防火墙需允许 Unreal Editor 访问网络。
    - 确认 Python 侧连接地址与 UE 端口一致（默认 `127.0.0.1:5726`）。
    - 如果你禁用了 gRPC 插件，请重新启用并重启 Editor。

??? tip "端口占用 / 未监听"
    UE 端默认监听 `0.0.0.0:5726`。若端口被占用，可修改
    `unreal/Plugins/TongSimGrpc/Source/TongosGrpc/Private/TSGrpcSubsystem.cpp` 并重新编译。

    === ":material-microsoft-windows: Windows"

        ```powershell
        netstat -ano | findstr :5726
        ```

    === ":material-linux: Linux"

        ```bash
        ss -lntp | grep 5726
        ```

??? tip "未自动切换到示例关卡"
    - 确认先点击 **Play** 再运行脚本。
    - 检查工程中是否存在 `/Game/Developer/Maps/L_DemoRL`。
    - 兜底方案：手动打开 `/Game/Developer/Maps/L_DemoRL` 后重新运行脚本。

??? tip "SpawnActor 失败 / 角色不移动"
    - 确认已拉取 LFS 资源（`git lfs pull`）。
    - 关卡需要存在可用 NavMesh（在视口按 **P** 可显示导航网格）。

---

**下一步：** [工作原理概览](client_server.zh.md)
