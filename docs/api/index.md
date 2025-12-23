# API Overview

The TongSim Python SDK surfaces several API areas that are grouped into the
following sections:

- **Runtime**: Core classes such as `TongSim`, `WorldContext`, and `AsyncLoop`
  that bootstrap and coordinate a session.
- **Math Types**: Lightweight spatial primitives (`Vector3`, `Transform`, etc.)
  and helper functions used across the SDK.
- **gRPC Connection**: Channel/stub management and SDK↔Proto conversion helpers.
- **Core Control**: Baseline actor control, navigation, tracing, and console
  utilities (implemented by `DemoRLService` in TongSIM Lite).
- **Arena**: Multi-level streaming and arena-local actor utilities.
- **Capture**: Snapshot-based RGB/Depth capture cameras.
- **Voxel Perception**: Sampling volumetric information for perception and
  learning tasks.

Dive into each section for detailed guides and mkdocstrings-generated
API references.
