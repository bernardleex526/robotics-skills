---
name: robotics-force-control
description: Use when integrating or debugging force/torque sensors, wrench frames, gravity compensation, admittance, impedance, hybrid force-motion control, contact transitions, passivity, watchdogs, saturation, or staged force-control commissioning.
license: LICENSE.txt
---

# Robotics Force Control

## Safety Boundary

This skill analyzes logs and configuration only. Its scripts never publish a
command, switch a controller, or activate hardware. A software timeout,
trajectory cancel, or zero command is not a safety-rated protective function.

## Route by Task

| Task or symptom | Read / run |
|---|---|
| Bias, drift, noise, rate or saturation concern | `references/wrench_admission.md` and `scripts/analyze_wrench_log.py` |
| Admittance/force configuration review | `references/control_and_commissioning.md` and `scripts/check_force_config.py` |
| Contact instability or oscillation | Frames/gravity first, then latency, passivity and gains |
| Real hardware commissioning | Complete hazard analysis and independent protective measures first |

## Workflow

1. Declare F/T sensor axes, SI units, frame, acquisition timestamp, saturation,
   payload/CoG and gravity direction.
2. Export a bounded offline CSV plus manifest like
   `assets/fixtures/wrench_nominal.yaml`.
3. Run:

   ```bash
   python3 scripts/analyze_wrench_log.py wrench.yaml
   ```

4. Fix sensor/frame/gravity/timing failures before controller tuning.
5. Copy `assets/fixtures/force_config_valid.yaml`, replace every field with the
   deployed contract, and run:

   ```bash
   python3 scripts/check_force_config.py force_config.yaml
   ```

6. Use staged simulation, non-contact, compliant-contact and bounded task
   trials under an approved safety procedure. Preserve command/measured wrench,
   pose, velocity, controller state, watchdog and protective events.

## Hard Gates

- Six axes, units, frames and sign conventions are explicit.
- Gravity and payload compensation are validated before contact inference.
- Mass/damping are positive; stiffness is nonnegative; array order is fixed.
- Sensor age, control rate, filtering, slew and wrench limits are declared.
- Timeout behavior is gravity-aware; generic “disable” is not accepted for a
  gravity-loaded mechanism.

## Result Boundary

Exit `0` is offline admission, exit `1` is a configured gate failure, and exit
`2` is malformed required input. Passing does not authorize contact or motion.
