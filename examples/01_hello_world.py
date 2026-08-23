# 01_hello_world.py — minimal capture, print image info
# cam-api-mcpy:20  examples/01_hello_world.py:20
# Copy to board and run:  mpremote run examples/01_hello_world.py
from xiao_sense import XiaoCamera
from xiao_sense.camera import FrameSize, PixelFormat

# XIAO pins are automatic; VGA JPEG is a safe default (needs PSRAM octal firmware)
cam = XiaoCamera(frame_size=FrameSize.VGA, pixel_format=PixelFormat.JPEG, jpeg_quality=85)

print("sensor:", cam.sensor_name, "size:", cam.width, "x", cam.height)
print("free mem:", __import__("gc").mem_free() if hasattr(__import__("gc"), "mem_free") else "n/a")

frame = cam.capture()  # memoryview of JPEG bytes
print("captured", len(frame), "bytes")
# keep a copy if you want to process it after free_buffer
data = bytes(frame)
cam.free_buffer()
print("copied", len(data), "bytes, first 2 bytes JPEG SOI:", hex(data[0]), hex(data[1]))

# quick sanity: JPEG should start with FF D8
assert data[0] == 0xFF and data[1] == 0xD8, "not a JPEG — check pixel_format=JPEG"

cam.deinit()
print("done — try 02_photo_to_flash.py next")
