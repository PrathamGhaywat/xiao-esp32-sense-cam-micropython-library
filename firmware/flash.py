#!/usr/bin/env python3
"""flash.py — helper to flash XIAO ESP32S3 Sense camera firmware via esptool
cam-api-mcpy:45  firmware/flash.py:45
Usage:
  python firmware/flash.py --port COM3 --bin out/XIAO_ESP32S3_SENSE-camera-*.bin
  python firmware/flash.py --port /dev/ttyACM0 --bin firmware.bin
Requires: pip install esptool
"""
import argparse, subprocess, sys, glob, pathlib

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True, help="serial port e.g. COM3 or /dev/ttyACM0")
    p.add_argument("--bin", required=True, help="firmware .bin (glob allowed)")
    p.add_argument("--baud", default="460800")
    p.add_argument("--erase", action="store_true", help="erase flash first (slow)")
    args = p.parse_args()
    bins = glob.glob(args.bin)
    if not bins:
        print(f"no file matches {args.bin!r}", file=sys.stderr)
        sys.exit(1)
    bins = sorted(bins)
    bin_path = bins[-1]
    print(f"flashing {bin_path} to {args.port} @ {args.baud}")
    if args.erase:
        subprocess.check_call([sys.executable, "-m", "esptool", "--chip", "esp32s3", "--port", args.port, "erase-flash"])
    subprocess.check_call([sys.executable, "-m", "esptool", "--chip", "esp32s3", "--port", args.port, "--baud", args.baud, "write-flash", "-z", "0x0", bin_path])
    print("done — now run: mpremote connect {} run examples/00_diagnose.py".format(args.port))

if __name__ == "__main__":
    main()
