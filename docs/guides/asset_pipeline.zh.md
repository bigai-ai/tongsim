# :material-package-variant-closed: 资产与场景管线

本指南介绍如何将资产接入 **TongSIM Lite**，并将场景制作成可通过 **Arena** 接口加载的关卡。

!!! tip ":material-check-circle: 你将掌握"
    - TongSIM 资产库的获取方式
    - UE 工程内的资源组织建议
    - 如何制作可被 `ArenaService/LoadArena` 流式加载的关卡

---

## :material-database: 获取 TongSIM 资产

TongSIM Lite 的 Unreal 工程资源（`unreal/Content/`）不在 Git 仓库中，请从以下数据集下载：

- :simple-huggingface: Unreal Content 数据集：`https://huggingface.co/datasets/bigai/tongsim-unreal-content`

=== ":material-script-text: 使用脚本下载（推荐）"

    ```bash
    python -m pip install -U huggingface_hub
    python scripts/fetch_unreal_content.py
    ```

=== ":material-language-python: 使用 Python 下载（huggingface_hub）"

    ```bash
    python -m pip install -U huggingface_hub
    python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='bigai/tongsim-unreal-content', repo_type='dataset', local_dir='tongsim-unreal-content', local_dir_use_symlinks=False)"
    ```

!!! note ":material-information-outline: 导入还是拷贝？"
    具体如何接入取决于资产库提供的格式：

    - 对 TongSIM Lite，运行 `python scripts/fetch_unreal_content.py` 将 UE 资源（`.uasset`、`.umap`）安装到 `unreal/Content/`。
    - 若资产库提供 **源资产**（`.fbx`、`.gltf`、贴图等），请通过 Unreal Editor 的导入流程导入。

---

## :material-cube-outline: 导入外部模型（FBX/GLTF）

如果你导入的是源模型，建议统一这些约定：

- **单位**：Unreal 使用厘米（1 UU = 1 cm）
- **坐标轴**：Z-up
- **缩放**：尽量保持统一缩放，避免导入时大量“修正”

!!! tip ":material-tune: 导入检查清单"
    - 合理设置 pivot/origin（尤其是可交互物体）
    - 骨骼模型：保留 root 骨骼命名与层级结构
    - 碰撞体：根据交互需求选择 simple / complex collision

---

## :material-map: 制作 Arena 关卡（可流式加载的 `UWorld`）

TongSIM Lite 的 Arena 系统使用 `ULevelStreamingDynamic` 将 **关卡资产** 动态加载到当前世界中。

### :material-folder-multiple-outline: 推荐的目录结构

在下载并准备好 `unreal/Content` 后，本仓库使用了较清晰的“演示内容 vs 可复用内容”划分：

- 演示地图：`unreal/Content/Developer/Maps/`
- 工程地图：`unreal/Content/Maps/`
- 通用资产：`unreal/Content/TongSim/`

建议将 Arena 地图放在 `unreal/Content/Maps/Sublevels/` 下，便于与入口地图区分。

### :material-link-variant: 获取 `level_asset_path`

`ArenaService/LoadArena` 需要一个 **soft object path** 字符串。

在 Unreal Editor 中：

1. 在 **Content Browser** 选中你的关卡资产
2. 右键 → **Copy Reference**
3. 将复制出来的字符串作为 `level_asset_path`

典型示例（UE 常见格式）：

```text
/Game/Maps/Sublevels/MyArena.MyArena
```

---

## :material-anchor: Anchor 与坐标系

**Anchor transform** 用于将 Arena 实例摆放到世界中，并定义 **arena-local** 的局部坐标系。

!!! tip ":material-map-marker-radius: 推荐实践"
    制作关卡时尽量把内容放在局部原点附近（接近 `(0, 0, 0)`）。在并行训练时，通过不同的 anchor 将多个实例摆放到相距较远的位置，避免互相干扰。

相关接口：

- `ArenaService/LocalToWorld`
- `ArenaService/WorldToLocal`

---

## :material-console: 用 Python 加载并验证

```python
from tongsim import TongSim
from tongsim.connection.grpc.unary_api import UnaryAPI
from tongsim.math import Transform, Vector3

LEVEL = "/Game/Maps/Sublevels/MyArena.MyArena"
ANCHOR = Transform(location=Vector3(0, 0, 0))

with TongSim("127.0.0.1:5726") as ts:
    arena_id = ts.context.sync_run(
        UnaryAPI.load_arena(ts.context.conn, LEVEL, anchor=ANCHOR, make_visible=True)
    )
    arenas = ts.context.sync_run(UnaryAPI.list_arenas(ts.context.conn))
    print(arena_id, arenas)
```

---

## :material-bug: 常见问题

??? tip "LoadArena 失败 / 返回空 id"
    - 使用 Editor 时确认已进入 **Play (PIE)**。
    - 确保 `level_asset_path` 通过 **Copy Reference** 获取，并且对应的是 `UWorld` 资产。
    - 检查资产依赖是否齐全（若 `unreal/Content` 缺失，请运行 `python scripts/fetch_unreal_content.py`）。

??? tip "Arena 加载成功但导航不可用"
    - 为 Arena 地图构建 **NavMesh**（视口按 **P** 可视化）。
    - 多个 Arena 不要摆放过近（NavMesh 可能产生意外的合并/干扰）。

---

**下一步：** [多层关卡系统](multilevel.md)
