# PointCloud2 byte and semantic contract

## Runtime identity

Use canonical ROS 2 type `sensor_msgs/msg/PointCloud2`. Inspect an actual
bounded message sample; interface introspection alone cannot reveal runtime
field names, offsets, units, byte order or padding.

Record:

- acquisition stamp and frame;
- height, width, point_step and row_step;
- is_bigendian and is_dense;
- every PointField name, offset, datatype and count;
- raw payload length;
- sensor/driver model and field-unit documentation.

## Datatypes and offsets

ROS PointField datatype IDs are INT8=1, UINT8=2, INT16=3, UINT16=4, INT32=5,
UINT32=6, FLOAT32=7 and FLOAT64=8. `count` is the number of values in that
field, not bytes. A field must fit entirely within `point_step`.

Do not assume XYZ are the first 12 bytes, float32, little-endian, or contiguous.
Do not assume `intensity`, `ring`, `time`, `t`, `timestamp`, `reflectivity` or
`tag` have interchangeable meanings.

## Rows and payload length

For an organized cloud, a row may have padding:

```text
minimum row bytes = width * point_step
payload bytes     = height * row_step
```

Index point `(row, column)` at
`row * row_step + column * point_step`. Ignoring row padding works for many
unorganized clouds and silently fails on valid organized data.

## Endianness and finite values

Decode multi-byte fields according to `is_bigendian`. Count points whose X, Y
and Z are all finite. A low finite ratio is evidence to investigate; the
acceptable ratio depends on the sensor representation and algorithm. `is_dense`
is a publisher assertion, not a substitute for checking values.

## Per-point time and ring

Deskew algorithms often require per-point acquisition time and sometimes a
scan/ring identity. Field names, units, epoch and reference (start/end/absolute)
are driver-specific. Declare the expected field explicitly and validate its
distribution against the driver contract. A message-level stamp cannot replace
per-point timing during motion.

## Frame and clock

The frame must describe the coordinate system of XYZ at the acquisition time.
Check TF availability at that stamp, static extrinsics, clock domain, hardware
synchronization and bag playback behavior. Receipt-time stamping can conceal
transport latency and corrupt fusion.

## Tool boundary

`scripts/check_pointcloud_contract.py` decodes bounded JSON `data_hex` without
ROS, PCL or Open3D. It validates layout and finite XYZ only. It does not prove
calibration, deskew correctness, point accuracy, returns through glass, QoS,
packet loss or scene coverage.

## Primary upstream references

- [ROS 2 Humble sensor message package](https://docs.ros.org/en/ros2_packages/humble/api/sensor_msgs/)
- [ROS 2 Humble perception_pcl](https://docs.ros.org/en/humble/p/perception_pcl/)
