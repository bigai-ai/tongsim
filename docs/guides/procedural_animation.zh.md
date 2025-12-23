# :material-run-fast: ControlRig 程序化动画

本页介绍 TongSIM 风格角色使用 **Unreal ControlRig** 实现的“**程序化步态/行走**”设计，主要用于：

- 人形/多足生物的自然行走节奏
- 结合 IK 的地形自适应（落脚点预测 + 脚底锁定）
- 与行为树或学习策略结合，实现可控的实时姿态

!!! note ":material-information-outline: 适用范围"
    TongSIM Lite 的 gRPC API 主要用于 Gameplay 层面的 actor 控制；本页聚焦 **UE 内部的角色动画/ControlRig 结构**，用于构建可用于仿真的角色表现。

---

## :material-target: 设计目标

- **地形自适应**：支撑期脚底稳定，结合 IK 贴合地面
- **步态可组合**：通过相位偏移与分组配置不同步态风格
- **速度信号稳定**：使用平滑后的速度驱动步态频率/步长
- **可控参数暴露**：为 AI 提供速度、转向、相位等控制入口

---

## :material-speedometer: 速度估计（平滑）

一个可靠的步态控制需要稳定的速度信号。

推荐流程：

1. 由连续两帧的平移差计算 **原始速度**（除以 `DeltaTime`）。
2. 每帧用弹簧插值/临界阻尼等方式对速度进行平滑。

!!! tip ":material-tune: 为什么要平滑"
    角色移动速度会受碰撞、坡度修正、插值等影响产生噪声；平滑后可避免步态频繁抖动和突变。

---

## :material-timeline-clock: 步态周期：摆动与支撑

每条腿使用归一化周期 `progress ∈ [0, 1)`：

- **Swing（摆动）**：`progress ∈ [0, swing_percent)` — 脚从当前点移动到下一落点
- **Stance/Lock（支撑/锁定）**：`progress ∈ [swing_percent, 1)` — 脚在世界空间保持稳定

多足角色可为每条腿设置 **相位偏移（phase offset）** 来实现错峰节奏（例如六足的 6 个 offset）。

---

## :material-foot-print: 落脚预测

如果脚仅落在身体“当前正下方”，身体前进后脚会显得滞后。对落脚点做“向前预测”可以更接近真实生物的行走表现。

给定：

- `current_percent`：当前周期位置
- `swing_percent`：摆动占比
- `cycle_duration`：周期时长（秒）
- `velocity`：平滑后的身体速度（world space）

```text
predict_percent  = clamp(swing_percent - current_percent, 0.0, 1.0) + (1 - swing_percent) / 2
predict_time     = predict_percent * cycle_duration
predicted_offset = velocity * predict_time
```

!!! tip ":material-compass: 直观理解"
    `predict_percent` 由“剩余摆动时间 + 支撑期前半段”组成，用于估计身体处于支撑中段时的位置。

---

## :material-chart-bell-curve: 摆动轨迹与脚底锁定

实践建议：

- 摆动轨迹：用曲线/样条控制高度（中段最高）并在起落点平滑过渡。
- 支撑阶段：将脚锁定在世界空间，同时每帧解 IK 以贴合地面。
- 地形采样：对预测目标点做向下射线检测得到地面点与法线。

---

## :material-scale-balance: 平衡与身体控制

- 多足：保持重心位于支撑多边形内（由腿分组定义）。
- 人形：结合骨盆/脊柱控制器，必要时叠加 LookAt 约束来稳定上半身。

---

## :material-table: 参数建议

| 参数 | 常见范围 | 说明 |
|---|---:|---|
| `swing_percent` | 0.4–0.7 | 越大越“轻快”，越小越“沉稳” |
| `cycle_duration` | 0.3–1.2s | 随物种与速度调整 |
| `step_height` | 2–12cm | 过高会显得飘 |
| `phase_offsets` | 每条腿独立 | 用于制造错峰节奏 |
| `lock_blend` | 0–1 | 脚底锁定的平滑权重 |

---

## :material-link: 在本仓库中如何定位

- 角色相关资源（骨骼/动画/ControlRig）：`unreal/Content/TongSim/Characters/`
- 相关运行系统（Gameplay/角色控制）：`unreal/Plugins/TongSimCore/Source/TongSimGameplay/`

---

**下一步：** [UE 打包与部署](ue_packaging.md)
