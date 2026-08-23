# stream.py — tiny MJPEG HTTP server for MicroPython + XiaoCamera
# cam-api-mcpy:11
import socket
import time

_HTML = """<!DOCTYPE html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>XIAO Sense Camera</title>
<style>
 body{font-family:system-ui,sans-serif;background:#0f1115;color:#e6e6e6;display:flex;flex-direction:column;align-items:center;margin:0;padding:24px}
 .card{background:#181b22;border-radius:16px;padding:16px 20px;box-shadow:0 8px 24px rgba(0,0,0,.4);max-width:780px;width:100%}
 img{width:100%;border-radius:12px;background:#000;min-height:240px}
 a{color:#7ab4ff}code{background:#222632;padding:2px 6px;border-radius:6px}
 .row{display:flex;gap:12px;flex-wrap:wrap;margin-top:12px}
 .btn{padding:8px 12px;border-radius:10px;background:#2a2f3f;color:#fff;text-decoration:none}
</style>
</head><body>
 <div class='card'>
  <h2 style='margin:4px 0 8px'>XIAO ESP32S3 Sense — Live</h2>
  <img src='/stream' alt='mjpeg stream'>
  <div class='row'>
   <a class='btn' href='/stream'>/stream</a>
   <a class='btn' href='/capture'>/capture (single JPEG)</a>
   <a class='btn' href='/' onclick='location.reload();return false'>Reload</a>
  </div>
  <p>Tip: lower <code>frame_size</code> or set <code>jpeg_quality=80</code> if you see tearing.</p>
 </div>
</body></html>
"""

def _send_all(sock, data):
    if isinstance(data, str):
        data = data.encode()
    # MicroPython socket may not have sendall
    try:
        sock.sendall(data)
    except AttributeError:
        mv = memoryview(data)
        off = 0
        while off < len(mv):
            n = sock.send(mv[off:])
            if not n:
                break
            off += n

def _handle_stream(conn, cam):
    # ensure camera is up
    try:
        cam.init()
    except Exception:
        pass
    hdr = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n"
        "Cache-Control: no-cache\r\n"
        "Connection: close\r\n\r\n"
    )
    _send_all(conn, hdr)
    # stream loop
    while True:
        try:
            frame = cam.capture()
            if not frame:
                time.sleep_ms(50) if hasattr(time, "sleep_ms") else time.sleep(0.05)
                continue
            # handle both memoryview and bytes
            header = (
                "--frame\r\n"
                "Content-Type: image/jpeg\r\n"
                "Content-Length: {}\r\n\r\n".format(len(frame))
            )
            _send_all(conn, header)
            _send_all(conn, frame)
            _send_all(conn, b"\r\n")
            # optional pacing
            # don't keep buffer forever on fb_count=1
            try:
                cam.free_buffer()
            except Exception:
                pass
        except OSError:
            break
        except Exception as e:
            try:
                print("stream err:", e)
            except Exception:
                pass
            break

def _handle_capture(conn, cam):
    try:
        cam.init()
    except Exception:
        pass
    try:
        frame = cam.capture()
        if not frame:
            _send_all(conn, "HTTP/1.1 500 No frame\r\nConnection: close\r\n\r\n")
            return
        hdr = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: image/jpeg\r\n"
            "Content-Length: {}\r\n"
            "Cache-Control: no-cache\r\n"
            "Connection: close\r\n\r\n".format(len(frame))
        )
        _send_all(conn, hdr)
        _send_all(conn, frame)
        try:
            cam.free_buffer()
        except Exception:
            pass
    except Exception as e:
        _send_all(conn, "HTTP/1.1 500 {}\r\nConnection: close\r\n\r\n".format(e))

def _handle_root(conn):
    body = _HTML.encode()
    hdr = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "Content-Length: {}\r\n"
        "Connection: close\r\n\r\n".format(len(body))
    )
    _send_all(conn, hdr)
    _send_all(conn, body)

def start_stream(cam, host="0.0.0.0", port=80, backlog=2, timeout=30):
    """Blocking MJPEG server. Visit http://<board-ip>/ or /stream or /capture.

    Example:
        cam = XiaoCamera(frame_size=FrameSize.VGA)
        start_stream(cam)  # never returns

    For non-blocking use, run in a separate thread (if _thread available) or
    call ``handle_one_client`` manually (see below).
    """
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except Exception:
        pass
    s.bind(addr)
    s.listen(backlog)
    # disable nagle if available
    print("XIAO stream on http://{}:{}/  (/stream, /capture)".format(_ip(), port))
    print("Press Ctrl-C to stop")
    while True:
        try:
            conn, caddr = s.accept()
            try:
                conn.settimeout(timeout)
            except Exception:
                pass
            print("client", caddr)
            try:
                req = conn.recv(1024)
                if not req:
                    conn.close()
                    continue
                req_s = req.decode("utf-8", "ignore") if isinstance(req, bytes) else str(req)
                first = req_s.split("\r\n", 1)[0] if "\r\n" in req_s else req_s.split("\n",1)[0]
                if "GET /stream" in req_s:
                    _handle_stream(conn, cam)
                elif "GET /capture" in req_s:
                    _handle_capture(conn, cam)
                else:
                    _handle_root(conn)
            except Exception as e:
                try:
                    print("client err:", e)
                except Exception:
                    pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        except KeyboardInterrupt:
            print("stream stopped")
            break
        except Exception as e:
            try:
                print("accept err:", e)
                time.sleep_ms(200) if hasattr(time, "sleep_ms") else time.sleep(0.2)
            except Exception:
                pass
    try:
        s.close()
    except Exception:
        pass

def _ip():
    try:
        import network
        sta = network.WLAN(network.STA_IF)
        if sta.isconnected():
            return sta.ifconfig()[0]
        ap = network.WLAN(network.AP_IF)
        if ap.active():
            return ap.ifconfig()[0]
    except Exception:
        pass
    return "0.0.0.0"
