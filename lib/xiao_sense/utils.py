# utils.py — small helpers that have no hardware dependency
# cam-api-mcpy:5
import time

try:
    from micropython import const
except ImportError:
    def const(x):
        return x

def _ticks_ms():
    try:
        return time.ticks_ms()  # micropython
    except AttributeError:
        return int(time.time() * 1000)

def _ticks_diff(a, b):
    try:
        return time.ticks_diff(a, b)
    except AttributeError:
        return a - b

def safe_filename(prefix, idx, ext=".jpg"):
    # zero-padded so ls sorts correctly: prefix00001.jpg
    return "{}{:05d}{}".format(prefix, idx, ext)

def free_mem():
    try:
        import gc
        gc.collect()
        return gc.mem_free()
    except Exception:
        return -1

def next_filename(prefix="/sd/img_", ext=".jpg", start=0):
    # avoid overwriting: probe existing files
    import os
    for i in range(start, 100000):
        p = safe_filename(prefix, i, ext)
        try:
            os.stat(p)
        except OSError:
            return p
    return safe_filename(prefix, start, ext)
