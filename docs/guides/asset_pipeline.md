# :material-package-variant-closed: Asset & Scene Pipeline

This guide covers a practical workflow for bringing assets into **TongSIM Lite** and turning them into **Arena**-loadable levels.

!!! tip ":material-check-circle: You will learn"
    - Where to download TongSIM assets
    - How to structure assets in the UE project
    - How to build a level that can be loaded via `ArenaService/LoadArena`

---

## :material-database: Get TongSIM assets

TongSIM Lite does not store `unreal/Content/` in Git. Download the Unreal Content dataset:

- :simple-huggingface: Unreal Content dataset: `https://huggingface.co/datasets/bigai/tongsim-unreal-content`

=== ":material-script-text: Download via helper script (recommended)"

    ```bash
    python -m pip install -U huggingface_hub
    python scripts/fetch_unreal_content.py
    ```

=== ":material-language-python: Download via Python (huggingface_hub)"

    ```bash
    python -m pip install -U huggingface_hub
    python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='bigai/tongsim-unreal-content', repo_type='dataset', local_dir='tongsim-unreal-content', local_dir_use_symlinks=False)"
    ```

!!! note ":material-information-outline: Import vs copy"
    How you integrate assets depends on the dataset format:

    - For TongSIM Lite, run `python scripts/fetch_unreal_content.py` to install UE-ready assets (`.uasset`, `.umap`) into `unreal/Content/`.
    - If the dataset provides **source** assets (`.fbx`, `.gltf`, textures), import them through Unreal Editor.

---

## :material-cube-outline: Import external meshes (FBX/GLTF)

If you are importing source meshes, keep these conventions consistent:

- **Units**: Unreal uses centimeters (1 UU = 1 cm)
- **Up axis**: Z-up
- **Scale**: keep uniform scale; avoid import-time “fixups” when possible

!!! tip ":material-tune: Suggested import checklist"
    - Keep mesh pivot/origin meaningful (especially for interactables)
    - For skeletal meshes: preserve root bone naming and hierarchy
    - Verify collision (simple vs complex) matches your interaction needs

---

## :material-map: Build an Arena level (streamable `UWorld`)

TongSIM Lite’s Arena system streams **level assets** into the current world using `ULevelStreamingDynamic`.

### :material-folder-multiple-outline: Recommended content layout

After `unreal/Content` is downloaded, the project uses a split between demo and reusable content:

- Demo maps: `unreal/Content/Developer/Maps/`
- Project maps: `unreal/Content/Maps/`
- Reusable assets: `unreal/Content/TongSim/`

You can store your Arena maps under `unreal/Content/Maps/Sublevels/` (recommended), so they are clearly separated from entry maps.

### :material-link-variant: Get the `level_asset_path`

`ArenaService/LoadArena` expects a **soft object path** string.

In Unreal Editor:

1. Select the level asset in **Content Browser**
2. Right click → **Copy Reference**
3. Use the copied string as `level_asset_path`

Example (typical UE format):

```text
/Game/Maps/Sublevels/MyArena.MyArena
```

---

## :material-anchor: Anchors and coordinates

An **anchor transform** places an Arena instance into the world and defines its **arena-local** coordinate frame.

!!! tip ":material-map-marker-radius: Best practice"
    Author the Arena level near its local origin (around `(0, 0, 0)`). Use the anchor to place multiple instances far apart for parallel training.

Related API:

- `ArenaService/LocalToWorld`
- `ArenaService/WorldToLocal`

---

## :material-console: Load and validate from Python

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

## :material-bug: Troubleshooting

??? tip "LoadArena fails / returns an empty id"
    - Ensure Unreal is in **Play (PIE)** when using the editor.
    - Confirm `level_asset_path` comes from **Copy Reference** and points to a `UWorld` asset.
    - Check that the level and its dependencies exist locally (run `python scripts/fetch_unreal_content.py` if `unreal/Content` is missing).

??? tip "Arena loads, but navigation does not work"
    - Build a **NavMesh** for the Arena map (press **P** to visualize).
    - Avoid overlapping multiple arenas too closely (NavMesh can merge in unexpected ways).

---

**Next:** [Multi-level System](multilevel.md)
