# pins.py — XIAO ESP32S3 Sense camera + expansion board SD pins
# Verified against https://wiki.seeedstudio.com/xiao_esp32s3_camera_usage/
# and cnadler86/camera_pins.h  MICROPY_CAMERA_MODEL_XIAO_ESP32S3
# cam-api-mcpy:2

# Camera DVP pins (OV2640/OV3660/OV5640 module on the Sense flex)
XCLK_PIN = 10
SIOD_PIN = 40  # SDA
SIOC_PIN = 39  # SCL
PWDN_PIN = -1  # power-down not wired on this revision
RESET_PIN = -1

Y9_PIN = 48
Y8_PIN = 11
Y7_PIN = 12
Y6_PIN = 14
Y5_PIN = 16
Y4_PIN = 18
Y3_PIN = 17
Y2_PIN = 15

VSYNC_PIN = 38
HREF_PIN = 47
PCLK_PIN = 13

# Clock & sensible defaults
XCLK_FREQ_HZ = 20_000_000
DEFAULT_JPEG_QUALITY = 85  # 0..100  (C driver maps 100->best)
DEFAULT_FB_COUNT = 2       # S3 benefits from double-buffering in JPEG mode
# Up to 20 MHz is stable on the flex; use 10 MHz if you see corruption on long wires.

# As a list matching data_pins=[D0..D7] where D0 is LSB (Y2)
DATA_PINS = [Y2_PIN, Y3_PIN, Y4_PIN, Y5_PIN, Y6_PIN, Y7_PIN, Y8_PIN, Y9_PIN]

# Expansion board microSD slot (SPI)
# Seeed docs show SD.begin(21) on Arduino — CS=21, SPI SCK/MOSI/MISO on 7/8/9
SD_SPI_SCK = 7
SD_SPI_MOSI = 9
SD_SPI_MISO = 8
SD_CS_PIN = 21
SD_SPI_SLOT = 2          # HSPI on ESP32S3 when using machine.SDCard(slot=2,...)
SD_MOUNT_POINT = "/sd"

# Optional alternate CS pins seen in community wiring (kept for sdcard auto-probe)
SD_CS_CANDIDATES = [21, 1, 2, 4]
