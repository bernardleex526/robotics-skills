# ROS 2 Humble camera pipeline contract

## Message identity

Use canonical ROS 2 types `sensor_msgs/msg/Image` and
`sensor_msgs/msg/CameraInfo`. Record the actual topic type and publisher QoS.
`ros2 interface show` describes the message schema; it does not reveal runtime
encoding, stride, fields, timestamps or byte layout.

## Optical frames

A conventional camera optical frame uses +x right, +y down and +z forward.
Confirm the driver's documented frame and TF, rather than renaming a body frame
to look optical. Image and CameraInfo for one observation should use compatible
frame identities.

## Acquisition time

`header.stamp` should represent sensor acquisition time in the clock domain
used for fusion. Callback receipt time measures transport plus scheduling and
must not silently replace acquisition time. Check monotonicity, clock resets,
bag playback clock and hardware synchronization separately.

Synchronization skew and end-to-end latency are different:

- pairing skew compares acquisition times of related messages;
- latency compares acquisition to a defined downstream completion time.

Choose exact or approximate pairing from the sensor contract and motion budget.
Do not copy a universal millisecond threshold.

## Encoding and stride

For uncompressed `Image`, `step` is bytes per row and may include padding.
Payload length is `step * height`; minimum row bytes are width times bytes per
pixel for the declared encoding. Endianness matters for multi-byte encodings.
The bundled checker recognizes a bounded common set and fails closed on unknown
encodings.

Do not infer RGB/BGR order from appearance. Preserve encoding through image
transport and conversion. Compressed transports have a different payload
contract and must be decoded before using the offline fixture.

## CameraInfo

Check width/height, frame, distortion model and finite D/K/R/P values. Matrix
presence does not prove calibration quality. Also preserve binning and region
of interest when the live stream uses them. A calibration obtained at another
resolution, focus, lens state or rectification mode needs independent evidence.

## QoS admission

Sensor streams commonly use best-effort sensor-data QoS, but compatibility is a
publisher/subscriber contract, not a slogan. Inspect offered/requested
reliability, durability, history and depth. A visible average rate does not
prove absence of burst loss, timestamp jitter or queue latency.

## Live acceptance

Offline pass must be followed by bounded live checks for topic type/QoS,
frame/TF, monotonic acquisition stamps, pairing skew distribution, lost frames,
end-to-end latency and CPU/GPU pressure. Real-camera calibration and target
coverage remain hardware evidence.

## Primary upstream references

- [ROS 2 Humble Image message](https://docs.ros.org/en/humble/p/sensor_msgs/msg/Image.html)
- [ROS 2 Humble sensor message package](https://docs.ros.org/en/ros2_packages/humble/api/sensor_msgs/)
