# :material-lan: TongSIM 工作原理概览

TongSIM Lite 采用典型的 **Client–Server（客户端-服务端）** 架构：

- :material-server: **服务端（Unreal Engine）** 负责运行仿真世界，并通过 **gRPC** 对外提供能力接口
- :material-laptop: **客户端（Python SDK）** 连接服务端并发起 RPC 调用（生成/移动/查询/体素等）

```text
Unreal Engine（TongSIM Lite）                Python（tongsim）
┌──────────────────────────┐                ┌──────────────────────┐
│ TongSimCore + TongSimGrpc│  gRPC/protobuf  │ TongSim / UnaryAPI    │
│ 世界状态 & 物理           │ <-------------> │ examples/*.py         │
└──────────────────────────┘                └──────────────────────┘
```

!!! info ":material-link-variant: 连接地址"
    - 客户端默认：`127.0.0.1:5726`
    - 服务端监听：`0.0.0.0:5726`（监听所有网卡）

---

## :material-server: Unreal 侧（服务端）

服务端主要负责：

- 管理世界状态（关卡、Actor、物理、导航、感知等）
- 执行动作与任务（移动/导航/拾取/射线检测/体素查询等）
- 通过 gRPC 将结果返回给客户端

运行方式：

- 打开 `unreal/TongSim_Lite.uproject`
- 在 Editor 中点击 **Play（PIE）**，此时 gRPC 服务通常可用

---

## :material-laptop: Python 侧（客户端）

客户端主要负责：

- 连接 UE 端 endpoint
- 调用高层 RPC 封装（例如 `UnaryAPI.reset_level`、`UnaryAPI.spawn_actor`、`UnaryAPI.query_voxel`）
- 编写实验/训练循环（见 `examples/`）

!!! note ":material-code-tags: 控制台命令"
    SDK 提供 `UnaryAPI.exec_console_command(...)`，可执行 UE 控制台命令（如 `stat fps`、`open <level>`）。
    快速开始脚本 `examples/quickstart_demo.py` 会使用该能力自动切换到示例关卡。

---

## :material-repeat: 推荐工作流

1. :material-play: 在 Unreal Editor 中点击 **Play**
2. :material-console: 运行 `examples/` 下的 Python 脚本
3. :material-pencil: 迭代优化：
    - UE 侧：地图/蓝图/资产/交互逻辑
    - Python 侧：策略/算法/数据采集/评测脚本

---

## :material-school: Tutorials

当你已经能成功运行 `examples/quickstart_demo.py`，建议继续阅读 Tutorials：

- :material-run-fast: **单智能体 RL 导航** — 面向室内多房间场景的探索与导航任务，提供 Gymnasium 风格环境封装与 Stable-Baselines3 baseline。
  从这里开始：[任务概览](../tutorial/single_agent_nav/task_overview.md)
- :material-account-group: **多智能体 RL 导航** — 基于轻量化 XuanCe 适配的 MACS 协作任务，强调部分可观测条件下的协同与决策。
  从这里开始：[任务概览](../tutorial/multi_agent_nav/task_overview.md)

---

**下一步：** [单智能体 RL 导航](../tutorial/single_agent_nav/task_overview.md) · [多智能体 RL 导航](../tutorial/multi_agent_nav/task_overview.md)
