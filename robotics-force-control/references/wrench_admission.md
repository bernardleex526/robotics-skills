# Wrench sensor admission

## Interfaces and units

Record the six-axis order `[Fx, Fy, Fz, Tx, Ty, Tz]`, force in N, torque in
N*m, and the frame in which the wrench is expressed. Verify sensor sign against
known loads. A frame rotation changes both force and torque; a reference-point
translation also changes torque through the moment arm.

For ROS 2 Humble, `geometry_msgs/msg/WrenchStamped` carries a frame and stamp.
`force_torque_sensor_broadcaster` can expose semantic components, but interface
names and ordering remain hardware/configuration contracts.

## Timestamp and rate

Use sensor acquisition time when available. Check strictly monotonic stamps,
clock resets, message age, jitter and loss. Average sample rate is not control
loop timing or worst-case age. Preserve raw timestamps in logs.

## Bias, noise and drift

Measure a known unloaded/static condition across relevant warmup and
temperature. Report per-axis mean, RMS about the mean and linear drift slope.
Bias removal is valid only for the payload, orientation and gravity-compensation
stage in which it was identified.

The bundled analyzer computes descriptive values and applies only declared
gates. It does not infer contact from a single force threshold.

## Saturation and clipping

Use sensor/ADC limits in the declared axes and units. Count samples at or beyond
limits and retain them. Clipped data cannot support accurate force estimates,
even if the controller remains stable. Investigate overload, range selection,
amplifier settings, payload and collision.

## Gravity and payload

A tool-mounted sensor observes payload gravity as orientation changes. Record
payload mass, center of gravity, sensor-to-control transform and gravity vector.
Validate compensated wrench across multiple static orientations. Wrong frame,
mass or CoG can look like contact and destabilize force control.

## Filtering

Record filter type, cutoff, sample rate, order and phase/group delay. Filtering
noise trades bandwidth and phase margin; no universal cutoff fits all
mechanisms. Avoid applying undocumented filters in both driver and controller.

## Tool boundary

`scripts/analyze_wrench_log.py` reads a bounded CSV through a YAML contract. It
reports rate, monotonicity, bias, RMS, drift and saturation. It cannot validate
sensor calibration, cross-axis coupling, dynamic load, aliasing, TF at runtime,
contact state or protective functions.
