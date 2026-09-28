#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "reportlab"]
# ///
"""
make_guide.py - regenerate the illustrated assembly guide (PDF + markdown) from the current design.

    python3 guide/make_guide.py                 # full guide -> docs/assembly/
    python3 guide/make_guide.py --steps disc1 cam_upper     # re-render just some steps (for proofing)
    uv run guide/make_guide.py                  # same, with Pillow/reportlab installed on the fly

What it does:
  1. runs Blender in the background (render_stage.py): builds every part from geometry/build_drive.py,
     stages each step, SLIDES EVERY PART ALONG ITS INSERTION PATH to check it can actually be assembled,
     and renders one image per step
  2. draws the callouts and lays out the pages (compose_stage.py), writing
        docs/assembly/<date>-cycloidal-drive-assembly-guide.pdf
        docs/assembly/<date>-cycloidal-drive-assembly-guide.md
        docs/assembly/img/step-NN-<key>.png
Exit code 1 if any step's assembly path is blocked (the page also carries a red warning).

To change the guide: words live in guide_text.py (numbers come from geometry/params.py), scenes and
callouts in guide_steps.py, colours in guide_style.py. Blender: --blender PATH or $BLENDER, else the
macOS app, else `blender` on PATH, else an importable `bpy` module.
"""
import argparse, datetime, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

def find_blender(explicit):
    for c in (explicit, os.environ.get("BLENDER"), "/Applications/Blender.app/Contents/MacOS/Blender", shutil.which("blender")):
        if c and os.path.exists(c): return [c, "--background", "--factory-startup", "--python"]
    try:
        import importlib.util
        if importlib.util.find_spec("bpy"): return [sys.executable]
    except Exception: pass
    sys.exit("Blender not found: pass --blender /path/to/Blender or set $BLENDER")

def git_commit():
    try:
        r = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "geometry", "guide"], capture_output=True, text=True, timeout=10)
        return (r.stdout.strip() + ("+dirty" if dirty.stdout.strip() else "")) if r.returncode == 0 else None
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--steps", nargs="*", help="step keys to render (default: all); see guide_text.KEYS")
    ap.add_argument("--out", default=os.path.join(REPO, "docs", "assembly"))
    ap.add_argument("--build", default=os.path.join(HERE, "_build"), help="scratch dir for raw renders")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--blender")
    ap.add_argument("--skip-render", action="store_true", help="re-compose from the last renders")
    ap.add_argument("--no-cover", action="store_true")
    a = ap.parse_args()

    import guide_text as T
    keys = a.steps or T.KEYS
    unknown = [k for k in keys if k not in T.KEYS]
    if unknown: sys.exit(f"unknown step keys {unknown}; valid: {T.KEYS}")
    os.makedirs(a.build, exist_ok=True)
    if not a.skip_render:
        cmd = find_blender(a.blender) + [os.path.join(HERE, "render_stage.py"), "--", "--out", a.build, "--steps", *keys]
        print("[guide] rendering with", cmd[0], flush=True)
        r = subprocess.run(cmd, cwd=REPO)
        if r.returncode != 0: sys.exit(f"render stage failed ({r.returncode})")

    import json
    man = json.load(open(os.path.join(a.build, "manifest.json")))
    if not man.get("positive_control", {}).get("caught", False):
        sys.exit("[guide] the path checker failed its positive control (one-piece cam not caught) - results not trustworthy")
    import compose_stage as C
    stem = f"{a.date}-cycloidal-drive-assembly-guide" if not a.steps else f"{a.date}-assembly-guide-proof"
    pdf, md, blocked = C.compose(a.build, a.out, stem, dict(date=a.date, commit=git_commit(), only=a.steps), cover_page=not a.no_cover)
    print(f"[guide] wrote {os.path.relpath(pdf, REPO)}\n[guide] wrote {os.path.relpath(md, REPO)}")
    if blocked:
        for k, v in blocked.items():
            for x in v: print(f"[guide] BLOCKED step {T.NUM[k]} ({k}): {x['part']} collides with {x['hits']} ({x['overlap_mm3']} mm3)")
        sys.exit(1)
    print("[guide] every assembly path is clear")

if __name__ == "__main__":
    main()
