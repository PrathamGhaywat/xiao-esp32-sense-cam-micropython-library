# 06_motion_detection.py — cheap motion detection via GRAYSCALE differencing
# cam-api-mcpy:35  examples/06_motion_detection.py:35
# No ML model needed. Good for: door alert, wildlife trigger, time-lapse gate.
# The library switches to QQVGA GRAYSCALE for diffing, then optionally snaps a
# higher-res JPEG when motion is seen.
from xiao_sense import XiaoCamera
from xiao_sense.camera import FrameSize, PixelFormat
import time, os

cam = XiaoCamera(frame_size=FrameSize.QQVGA, pixel_format=PixelFormat.GRAYSCALE)

print("sensor:", cam.sensor_name, "motion threshold demo")
print("wiring: if you use SD snapshots, have expansion board + FAT32 card inserted")

# Tune these:
#  threshold  = per-pixel brightness change to count (12 sensitive, 25 strict)
#  min_pixels = how many changed pixels = motion (400 very sensitive, 2000 needs big object)
#  sample_interval_ms slows the loop and saves power

threshold = 14
min_pixels = 900

print("monitoring — move in front of camera or wave your hand")
print("Ctrl-C to stop")

try:
    for evt, changed, snap in cam.motion_stream(
        threshold=threshold,
        min_pixels=min_pixels,
        sample_interval_ms=300,
        jpeg_on_motion=True,          # save a VGA JPEG to /sd/motion/ on each event
        save_dir="/sd/motion",
        max_events=10):                # stop after 10 events for this demo

        print("MOTION #{} changed={} -> {}".format(evt, changed, snap))
        # you could also ring a buzzer, send MQTT, etc here

except KeyboardInterrupt:
    print("stopped by user")

cam.deinit()
print("saved events in /sd/motion/:")
try:
    print(os.listdir("/sd/motion")[:10])
except Exception:
    pass
