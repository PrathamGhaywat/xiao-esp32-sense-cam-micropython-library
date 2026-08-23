# 04_web_stream.py — MJPEG streaming server (view in browser)
# cam-api-mcpy:29  examples/04_web_stream.py:29
# Connect XIAO to WiFi, then open http://<ip>/ in your phone/laptop browser.
# Endpoints:  /         -> html viewer      /stream  -> MJPEG   /capture -> single JPEG
import network, time
from xiao_sense import XiaoCamera
from xiao_sense.camera import FrameSize, PixelFormat
from xiao_sense.stream import start_stream

WIFI_SSID = "YOUR_SSID"
WIFI_PASS = "YOUR_PASSWORD"

def connect_wifi(ssid, pw, timeout=12):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        print("connecting to", ssid, "...")
        sta.connect(ssid, pw)
        t0 = time.time()
        while not sta.isconnected() and time.time() - t0 < timeout:
            time.sleep(0.5)
            print(".", end="")
        print()
    if not sta.isconnected():
        raise RuntimeError("WiFi connect failed")
    print("WiFi:", sta.ifconfig())
    return sta.ifconfig()[0]

ip = connect_wifi(WIFI_SSID, WIFI_PASS)
print("open http://{}/ in your browser".format(ip))

# VGA gives ~12-25 fps in JPEG with fb_count=2; drop to QVGA if your WiFi is slow
cam = XiaoCamera(frame_size=FrameSize.VGA, pixel_format=PixelFormat.JPEG, jpeg_quality=80, fb_count=2)
print("sensor:", cam.sensor_name, cam.width, "x", cam.height)

# blocking — serves forever (Ctrl-C to stop in REPL)
start_stream(cam, port=80)
# never reached unless you stop the server
cam.deinit()
