# 快速启动

## 安装

**前置条件**

1. 参考[环境准备](../../quickstart/environment.md)与[首个仿真任务](../../quickstart/first_simulation.md)，完成 TongSIM 仿真环境安装与配置。确认能够成功运行 `examples/quickstart_demo.py` 后，按照以下步骤安装配置单智能体导航任务场景。

2. 本项目使用 uv 作为项目管理工具，推荐使用 uv 安装和管理依赖。请参考 [uv 官网](https://hellowac.github.io/uv-zh-cn/) 进行安装。


**安装依赖库**

本项目需要的依赖库及版本要求如下：
```toml
[dependency-groups]
rl_nav = [
    "gymnasium>=1.2.1",
    "pygame>=2.6.1",
    "stable-baselines3[extra]>=2.7.0",
    "tensorboard>=2.20.0",
    "pillow>=10.0.0",
    "opencv-python>=4.10.0.84",
]
```
相关配置记录在 `./pyproject.toml`的rl_nav组下。将工作目录切换到项目根目录下，执行
```bash
uv sync --group rl_nav
```

## 验证
本项目主要结构：
```bash
./examples/rl_nav
│  collect_task.py # task env
│  run.py # tain/evaluation/manual
│
├─common # common module
│
├─model # baseline model
│
└─occupy_grid # occupy grid png data
```

启动TongSIM，打开空场景地图。将工作目录切换到项目根目录下，执行：
```bash
uv run python ./examples/rl_nav/run.py test --model_name="search_ppo_10000000_steps.zip"
```
TongSIM加载室内场景，桌面弹出占用网格窗口，说明环境配置成功。具体效果如下图所示：

![Task Launched Successfully](run.png)
***图 1**. 任务启动成功*
