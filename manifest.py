# manifest.py — for `mpremote mip install` / `mip` frozen manifests
# cam-api-mcpy:50
# Usage (on device with internet, or via mpremote):
#   import mip; mip.install("github:your-org/cam-api-mcpy")
# Or freeze into firmware: add to boards manifest:
#   require("xiao_sense")
metadata(version="0.2.0", description="XIAO ESP32S3 Sense camera helpers")
package("xiao_sense", files=[
    "lib/xiao_sense/__init__.py",
    "lib/xiao_sense/camera.py",
    "lib/xiao_sense/pins.py",
    "lib/xiao_sense/sdcard.py",
    "lib/xiao_sense/stream.py",
    "lib/xiao_sense/utils.py",
])
