# xiao_sense — MicroPython camera helpers for Seeed XIAO ESP32S3 Sense
# cam-api-mcpy:2  lib/xiao_sense/__init__.py:2
"""Convenience package.

from xiao_sense import XiaoCamera
from xiao_sense.camera import FrameSize, PixelFormat, GrabMode

cam = XiaoCamera(frame_size=FrameSize.VGA)
jpeg = cam.capture()
cam.capture_to_file('/sd/photo.jpg')
cam.deinit()
"""
from .camera import XiaoCamera, FrameSize, PixelFormat, GrabMode, GainCeiling
from . import pins as pins  # so user can do xiao_sense.pins.SD_CS_PIN
from . import sdcard as sdcard
from . import stream as stream

__all__ = ["XiaoCamera", "FrameSize", "PixelFormat", "GrabMode", "GainCeiling", "pins", "sdcard", "stream"]

try:
    __version__ = "0.2.0"
except Exception:
    pass
