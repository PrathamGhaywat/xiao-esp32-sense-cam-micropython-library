# 03_photo_to_sd.py — save a photo to the expansion board microSD (/sd)
# cam-api-mcpy:26  examples/03_photo_to_sd.py:26
# Requires: XIAO ESP32S3 Sense expansion board with FAT32 microSD inserted
# Wiring: SCK=7 MOSI=9 MISO=8 CS=21 (see lib/xiao_sense/pins.py)
from xiao_sense import XiaoCamera
from xiao_sense.camera import FrameSize, PixelFormat
import xiao_sense.sdcard as sd
import os, time

# 1) Mount SD (auto-probes CS=21)
try:
    sd.mount()
    print("SD mounted at /sd")
    print(os.listdir("/sd")[:10])
    total, free = sd.card_info()
    if total:
        print("SD total/free: {} / {} bytes".format(total, free))
except Exception as e:
    print("SD mount failed:", e)
    print("-> Is the expansion board attached and card FAT32?")
    raise

# 2) Capture — UXGA is the OG 1600x1200 but uses more RAM; SVGA is faster
cam = XiaoCamera(frame_size=FrameSize.UXGA, pixel_format=PixelFormat.JPEG, jpeg_quality=85)
print("sensor:", cam.sensor_name, cam.width, "x", cam.height)

# 3) Save with timestamp-ish name
stamp = int(time.time()) if hasattr(time, "time") else 0
path = "/sd/photo_{}.jpg".format(stamp)
path, n = cam.capture_to_file(path)
print("saved", path, n, "bytes")

# also demo next_filename helper to avoid overwrites
from xiao_sense.utils import next_filename
path2 = next_filename("/sd/img_", ".jpg")
cam.capture_to_file(path2)
print("saved", path2)

print("SD root now:", os.listdir("/sd")[:12])
cam.deinit()
# sd.umount()  # optional — keep mounted for next example
print("done")
