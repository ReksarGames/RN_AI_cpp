# Config Logic Guide (RN_AI)

This document explains parameter behavior and runtime logic, not file structure.

## 1) How Target Selection Works

Pipeline:
1. Read detections from the current frame.
2. Apply class filters and user constraints.
3. Compute pivot (aim point) for each candidate.
4. If lock is enabled, try to keep the current target first.
5. Otherwise choose a new target using priority and weights.
6. Compute mouse movement for the selected target.

---

## 2) Target: Core Flags

`disable_headshot`
- Excludes `class_head` from target selection.

`ignore_third_person`
- Ignores `class_third_person`.

`auto_aim`
- Enables automatic aiming when the aim condition is active.

`aim_bot_scope`
- Search radius around screen center, in pixels.

---

## 3) Smart Target Lock

`smart_target_lock`
- Keeps the current target across frames and reduces target hopping.

`target_lock_distance`
- Maximum distance for lock keep/reacquire.

`target_lock_reacquire_time`
- Time to wait after target loss before hard lock reset.

`target_switch_delay`
- Debounce for switching to another target (ms), reduces jittery switching.

---

## 4) Advanced Class Controls

`target_reference_class`
- Base class used by lock logic.

`target_lock_fallback_class`
- Backup class when reference class is lost (`-1` = disabled).

`allowed_classes`
- Allow-list of classes. Classes outside are ignored.

`class_priority_order`
- Hard class order. If set, selection starts from the first available class in this order.

`class_aim_positions`
- Per-class vertical pivot range (`pos1..pos2`).

`head -> body` example:
1. `class_head` is set to head class ID.
2. Head and body are both in `allowed_classes`.
3. `target_reference_class` = head (or head first in `class_priority_order`).
4. `target_lock_fallback_class` = body.

Result:
- head visible: lock stays on head;
- head lost: lock tries to keep target via body;
- head returns: can switch back to head (with `target_switch_delay` applied).

Important:
- if `disable_headshot=true`, head fallback/return cannot happen.

---

## 5) Target Weights

`distance_scoring_weight`
- Weight for distance to center.

`center_scoring_weight`
- Extra center-bias weight.

`size_scoring_weight`
- Bounding-box size weight.

`aim_weight_tiebreak_ratio`
- Tie-break behavior for near-equal candidates.

---

## 6) Mouse: Correction and Tracking

`snapRadius`
- Inner fast-capture zone.

`nearRadius`
- Transition zone for smoother movement.

`minSpeed`, `maxSpeed`, `speedCurveExponent`, `snapBoostFactor`
- Define speed curve toward the target.

`use_smoothing`
- Enables mouse movement smoothing.
- Recommended to keep enabled.

`use_kalman`
- Enables Kalman in mouse movement loop.
- Usually works best with `use_smoothing=true`.

`tracking_smoothing`
- Moving-target tracking mode.
- Makes tracking "stickier": faster catch-up with fewer sharp jumps.

`kalman_process_noise`
- Movement-Kalman process noise.
- Higher value: faster response, more noise sensitivity.

`kalman_measurement_noise`
- Movement-Kalman measurement noise.
- Higher value: stronger filtering, more inertia.

`kalman_speed_multiplier_x`, `kalman_speed_multiplier_y`
- Per-axis post-Kalman movement multipliers.

`camera_compensation_enabled`
- Enables camera-motion compensation in target velocity estimation.

`camera_compensation_max_shift`
- Clamp for camera delta input.

`camera_compensation_strength`
- Camera compensation strength.
- `0` almost off, `1` baseline compensation, `>1` stronger compensation.

4K note:
- `aim_bot_scope`, `snapRadius`, `nearRadius` are pixel-based, so they are typically increased for 4K vs FHD.

---

## 7) Prediction + Kalman

Important: there are two different loops.
- Prediction-Kalman: predicts future target position.
- Movement-Kalman: smooths mouse movement (section 6).

`prediction_mode`
- `0`: classic velocity.
- `1`: Kalman lead.
- `2`: Kalman + raw velocity (hybrid).

`predictionInterval`
- Base lead horizon (seconds).

`prediction_kalman_lead_ms`
- Extra lead in milliseconds.

`prediction_kalman_max_lead_ms`
- Upper cap for lead.

`prediction_velocity_smoothing`
- EMA smoothing for predicted velocity.

`prediction_velocity_scale`
- Predicted velocity multiplier.

`prediction_kalman_process_noise` (`Pred Kalman Q`)
- Prediction-Kalman process noise.

`prediction_kalman_measurement_noise` (`Pred Kalman R`)
- Prediction-Kalman measurement noise.

`prediction_use_future_for_aim`
- If enabled, aim uses the last point of future trajectory.

`prediction_futurePositions`
- Number of future trajectory points.

`draw_futurePositions`
- Draw future trajectory in debug.

`game_overlay_draw_future`
- Draw future trajectory in game overlay.

Noise summary:
- prediction: `prediction_kalman_process_noise`, `prediction_kalman_measurement_noise`.
- movement: `kalman_process_noise`, `kalman_measurement_noise`.

---

## 8) AI: NMS and Small Targets

`nms_threshold`
- Base NMS IoU threshold.

`adaptive_nms`
- Enables adaptive NMS for small boxes.
- Logic: median detection area is computed; for small boxes, threshold is increased to `min(nms_threshold * 1.5, 0.8)`.

`small_target_enhancement_enabled`
- Enables small-target boost in scoring.

`small_target_threshold`
- Relative-size threshold for "small" targets.

`small_target_boost_factor`
- Boost for very small targets.

`small_target_medium_threshold`
- Threshold for "medium-small" targets.

`small_target_medium_boost`
- Boost for medium-small targets.

`small_target_smooth_enabled`
- Enables history-based smoothing of small target pivot/size.

`small_target_smooth_frames`
- Number of history frames used for smoothing.

---

## 9) Game Overlay

`show fps counter`
- Shows FPS on game overlay.

`show latency`
- Shows latency on game overlay.

`overlay_fps_text_size`, `overlay_latency_text_size`
- Metrics text size.

Box colors:
- class `0` is always green;
- other classes are auto-assigned from palette.

---

## 10) Debug and Logs

When file logging is enabled:
- log is cleared at the start of a new session;
- console events are written to runtime log.
