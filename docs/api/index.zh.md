# API 总览

TongSIM Python SDK 的 API 文档按以下部分组织：

- **Runtime**：启动与会话管理相关的核心类型，例如 `TongSim`、`WorldContext`、`AsyncLoop`。
- **Math Types**：常用空间基础类型（`Vector3`、`Transform` 等）与几何工具函数。
- **gRPC Connection**：gRPC 通道/Stub 管理，以及 SDK↔Proto 的数据转换与安全调用封装。
- **Core Control**：基础的 actor 控制与查询能力（协议层由 `DemoRLService` 实现），包含导航、射线检测、控制台命令等。
- **Arena**：多关卡流式加载与 arena-local 坐标系下的 actor 工具。
- **Capture**：基于 Snapshot 的 RGB/Depth 采集相机接口。
- **Voxel Perception**：体素占用采样接口，用于感知与学习任务。

进入对应页面查看详细说明与 mkdocstrings 自动生成的 API 参考。
