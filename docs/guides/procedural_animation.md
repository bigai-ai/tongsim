# :material-run-fast: ControlRig Procedural Animation

This page documents the **procedural locomotion** design used by TongSIM-style characters, implemented with **Unreal ControlRig**. It is primarily intended for:

- believable walking cycles for humanoids and multi-legged creatures
- real-time adaptation to uneven terrain (with IK / foot locking)
- integrating motion control with behavior trees or learned policies

!!! note ":material-information-outline: Scope"
    TongSIM Lite’s gRPC APIs control actors at the gameplay level. This guide focuses on **character animation rigs inside UE** and how to structure them for simulation use.

---

## :material-target: Design goals

- **Terrain-aware**: feet stay planted during stance and conform to uneven ground
- **Composable gait**: configure phase offsets and leg grouping for different styles
- **Stable velocity signal**: drive gait using a smoothed velocity estimate
- **Policy-friendly hooks**: expose parameters (desired speed, turn rate, phase) for AI control

---

## :material-speedometer: Velocity estimation (smoothed)

A robust gait controller needs a stable velocity estimate.

Recommended pipeline:

1. Compute **raw velocity** from delta translation between frames (divide by `DeltaTime`).
2. Smooth it each frame using a spring interpolation / critically damped filter.

!!! tip ":material-tune: Why smoothing helps"
    Raw velocity from character movement can be noisy due to collisions, slope correction and network-style interpolation. Smoothing avoids “twitchy” gait changes.

---

## :material-timeline-clock: Gait cycle: swing vs stance

Each leg follows a normalized cycle `progress ∈ [0, 1)`:

- **Swing**: `progress ∈ [0, swing_percent)` — foot moves to the next target
- **Stance / lock**: `progress ∈ [swing_percent, 1)` — foot stays planted in world space

For multi-legged creatures you can de-synchronize legs by adding a per-leg **phase offset** (for example a hexapod using 6 offsets).

---

## :material-foot-print: Foot placement prediction

If the foot lands exactly under the current body position, the torso will quickly move past it and the foot will “trail”. Predicting the landing point ahead improves realism.

Given:

- `current_percent`: current leg cycle progress
- `swing_percent`: swing ratio of the cycle
- `cycle_duration`: seconds per cycle
- `velocity`: smoothed body velocity (world space)

```text
predict_percent  = clamp(swing_percent - current_percent, 0.0, 1.0) + (1 - swing_percent) / 2
predict_time     = predict_percent * cycle_duration
predicted_offset = velocity * predict_time
```

!!! tip ":material-compass: Intuition"
    `predict_percent` uses the remaining swing time plus half of stance, aiming where the body will be mid-support.

---

## :material-chart-bell-curve: Swing trajectory & foot locking

Practical recommendations:

- Swing trajectory: use a curve/spline for height (peak at mid-swing) and blend smoothly at takeoff/landing.
- Stance: lock the foot in world space, then solve IK each frame to match the terrain.
- Terrain sampling: raycast down from the predicted target to find the ground point and normal.

---

## :material-scale-balance: Balance and body motion

- Multi-legged: keep the center of mass inside the support polygon (configured by leg groups).
- Humanoids: blend pelvis/spine controllers and add LookAt constraints to maintain stability.

---

## :material-table: Suggested parameters

| Parameter | Typical range | Notes |
|---|---:|---|
| `swing_percent` | 0.4–0.7 | Higher swing feels “lighter”, lower swing feels “heavier” |
| `cycle_duration` | 0.3–1.2s | Tune per species and speed |
| `step_height` | 2–12cm | Too high looks “floaty” |
| `phase_offsets` | per leg | Use offsets to stagger legs |
| `lock_blend` | 0–1 | Blend into foot lock smoothly |

---

## :material-link: Where to look in this repo

- Character content (rigs, skeletons, animation assets): `unreal/Content/TongSim/Characters/`
- Related runtime systems (gameplay + agent control): `unreal/Plugins/TongSimCore/Source/TongSimGameplay/`

---

**Next:** [UE Packaging & Deployment](ue_packaging.md)
