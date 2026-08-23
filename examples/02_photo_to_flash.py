# 02_photo_to_flash.py — capture JPEG to internal flash (/photo.jpg)
# cam-api-mcpy:23  examples/02_photo_to_flash.py:23
# Run: mpremote run examples/02_photo_to_flash.py  then  mpremote ls :  or download the file
from xiao_sense import XiaoCamera
from xiao_sense.camera import FrameSize, PixelFormat
import os

cam = XiaoCamera(frame_size=FrameSize.SVGA, pixel_format=PixelFormat.JPEG, jpeg_quality=88)

# capture_to_file handles .tmp atomic write + gc
path, n = cam.capture_to_file("/photo.jpg")
print("saved", path, n, "bytes")

# also show how to save several with incrementing names
for i in range(2):
    p, _ = cam.capture_to_file("/photo_{}.jpg".format(i))
    print("saved", p)

print("flash contents:")
try:
    print(os.listdir("/"))
except Exception as e:
    print(e)

cam.deinit()
print("tip: download with  mpremote cp :photo.jpg ./photo.jpg")
