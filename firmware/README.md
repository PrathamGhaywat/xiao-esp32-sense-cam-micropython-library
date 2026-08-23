# Firmware — XIAO ESP32S3 Sense + MicroPython + Camera

The **XIAO ESP32S3 Sense** has 8 MB **octal** PSRAM (`ESP32-S3R8`). Stock MicroPython
has no camera driver, and a generic `ESP32_GENERIC_S3` build with **quad** PSRAM
will fail to enable PSRAM — the camera then has nowhere to put the framebuffer.

You need a build with **`MICROPY_CAMERA_MODEL_XIAO_ESP32S3`** and
`CONFIG_SPIRAM_MODE_OCT`. This repo gives you two ways to get it.

## Option A — Prebuilt (recommended, no toolchain)

Download the latest `XIAO_ESP32S3_SENSE` `camera` build from the upstream
**micropython-camera-API** releases:

**https://github.com/cnadler86/micropython-camera-API/releases**

Pick the file whose name contains **XIAO_ESP32S3** and a recent MicroPython
version (≥1.24). If you only see a `GENERIC_S3-SPIRAM_OCT` file, that also works —
its pins must be passed from Python, but `lib/xiao_sense` does that for you.

### Flash via browser (easiest)

1. Open **https://esp.huhn.me/** in Chrome/Edge.
2. Connect — pick your `USB JTAG/serial debug unit` (CP210x is the old XIAO,
   JTAG is the S3).
3. Choose the downloaded `.bin` -> **Flash**.

### Flash via esptool (Windows/macOS/Linux)

```bash
pip install esptool
esptool --chip esp32s3 --port COM3 --baud 460800 write-flash -z 0x0 XIAO_ESP32S3_SENSE-camera-*.bin
# Tip: use --port /dev/ttyACM0 on Linux,  --port COM3 on Windows
# Find the port:  esptool --chip esp32s3 flash-id   or check Device Manager
```

First boot takes a few seconds (FS format). Then in `mpremote`:

```
mpremote connect COM3
>>> import camera; print(camera.Version())
>>> from xiao_sense import XiaoCamera; cam=XiaoCamera(); print(cam.sensor_name)
```

If you see `OSError: Failed to capture initial frame` -> wrong firmware variant,
bad flex cable, or unsupported sensor. Try reseating the camera and flashing the
octal build.

## Option B — CI build (no local toolchain either)

This repo ships `.github/workflows/build.yml`. It builds the same octal firmware
**in the cloud** using `espressif/idf:v5.2.3`.

1. Push a tag:

```bash
git tag v0.2.0
git push origin v0.2.0
```

2. GitHub Actions -> **Build XIAO Sense firmware** -> downloads as artifact
   and, on tags, creates a Release with the `.bin`.

You never need to install ESP-IDF/WSL locally.

## Option C — Local build (only if you want it)

```bash
# Inside WSL2 / Linux / Docker:
git clone --recursive https://github.com/micropython/micropython
git clone https://github.com/cnadler86/micropython-camera-API  # user C module
git clone https://github.com/your-org/cam-api-mcpy              # this repo
cd micropython/ports/esp32
# add esp32-camera as required by the user module (see micropython-camera-API build.sh)
# then:
./path/to/micropython-camera-API/build.sh -m ../.. -b ESP32_GENERIC_S3 -v SPIRAM_OCT \
  --camera-model XIAO_ESP32S3 --extra-modules ../../../cam-api-mcpy/lib
# or build via Docker: docker run --rm -v $PWD:/project espressif/idf:v5.2.3 ...
```

See upstream `build.sh -h` for options. Add `-o` to include `mp_jpeg` for JPEG decode.

## Verifying the build

```python
import esp, os, gc
print(os.uname())
print(gc.mem_free())
import camera
print(camera.Version())
from xiao_sense import XiaoCamera
cam = XiaoCamera()  # should succeed without manual pins
print(cam.sensor_name, cam.width, cam.height)
buf = cam.capture(); print(len(buf)); cam.deinit()
```

## Troubleshooting

- `camera module not found` -> not the camera build. Reflash the `-camera-` file.
- `No PSRAM` in boot log -> you flashed the quad build on octal hardware. Use XIAO octal.
- `Camera probe failed` -> SDA/SCL swapped? Flex not seated. Try XCLK 10 MHz.
- Brownout -> use powered USB hub; camera + WiFi spikes >500 mA.
