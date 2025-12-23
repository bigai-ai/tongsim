# :material-lan: How TongSIM Works

TongSIM Lite follows a **client–server** design:

- :material-server: **Server (Unreal Engine)** runs the simulation and exposes APIs via **gRPC**
- :material-laptop: **Client (Python SDK)** connects to the server and sends RPC calls (spawn/move/query/voxel, etc.)

```text
Unreal Engine (TongSIM Lite)                 Python (tongsim)
┌──────────────────────────┐                ┌──────────────────────┐
│ TongSimCore + TongSimGrpc│  gRPC/protobuf  │ TongSim / UnaryAPI    │
│ World & physics          │ <-------------> │ examples/*.py         │
└──────────────────────────┘                └──────────────────────┘
```

!!! info ":material-link-variant: Endpoints"
    - Client default: `127.0.0.1:5726`
    - Server bind: `0.0.0.0:5726` (listens on all interfaces)

---

## :material-server: Unreal side (server)

What the server does:

- Owns the world state (levels, actors, physics, navigation, perception)
- Executes actions (move, navigate, pick up, traces, voxel queries)
- Streams results back to the client through gRPC responses

How to run it:

- Open `unreal/TongSim_Lite.uproject`
- Start a **Play** session (PIE) so the gRPC server is available

---

## :material-laptop: Python side (client)

What the client does:

- Connects to the UE server endpoint
- Calls high-level RPC helpers (for example `UnaryAPI.reset_level`, `UnaryAPI.spawn_actor`, `UnaryAPI.query_voxel`)
- Runs experiments/training loops (see `examples/`)

!!! note ":material-code-tags: Console commands"
    The SDK exposes `UnaryAPI.exec_console_command(...)`, which can run UE console commands (for example `stat fps`, `open <level>`).
    The quickstart script `examples/quickstart_demo.py` uses this to switch to the demo level automatically.

---

## :material-repeat: Recommended workflow

1. :material-play: Start **Play** in Unreal Editor
2. :material-console: Run a Python script from `examples/`
3. :material-pencil: Iterate on:
    - maps/blueprints on the UE side
    - policies/logic/data collection on the Python side

---

## :material-school: Tutorials

Once you can run `examples/quickstart_demo.py`, move on to Tutorials:

- :material-run-fast: **Single-agent RL Navigation** — exploration + navigation in multi-room indoor scenes, with Gymnasium-style wrappers and Stable-Baselines3 baselines.
  Start here: [Task Overview](../tutorial/single_agent_nav/task_overview.md)
- :material-account-group: **Multi-agent RL Navigation** — cooperative multi-agent task (MACS) built on a lightweight adaptation of XuanCe, focusing on coordination under partial observability.
  Start here: [Task Overview](../tutorial/multi_agent_nav/task_overview.md)

---

**Next:** [Single-agent RL Navigation](../tutorial/single_agent_nav/task_overview.md) · [Multi-agent RL Navigation](../tutorial/multi_agent_nav/task_overview.md)
