# 🚀 单智能体导航任务

## 概览

本项目是一个专门用于评估智能体探索和导航能力的强化学习代码库，它以具有挑战性的清理室内的所有纸团任务为中心，要求智能体在有多个房间、每个房间中有多个障碍物的复杂室内环境中收集散落在地面上的纸团。

## 安装

1. **设置TongSIM**

   参考[TongSIM/Quickstart](../../quickstart/overview.md)，安装并配置TongSIM仿真环境，确认能够成功运行 `examples/quickstart_demo.py` 后，执行以下步骤。

2. **安装 `uv` (依赖管理)**

  本项目使用 uv 作为项目管理工具，推荐使用 uv 安装和管理依赖。
  请参考 [uv 官网](https://hellowac.github.io/uv-zh-cn/) 进行安装。

3. **安装依赖库**

   将工作目录切换到项目根目录下，执行:
   ```bash
   # Install the RL task-specific group
   uv sync --group rl_nav
   ```

## 使用

将工作目录切换到项目根目录下，执行：

**运行基线模型**

```bash
uv run python examples/rl_nav/run.py test --model_name="search_ppo_10000000_steps.zip"
```

**人类测试**

```bash
uv run python examples/rl_nav/run.py manual
```

**训练模型**

```bash
uv run python examples/rl_nav/run.py train
```

---

**备注**

* 如果你使用的是 Windows，绝大多数 Python 工具都支持使用正斜杠（/）；否则请改用反斜杠（\）。
* 在运行任何脚本之前，请确保 TongSIM 服务已经启动并且可正常访问。
