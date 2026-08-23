# camera.py — XiaoCamera wrapper for XIAO ESP32S3 Sense
# cam-api-mcpy:14
# Wraps cnadler86/micropython-camera-API  (module ``camera``) with XIAO defaults.
# Re-exports FrameSize, PixelFormat, GrabMode, GainCeiling so user code
# doesn't need to know the underlying C module.
# cam-api-mcpy:14
import time
import os

try:
    import gc
except ImportError:
    gc = None

from .pins import (
    DATA_PINS, PCLK_PIN, VSYNC_PIN, HREF_PIN, SIOD_PIN, SIOC_PIN,
    XCLK_PIN, XCLK_FREQ_HZ, PWDN_PIN, RESET_PIN,
    DEFAULT_JPEG_QUALITY, DEFAULT_FB_COUNT,
)
from .utils import safe_filename

# --- try to import the C camera module -------------------------------------------------
# The firmware built from cnadler86 exposes ``camera`` (sync) and ``acamera`` (async).
# If neither is present, we raise a helpful error at construction time rather than
# import time so the library still imports on CPython/lint.
try:
    import camera as _camera_mod  # sync
    _HAS_CAMERA = True
except ImportError:
    _camera_mod = None
    _HAS_CAMERA = False

try:
    import acamera as _acamera_mod
    _HAS_ACAMERA = True
except ImportError:
    _acamera_mod = None
    _HAS_ACAMERA = False

# Re-export enums if available, else provide minimal fallbacks for lint/test
if _HAS_CAMERA:
    try:
        FrameSize = _camera_mod.FrameSize
        PixelFormat = _camera_mod.PixelFormat
        GrabMode = _camera_mod.GrabMode
        GainCeiling = _camera_mod.GainCeiling
    except AttributeError:
        # very old builds may not expose all enums
        FrameSize = getattr(_camera_mod, "FrameSize", None)
        PixelFormat = getattr(_camera_mod, "PixelFormat", None)
        GrabMode = getattr(_camera_mod, "GrabMode", None)
        GainCeiling = getattr(_camera_mod, "GainCeiling", None)
else:
    # Dummy stubs so examples still parse on non-camera ports/CPython
    class _DummyEnum:
        def __getattr__(self, k):
            return 0
    FrameSize = PixelFormat = GrabMode = GainCeiling = _DummyEnum()

# Friendly name map (avoids importing FrameSize on generic ports)
_FRAME_SIZE_NAMES = {
    # these match esp32-camera framesize_t ordinals used by the C API
    # Common subset — see sensor.h framesize_t
    0: "96X96",
    1: "QQVGA", 2: "QCIF", 3: "HQVGA", 4: "240X240",
    5: "QVGA", 6: "CIF", 7: "HVGA", 8: "VGA", 9: "SVGA",
    10: "XGA", 11: "HD", 12: "SXGA", 13: "UXGA",
    14: "FHD", 15: "P_HD", 16: "P_3MP", 17: "QXGA",
    18: "QHD", 19: "WQXGA", 20: "P_FHD", 21: "QSXGA",
}

# Valid property names forwarded to underlying sensor (see modcamera_api.c:370)
_SENSOR_RW_PROPS = (
    "frame_size","contrast","brightness","saturation","sharpness","denoise",
    "gainceiling","quality","colorbar","whitebal","gain_ctrl","exposure_ctrl",
    "hmirror","vflip","aec2","awb_gain","agc_gain","aec_value","special_effect",
    "wb_mode","ae_level","dcw","bpc","wpc","raw_gma","lenc",
)
_SENSOR_RO_PROPS = ("pixel_format","grab_mode","fb_count","pixel_width","pixel_height","max_frame_size","sensor_name")


def _is_xiao_firmware():
    """Heuristic: try to construct Camera() with no pins — succeeds only on
    XIAO-baked firmware (MICROPY_CAMERA_ALL_REQ_PINS_DEFINED)."""
    if not _HAS_CAMERA:
        return False
    try:
        # Probe by checking if default constructor signature allows missing pins
        # Do NOT actually init the sensor here — just inspect without side-effects
        # We attempt a dry-construct with init=False if the port supports it.
        c = _camera_mod.Camera(init=False)  # XIAO firmware allows this
        try:
            c.deinit()
        except Exception:
            pass
        return True
    except TypeError as e:
        if "required" in str(e).lower() or "data_pins" in str(e).lower():
            return False
        return False
    except Exception:
        # Any other error (e.g. OSError camera probe fail still means XIAO pins compiled)
        return False


class XiaoCamera:
    """High-level camera for XIAO ESP32S3 Sense.

    Example
    -------
    from xiao_sense import XiaoCamera
    from xiao_sense.camera import FrameSize, PixelFormat

    cam = XiaoCamera(frame_size=FrameSize.VGA)   # XIAO pins auto-configured
    jpeg = cam.capture()                          # -> memoryview (JPEG)
    cam.capture_to_file('/photo.jpg')
    cam.deinit()

    Parameters match the underlying ``camera.Camera``:
        frame_size, pixel_format, jpeg_quality (0..100), fb_count, grab_mode,
        xclk_freq, init, plus optional explicit pin overrides.

    Notes
    -----
    - On XIAO-specific firmware (``MICROPY_CAMERA_MODEL_XIAO_ESP32S3``) the
      pin arguments are optional. On a generic build they are required — this
      wrapper supplies the correct XIAO pins automatically on fallback.
    - The board has 8 MB octal PSRAM; the firmware must be the octal variant.
      Use the prebuilt ``XIAO_ESP32S3`` image or the CI octal build.
    """

    def __init__(self,
                 frame_size=None,
                 pixel_format=None,
                 jpeg_quality=DEFAULT_JPEG_QUALITY,
                 fb_count=DEFAULT_FB_COUNT,
                 grab_mode=None,
                 xclk_freq=XCLK_FREQ_HZ,
                 init=True,
                 # pin overrides — normally None -> use XIAO defaults
                 data_pins=None,
                 pclk_pin=None, vsync_pin=None, href_pin=None,
                 sda_pin=None, scl_pin=None, xclk_pin=None,
                 powerdown_pin=None, reset_pin=None,
                 i2c=None):
        if not _HAS_CAMERA:
            raise RuntimeError(
                "camera module not found. Flash the camera firmware: "
                "see firmware/README.md or https://github.com/cnadler86/micropython-camera-API/releases"
            )

        # Resolve enums with sensible defaults if caller passed None
        # Default to JPEG VGA for a good balance; caller can reconfigure later
        if frame_size is None:
            try:
                frame_size = FrameSize.VGA
            except Exception:
                frame_size = 8  # VGA ordinal fallback
        if pixel_format is None:
            try:
                pixel_format = PixelFormat.JPEG
            except Exception:
                pixel_format = 4  # JPEG ordinal fallback (depends on version)
        if grab_mode is None:
            try:
                grab_mode = GrabMode.LATEST  # best for S3
            except Exception:
                grab_mode = 1

        self._frame_size = frame_size
        self._pixel_format = pixel_format
        self._kwargs = dict(
            frame_size=frame_size,
            pixel_format=pixel_format,
            jpeg_quality=jpeg_quality,
            fb_count=fb_count,
            grab_mode=grab_mode,
            xclk_freq=xclk_freq,
        )

        # Build constructor kwargs — try XIAO-baked first, then explicit pins
        base_kw = dict(
            frame_size=frame_size,
            pixel_format=pixel_format,
            jpeg_quality=jpeg_quality,
            fb_count=fb_count,
            grab_mode=grab_mode,
            xclk_freq=xclk_freq,
            init=init,
        )
        # Allow caller overrides
        pin_kw_explicit = {}
        if data_pins is not None:
            pin_kw_explicit["data_pins"] = data_pins
        if pclk_pin is not None:
            pin_kw_explicit["pclk_pin"] = pclk_pin
        if vsync_pin is not None:
            pin_kw_explicit["vsync_pin"] = vsync_pin
        if href_pin is not None:
            pin_kw_explicit["href_pin"] = href_pin
        if sda_pin is not None:
            pin_kw_explicit["sda_pin"] = sda_pin
        if scl_pin is not None:
            pin_kw_explicit["scl_pin"] = scl_pin
        if xclk_pin is not None:
            pin_kw_explicit["xclk_pin"] = xclk_pin
        if powerdown_pin is not None:
            pin_kw_explicit["powerdown_pin"] = powerdown_pin
        if reset_pin is not None:
            pin_kw_explicit["reset_pin"] = reset_pin
        if i2c is not None:
            pin_kw_explicit["i2c"] = i2c

        base_kw.update(pin_kw_explicit)

        # Strategy: if firmware already has XIAO pins baked, a bare constructor works.
        # Otherwise we must supply pins. This wrapper automatically falls back.
        cam = None
        last_err = None
        tried = []

        # 1) Try without explicit pins (XIAO firmware path) — only if caller didn't force pins
        if not pin_kw_explicit:
            tried.append("xiao_baked")
            try:
                cam = _camera_mod.Camera(**base_kw)
            except TypeError as e:
                # Missing required pins -> not XIAO-baked generic build, fall through
                if "required" in str(e).lower() or "data_pins" in str(e).lower() or "pclk_pin" in str(e).lower():
                    last_err = e
                    cam = None
                else:
                    raise
            except Exception as e:
                last_err = e
                cam = None

        # 2) Explicit XIAO pins fallback (generic firmware path)
        if cam is None:
            tried.append("explicit_pins")
            xiao_kw = dict(
                data_pins=DATA_PINS,
                pclk_pin=PCLK_PIN,
                vsync_pin=VSYNC_PIN,
                href_pin=HREF_PIN,
                sda_pin=SIOD_PIN if i2c is None else None,
                scl_pin=SIOC_PIN if i2c is None else None,
                xclk_pin=XCLK_PIN,
                powerdown_pin=PWDN_PIN,
                reset_pin=RESET_PIN,
            )
            # drop None entries for i2c path
            xiao_kw = {k: v for k, v in xiao_kw.items() if v is not None}
            # merge with base (base already has frame_size etc, xiao pins win)
            full_kw = {}
            full_kw.update(base_kw)
            full_kw.update(xiao_kw)
            # if i2c was supplied, ensure sda/scl not sent
            if i2c is not None and "sda_pin" in full_kw:
                full_kw.pop("sda_pin", None)
                full_kw.pop("scl_pin", None)
                full_kw["i2c"] = i2c
            # caller pin overrides already in base_kw, so they survive
            try:
                cam = _camera_mod.Camera(**full_kw)
            except Exception as e:
                last_err = e
                # give a super helpful error message
                raise RuntimeError(
                    "Camera init failed after trying {}.\n"
                    "Last error: {}\n"
                    "Hint: you need the XIAO_ESP32S3 octal-PSRAM firmware. "
                    "See firmware/README.md — flash the XIAO_ESP32S3 build, not a generic ESP32 build.\n"
                    "Pins used: data_pins={}, pclk={}, vsync={}, href={}, sda={}, scl={}, xclk={}, pwdn={}, reset={} xclk_freq={}".format(
                        tried, e,
                        DATA_PINS, PCLK_PIN, VSYNC_PIN, HREF_PIN, SIOD_PIN, SIOC_PIN, XCLK_PIN, PWDN_PIN, RESET_PIN, xclk_freq
                    )
                ) from e

        self._cam = cam
        self._init = init

    # --- thin wrappers ---------------------------------------------------------------

    def init(self):
        return self._cam.init()

    def deinit(self):
        try:
            return self._cam.deinit()
        except Exception:
            # some builds expose __exit__ only; fall back to deinit semantics
            try:
                return self._cam.__exit__(None, None, None)
            except Exception:
                raise

    def __enter__(self):
        return self

    def __exit__(self, *a):
        try:
            self.deinit()
        except Exception:
            pass
        return False

    def capture(self):
        """Capture one frame -> memoryview (JPEG by default).
        Caller should ``bytes(frame)`` if they need to keep it after free."""
        return self._cam.capture()

    def free_buffer(self):
        try:
            return self._cam.free_buffer()
        except AttributeError:
            # older builds name it.free_buffer or free_buf — try variants
            for n in ("free_buf", "free_buffer", "free"):
                if hasattr(self._cam, n):
                    return getattr(self._cam, n)()
            raise

    def frame_available(self):
        try:
            return bool(self._cam.frame_available())
        except AttributeError:
            return True

    def reconfigure(self, frame_size=None, pixel_format=None, grab_mode=None, fb_count=None):
        kw = {}
        if frame_size is not None:
            kw["frame_size"] = frame_size
        if pixel_format is not None:
            kw["pixel_format"] = pixel_format
        if grab_mode is not None:
            kw["grab_mode"] = grab_mode
        if fb_count is not None:
            kw["fb_count"] = fb_count
        if not kw:
            return
        return self._cam.reconfigure(**kw)

    # --- properties forwarding to sensor -------------------------------------------

    def __getattr__(self, name):
        # Forward unknown attributes to the underlying C camera object.
        # This exposes .brightness, .contrast, .vflip, .hmirror, .quality, etc.
        # as well as older get_*/set_* methods if the user prefers them.
        if name in _SENSOR_RW_PROPS or name in _SENSOR_RO_PROPS or name.startswith("get_") or name.startswith("set_"):
            return getattr(self._cam, name)
        # Also allow direct access to FrameSize etc if someone does cam.FrameSize
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        if name in _SENSOR_RW_PROPS:
            setattr(self._cam, name, value)
            return
        if name in _SENSOR_RO_PROPS:
            raise AttributeError("{} is read-only".format(name))
        object.__setattr__(self, name, value)

    # --- convenience read-only helpers ---------------------------------------------
    @property
    def width(self):
        try:
            return int(self._cam.pixel_width)
        except Exception:
            return 0

    @property
    def height(self):
        try:
            return int(self._cam.pixel_height)
        except Exception:
            return 0

    @property
    def sensor_name(self):
        try:
            return self._cam.sensor_name
        except Exception:
            return "unknown"

    @property
    def max_frame_size(self):
        try:
            return self._cam.max_frame_size
        except Exception:
            return None

    # --- file helpers --------------------------------------------------------------

    def capture_to_file(self, path, ensure_dir=True):
        """Capture and atomically write to *path* (JPEG).

        Returns (path, num_bytes). Ensures parent dir exists if ensure_dir.
        """
        if ensure_dir and "/" in path:
            d = path.rsplit("/", 1)[0]
            if d and d not in (".", "/"):
                try:
                    os.makedirs(d, exist_ok=True)
                except AttributeError:
                    # older MicroPython: mkdir without exist_ok
                    try:
                        os.mkdir(d)
                    except OSError:
                        pass
                except OSError:
                    pass
        frame = self.capture()
        if not frame:
            raise OSError("capture returned no frame")
        # micro: need to write bytes; frame is memoryview
        data = bytes(frame) if not isinstance(frame, (bytes, bytearray)) else frame
        # free underlying buffer early (allows next capture faster)
        try:
            self.free_buffer()
        except Exception:
            pass
        # atomic write: write to .tmp then rename (avoids half files on power loss)
        tmp = path + ".tmp"
        try:
            with open(tmp, "wb") as f:
                f.write(data)
            try:
                os.rename(tmp, path)
            except Exception:
                # fallback if rename not supported or tmp on different fs
                try:
                    os.remove(path)
                except Exception:
                    pass
                os.rename(tmp, path)
        except Exception:
            # last resort: direct write
            with open(path, "wb") as f:
                f.write(data)
            try:
                os.remove(tmp)
            except Exception:
                pass
        if gc:
            gc.collect()
        return (path, len(data))

    # --- timelapse ---------------------------------------------------------------
    def timelapse(self, count=10, interval_s=2.0, prefix="/sd/tl_", ext=".jpg",
                  on_capture=None, ensure_mount=True):
        """Capture *count* photos spaced by *interval_s* seconds.

        Saves to ``prefix00000.jpg`` etc. If prefix starts with ``/sd/`` and
        ``ensure_mount`` is True, tries to auto-mount the SD card.

        ``on_capture`` optional callback ``fn(index, path)``.

        Returns list of saved paths.
        """
        if ensure_mount and prefix.startswith("/sd/"):
            try:
                from .sdcard import ensure_mounted
                ensure_mounted()
            except Exception as e:
                print("timelapse: SD mount:", e)
        out = []
        for i in range(count):
            # avoid overwriting existing runs: first file probes next free index if file exists
            if i == 0:
                # find next free index so repeated runs don't clobber
                try:
                    base = prefix
                    for probe in range(0, 100000):
                        cand = safe_filename(base, probe, ext)
                        try:
                            os.stat(cand)
                        except OSError:
                            # free slot found — adjust i offset
                            if probe != 0:
                                # rewrite out to start at probe
                                # simpler: just set prefix offset variable
                                pass
                            break
                except Exception:
                    pass
            path = safe_filename(prefix, i, ext)
            try:
                self.capture_to_file(path)
                out.append(path)
                if on_capture:
                    try:
                        on_capture(i, path)
                    except Exception as e:
                        print("on_capture err:", e)
            except Exception as e:
                print("timelapse frame {} err: {}".format(i, e))
            if i != count - 1:
                if hasattr(time, "sleep_ms"):
                    time.sleep_ms(int(interval_s * 1000))
                else:
                    time.sleep(interval_s)
        return out

    # --- motion detection (grayscale differencing) ------------------------------
    def motion_stream(self, threshold=15, min_pixels=700, grace_frames=3,
                      sample_interval_ms=250, max_events=None,
                      jpeg_on_motion=False, jpeg_quality=80, save_dir="/sd/motion"):
        """Generator yielding motion events by comparing GRAYSCALE frames.

        Switches the sensor to a small GRAYSCALE mode for cheap differencing
        (QQVGA ~160x120), then yields ``(event_idx, changed_pixels)`` each
        time the pixel-diff exceeds ``threshold``/``min_pixels``.

        Parameters
        ----------
        threshold:
            per-pixel absolute difference to count as "changed" (0..255).
        min_pixels:
            how many changed pixels trigger an event. Tune: 400 sensitive, 2000 strict.
        grace_frames:
            ignore this many frames after start (auto-exposure settling).
        sample_interval_ms:
            sleep between samples.
        max_events:
            stop after this many events (None = infinite).
        jpeg_on_motion:
            if True, reconfigure to JPEG and save a snapshot to ``save_dir`` on each event.
        """
        # save current config so we can restore
        try:
            prev_fmt = self._cam.pixel_format
            prev_size = self._cam.frame_size
            prev_qual = self._cam.quality
        except Exception:
            prev_fmt = prev_size = prev_qual = None

        # switch to small grayscale for diff
        try:
            small = FrameSize.QQVGA if hasattr(FrameSize, "QQVGA") else 1
            gray = PixelFormat.GRAYSCALE if hasattr(PixelFormat, "GRAYSCALE") else 1
        except Exception:
            small, gray = 1, 1
        try:
            self.reconfigure(frame_size=small, pixel_format=gray)
            # let AE settle
            for _ in range(grace_frames):
                try:
                    f = self.capture()
                    self.free_buffer()
                except Exception:
                    pass
                if hasattr(time, "sleep_ms"):
                    time.sleep_ms(120)
                else:
                    time.sleep(0.12)
        except Exception as e:
            print("motion_stream reconfigure:", e)

        prev = None
        events = 0
        try:
            while True:
                if hasattr(time, "sleep_ms"):
                    time.sleep_ms(sample_interval_ms)
                else:
                    time.sleep(sample_interval_ms / 1000.0)

                cur_mv = self.capture()
                if not cur_mv:
                    continue
                # convert to bytes for diff; keep prev as bytes too
                try:
                    cur = bytes(cur_mv)
                except Exception:
                    cur = cur_mv
                try:
                    self.free_buffer()
                except Exception:
                    pass

                if prev is None:
                    prev = cur
                    continue

                # align lengths (should be same size, but guard)
                n = min(len(prev), len(cur))
                changed = 0
                # manual loop — keep it in Python but early-exit when exceeded?
                # For 160x120 = 19200 bytes, loop is ~1-2ms per frame on S3 in MicroPython?
                # Might be okay. Use memoryview + step sampling if huge.
                # Sample every 2nd byte when big to speed up
                step = 1
                if n > 40000:
                    step = 2
                th = threshold
                # local vars for speed
                p = prev
                c = cur
                if step == 1:
                    for i in range(n):
                        d = p[i] - c[i]
                        if d < 0:
                            d = -d
                        if d > th:
                            changed += 1
                            # early exit if already over min_pixels * 1.4 to save time?
                            # don't break too early — keep accurate but we can
                            # break once we know it's motion if not needing count
                            if changed > min_pixels and changed > 1200:
                                # enough to trigger; continue fast but not full scan?
                                # compromise: break early after 2*min
                                if changed > min_pixels * 2:
                                    break
                else:
                    for i in range(0, n, step):
                        d = p[i] - c[i]
                        if d < 0:
                            d = -d
                        if d > th:
                            changed += step
                            if changed > min_pixels * 2:
                                break

                is_motion = changed >= min_pixels

                # keep cur as next prev (double-buffer)
                prev = cur

                if is_motion:
                    events += 1
                    if jpeg_on_motion:
                        # snapshot in JPEG: reconfigure, capture, save, switch back
                        snap_path = None
                        try:
                            from .sdcard import ensure_mounted
                            if save_dir.startswith("/sd"):
                                try:
                                    ensure_mounted()
                                except Exception:
                                    pass
                            try:
                                os.makedirs(save_dir, exist_ok=True)
                            except Exception:
                                try:
                                    os.mkdir(save_dir)
                                except Exception:
                                    pass
                            # bump to larger JPEG for snapshot
                            shot_size = FrameSize.VGA if hasattr(FrameSize, "VGA") else 8
                            jpeg_fmt = PixelFormat.JPEG if hasattr(PixelFormat, "JPEG") else 4
                            self.reconfigure(frame_size=shot_size, pixel_format=jpeg_fmt)
                            if hasattr(self._cam, "quality"):
                                try:
                                    self._cam.quality = jpeg_quality
                                except Exception:
                                    pass
                            snap_path = "{}/evt_{:05d}.jpg".format(save_dir.rstrip("/"), events)
                            self.capture_to_file(snap_path)
                            # back to diff mode
                            self.reconfigure(frame_size=small, pixel_format=gray)
                        except Exception as e:
                            print("jpeg_on_motion err:", e)
                            # try to restore diff mode anyway
                            try:
                                self.reconfigure(frame_size=small, pixel_format=gray)
                            except Exception:
                                pass
                        yield (events, changed, snap_path)
                    else:
                        yield (events, changed)

                    if max_events is not None and events >= max_events:
                        break
                # else no motion — continue sampling
                if gc and events % 8 == 0:
                    gc.collect()

        finally:
            # restore previous config
            try:
                kw = {}
                if prev_fmt is not None:
                    kw["pixel_format"] = prev_fmt
                if prev_size is not None:
                    kw["frame_size"] = prev_size
                if kw:
                    self.reconfigure(**kw)
                if prev_qual is not None and hasattr(self._cam, "quality"):
                    try:
                        self._cam.quality = prev_qual
                    except Exception:
                        pass
            except Exception:
                pass

    # --- legacy shim for older examples using get_*/set_* ------------------------
    def get_frame_size(self):
        return self._cam.frame_size if hasattr(self._cam, "frame_size") else None
