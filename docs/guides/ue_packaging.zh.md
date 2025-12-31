# :material-package: UE 打包与部署

本指南介绍如何将 **TongSIM Lite** 打包为独立的 Unreal 应用，并从 Python SDK 连接到打包后的服务端。

!!! note ":material-lan-connect: gRPC 端点"
    TongSIM Lite 的 gRPC server 默认绑定 `0.0.0.0:5726`（见 `unreal/Plugins/TongSimGrpc/Source/TongosGrpc/Private/TSGrpcSubsystem.cpp`）。

---

## :material-hammer-wrench: 前置条件

- 已安装 Unreal Engine **5.6**（与 `unreal/TongSim_Lite.uproject` 对齐）
- 工程在 Editor 中能正常编译运行
- 若需要远程连接：在服务端机器放通 TCP `5726` 端口

---

## :material-rocket-launch: 通过 Unreal Editor 打包（推荐）

1. 打开 `unreal/TongSim_Lite.uproject`。
2. 在 `Project Settings → Packaging` 中配置打包选项（常见：启用 Pak、选择构建配置等）。
3. 通过 `File → Package Project` 选择目标平台（例如 Windows 64-bit）。

!!! tip ":material-check-circle: 打包后的快速自检"
    - 输出目录包含可执行文件与 `Content/Paks/*.pak`。
    - 启动可执行文件后保持运行稳定。
    - Python 侧使用 `<host_ip>:5726` 进行连接验证。

---

## :material-console: Python 连接打包后的服务端

当 UE 打包程序运行在另一台机器上时：

```python
from tongsim import TongSim

with TongSim("YOUR_SERVER_IP:5726") as ts:
    # 执行任意 RPC
    print(ts.context.uuid)
```

=== ":material-microsoft-windows: Windows 防火墙"

    为打包后的可执行文件放通入站 TCP `5726`（或对局域网开放该端口）。

=== ":material-linux: Linux 防火墙（示例）"

    ```bash
    sudo ufw allow 5726/tcp
    ```

---

## :material-tune: 运行注意事项

- **无渲染运行**：可用来提升训练速度；但请注意 **Capture** 等功能需要渲染后端才能产生图像/深度数据。
- **端口修改**：当前端口为硬编码；如需修改请更新 `TSGrpcSubsystem.cpp` 并重新编译。

---

## :material-bug: 常见问题

??? tip "Python 连接失败（connection refused / timeout）"
    - 确认打包程序正在运行并监听 `5726`。
    - 检查服务端机器的防火墙/安全软件。
    - 远程连接时 endpoint 必须是 `<server_ip>:5726`，不能写 `127.0.0.1`。

??? tip "打包程序能运行，但场景/资产缺失"
    - 确认相关资源被 cook 进了 pak。
    - 使用外部资产时，确保资源位于 `unreal/Content/` 下（先运行 `python scripts/fetch_unreal_content.py` 下载资源），并被打包地图引用到。

---

**下一步：** [系统架构概览](../architecture/platform_overview.md)
