# 07_sensor_tuning.py — tweak sensor properties live
# cam-api-mcpy:38  examples/07_sensor_tuning.py:38
# All properties mirror circuitpython/espcamera docs.
# See README "Properties" or Thonny autocomplete for full list.
from xiao_sense import XiaoCamera
from xiao_sense.camera import FrameSize, PixelFormat
import time, os

cam = XiaoCamera(frame_size=FrameSize.VGA, pixel_format=PixelFormat.JPEG, jpeg_quality=85)

print("sensor:", cam.sensor_name)
print("max_frame_size:", cam.max_frame_size)
print("before: brightness", cam.brightness, "contrast", cam.contrast, "saturation", cam.saturation)

# --- demo: change properties via assignment (preferred) --------------------------
cam.brightness = 1      # -2 .. 2
cam.contrast = 1        # -2 .. 2
cam.saturation = -1     # -2 .. 2
cam.hmirror = False
cam.vflip = False       # lens is mounted flipped on some Sense batches
cam.quality = 82        # 0..100 (maps internally to 63..0)

# Some settings only take effect after a new frame — grab one
cam.capture()
print("after:  brightness", cam.brightness, "quality", cam.quality)

# --- save 3 photos with different exposures -----------------------------------
for ev in (-1, 0, 1):
    cam.ae_level = ev
    time.sleep(0.5)  # let AEC settle
    p, n = cam.capture_to_file("/tune_ev{}.jpg".format(ev))
    print("saved", p, n, "ae_level", ev)

# --- reconfigure resolution on the fly ---------------------------------------
for fs_name, fs in [("QVGA", FrameSize.QVGA), ("VGA", FrameSize.VGA), ("SVGA", FrameSize.SVGA)]:
    try:
        cam.reconfigure(frame_size=fs)
        print("reconfigured to", fs_name, "->", cam.width, "x", cam.height)
        cam.capture_to_file("/tune_{}.jpg".format(fs_name))
    except Exception as e:
        print("reconfigure", fs_name, "err:", e)

# old get_/set_ API still works but is deprecated:
#   cam.get_brightness() / cam.set_brightness(1)

cam.deinit()
print("check flash:", [f for f in os.listdir("/") if f.startswith("tune_")])
print("tip: open CameraSettings example via xiao_sense.stream for a browser UI")
