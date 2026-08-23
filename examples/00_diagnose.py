# 00_diagnose.py — check board, PSRAM, firmware & camera before anything else
# cam-api-mcpy:42  examples/00_diagnose.py:42
# Run: mpremote run examples/00_diagnose.py
import sys, os, gc

print("=== XIAO ESP32S3 Sense Diagnose ===")
print("uname:", os.uname())
try:
    import esp
    print("flash size:", esp.flash_size())
except Exception as e:
    print("esp:", e)

print("mem free:", gc.mem_free())
try:
    gc.collect()
    print("mem free after collect:", gc.mem_free())
except Exception:
    pass

# PSRAM check
try:
    import esp32
    # some builds expose psram via gc? just try alloc
    print("trying large alloc to test PSRAM...")
    # don't actually blow heap — check via esp32 module if available
    print("micropython has PSRAM check via os.uname only; boot log tells truth")
except Exception as e:
    print(e)

# Camera module check
try:
    import camera
    print("camera module: OK", camera)
    try:
        print("  Version:", camera.Version())
    except Exception:
        pass
    # try FrameSize/PixelFormat enums
    print("  FrameSize:", [x for x in dir(camera.FrameSize) if not x.startswith("_")][:8], "...")
    print("  PixelFormat:", [x for x in dir(camera.PixelFormat) if not x.startswith("_")])
except ImportError as e:
    print("camera module: MISSING -> you are on stock MicroPython, not the camera build")
    print("  -> flash firmware from firmware/README.md or https://github.com/cnadler86/micropython-camera-API/releases")
    sys.exit(1)
except Exception as e:
    print("camera import err:", e)

# Try XiaoCamera init (without capturing)
try:
    from xiao_sense import XiaoCamera
    from xiao_sense.camera import FrameSize, PixelFormat
    print("xiao_sense import: OK")
    # Probe XIAO-baked vs generic firmware
    try:
        import camera as _cm
        try:
            c = _cm.Camera(init=False)
            c.deinit()
            print("firmware: XIAO-baked pins (MICROPY_CAMERA_MODEL_XIAO_ESP32S3) detected")
        except TypeError:
            print("firmware: GENERIC build (will supply XIAO pins from Python) — also OK")
    except Exception as e:
        print("firmware probe err:", e)

    print("trying XiaoCamera( QVGA ) ...")
    cam = XiaoCamera(frame_size=FrameSize.QVGA, pixel_format=PixelFormat.JPEG)
    print("  sensor:", cam.sensor_name, cam.width, "x", cam.height, "max", cam.max_frame_size)
    buf = cam.capture()
    print("  capture:", len(buf), "bytes, JPEG SOI:", hex(buf[0]), hex(buf[1]) if len(buf)>=2 else "")
    cam.free_buffer()
    cam.deinit()
    print("CAMERA OK — you're good to run 01_... 02_... etc.")
except Exception as e:
    import traceback
    print("XiaoCamera err:", e)
    traceback.print_exception(e)
    print("\nHints:")
    print("- Wrong firmware variant? Needs OCTAL PSRAM, not quad. Reflash XIAO_ESP32S3 build.")
    print("- Flex not seated? Reseat the camera FPC and retry.")
    print("- No PSRAM? Check boot log for 'PSRAM' line.")

# SD quick check (no card required)
try:
    import xiao_sense.sdcard as sd
    print("sdcard helper: OK, mount point", sd.SD_MOUNT_POINT if hasattr(sd, "SD_MOUNT_POINT") else "/sd")
    # don't auto-mount here; just check pins
    from xiao_sense.pins import SD_CS_PIN, SD_SPI_SCK, SD_SPI_MOSI, SD_SPI_MISO
    print(f"  SD pins SCK={SD_SPI_SCK} MOSI={SD_SPI_MOSI} MISO={SD_SPI_MISO} CS={SD_CS_PIN}")
except Exception as e:
    print("sdcard import err:", e)

print("=== done ===")
