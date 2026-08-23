# 05_timelapse.py — capture a photo every N seconds to /sd (or flash)
# cam-api-mcpy:32  examples/05_timelapse.py:32
# Great for plant growth, construction, sky. Use deep-sleep later if you need battery.
import time
from xiao_sense import XiaoCamera
from xiao_sense.camera import FrameSize, PixelFormat

# Pick where to save: "/sd/tl_" needs expansion board + SD, "/tl_" is internal flash
PREFIX = "/sd/tl_"   # change to "/tl_" if you have no SD
COUNT = 60           # number of photos
INTERVAL_S = 5       # seconds between shots

cam = XiaoCamera(frame_size=FrameSize.SVGA, pixel_format=PixelFormat.JPEG, jpeg_quality=84)

def on_each(i, path):
    print("[{}/{}] saved {}".format(i+1, COUNT, path))

print("starting timelapse: {} shots every {}s -> {}*.jpg".format(COUNT, INTERVAL_S, PREFIX))
paths = cam.timelapse(count=COUNT, interval_s=INTERVAL_S, prefix=PREFIX, on_capture=on_each)
print("timelapse done, saved", len(paths), "frames")
print(paths[:5], "..." if len(paths) > 5 else "")
cam.deinit()

# Turn the JPEGs into a video on your PC later:
#   ffmpeg -framerate 12 -pattern_type glob -i "tl_*.jpg" -c:v libx264 -pix_fmt yuv420p timelapse.mp4
