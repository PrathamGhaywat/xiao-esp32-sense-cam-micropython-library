# tools/check.py — quick CPython lint/sanity for the lib (no hardware needed)
# cam-api-mcpy:53
import py_compile, pathlib, sys
root = pathlib.Path(__file__).resolve().parents[1]
ok = True
for p in (root / "lib" / "xiao_sense").rglob("*.py"):
    try:
        py_compile.compile(str(p), doraise=True)
        print(f"[ok] {p.relative_to(root)}")
    except Exception as e:
        print(f"[FAIL] {p.relative_to(root)}: {e}")
        ok = False
for p in (root / "examples").rglob("*.py"):
    try:
        py_compile.compile(str(p), doraise=True)
        print(f"[ok] {p.relative_to(root)}")
    except Exception as e:
        print(f"[FAIL] {p.relative_to(root)}: {e}")
        ok = False
sys.exit(0 if ok else 1)
