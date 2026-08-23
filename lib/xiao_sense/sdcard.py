# sdcard.py — mount helpers for the XIAO ESP32S3 Sense expansion board
# cam-api-mcpy:8
import os
import time

try:
    from machine import Pin, SDCard, SPI
except ImportError:
    Pin = SDCard = SPI = None  # allow import on CPython for linting

from .pins import (
    SD_SPI_SCK, SD_SPI_MOSI, SD_SPI_MISO, SD_CS_PIN,
    SD_CS_CANDIDATES, SD_SPI_SLOT, SD_MOUNT_POINT,
)

_mounted = False

def _try_mount_sdcard_spi(sck_pin, mosi_pin, miso_pin, cs_pin, mount_point, freq=20_000_000):
    sd = SDCard(slot=SD_SPI_SLOT, sck=Pin(sck_pin), mosi=Pin(mosi_pin),
                miso=Pin(miso_pin), cs=Pin(cs_pin, Pin.OUT))
    # some ports need a tiny delay after CS init
    time.sleep_ms(50) if hasattr(time, "sleep_ms") else time.sleep(0.05)
    os.mount(sd, mount_point)
    return sd

def mount(mount_point=SD_MOUNT_POINT, cs_pin=None, sck=SD_SPI_SCK, mosi=SD_SPI_MOSI,
          miso=SD_SPI_MISO, freq=20_000_000, probe_alternates=True):
    """Mount FAT microSD from the Sense expansion board.

    Tries SDCard(slot=2) SPI wiring sck/mosi/miso/cs. If ``cs_pin`` is None,
    probes SD_CS_CANDIDATES (21, ...). Returns the SDCard object on success.

    Example:
        import xiao_sense.sdcard as sd
        sd.mount()  # -> /sd ready
        open('/sd/hello.txt','w').write('hi')
    """
    global _mounted
    if SDCard is None or Pin is None:
        raise RuntimeError("machine.SDCard not available in this MicroPython build")
    if mount_point in os.listdir("/"):
        # already has an entry - check if it's mounted
        try:
            os.stat(mount_point + "/")
            _mounted = True
            return None
        except OSError:
            pass

    candidates = [cs_pin] if cs_pin is not None else list(SD_CS_CANDIDATES)
    last_err = None
    for cs in candidates:
        try:
            sd = _try_mount_sdcard_spi(sck, mosi, miso, cs, mount_point, freq=freq)
            _mounted = True
            # sanity: list root
            try:
                os.listdir(mount_point)
            except Exception:
                pass
            return sd
        except Exception as e:
            last_err = e
            # try next CS, but ensure we unmounted any partial
            try:
                os.umount(mount_point)
            except Exception:
                pass
            continue
    raise OSError("SD mount failed on CS candidates {}: {}".format(candidates, last_err))

def umount(mount_point=SD_MOUNT_POINT):
    global _mounted
    try:
        os.umount(mount_point)
        _mounted = False
    except OSError as e:
        # already unmounted
        if "ENOENT" in str(e) or "no such" in str(e).lower():
            _mounted = False
            return
        raise

def is_mounted(mount_point=SD_MOUNT_POINT):
    try:
        os.stat(mount_point)
        os.listdir(mount_point)
        return True
    except Exception:
        return False

def ensure_mounted(**kw):
    if not is_mounted(kw.get("mount_point", SD_MOUNT_POINT)):
        return mount(**kw)
    return None

def card_info(mount_point=SD_MOUNT_POINT):
    """Return (total_bytes, free_bytes) via os.statvfs if available."""
    try:
        s = os.statvfs(mount_point)
        # statvfs: f_bsize, f_frsize, f_blocks, f_bfree, ...
        bsize = s[0]
        blocks = s[2]
        bfree = s[3]
        return (blocks * bsize, bfree * bsize)
    except Exception:
        return (None, None)
