"""
render_stage.py - Blender half of the guide generator. Run by make_guide.py as:
    blender --background --factory-startup --python guide/render_stage.py -- --out <dir> [--steps k1 k2 ...]
Writes <out>/raw/NN_key.png (transparent renders) and <out>/manifest.json (callout pixels + path checks).
"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import guide_scene as G      # noqa: E402  (imports bpy + geometry/build_drive)
import guide_text as T       # noqa: E402

def main(argv):
    out = argv[argv.index("--out") + 1]
    keys = argv[argv.index("--steps") + 1:] if "--steps" in argv else T.KEYS
    raw = os.path.join(out, "raw"); os.makedirs(raw, exist_ok=True)
    t0 = time.time()
    G.build(); G.setup_render()
    import guide_steps as GS     # after build(): it looks up part names in the scene
    mpath = os.path.join(out, "manifest.json")
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {"steps": {}}   # partial runs update the cache
    manifest["blender"] = __import__("bpy").app.version_string
    for key in keys:
        G.reset_state()
        calls, cam = GS.SCENES[key]()
        checks = [] if key in GS.LAYOUT_STEPS else G.path_check()
        G.fit(cam.get("az", -30), cam.get("el", 28), cam.get("margin", 0.06), cam.get("pad", (60, 60, 70, 70)))
        png = os.path.join(raw, f"{T.NUM[key]:02d}_{key}.png")
        G.render(png)
        manifest["steps"][key] = dict(raw=os.path.relpath(png, out),
                                      callouts=[dict(px=G.to_px(p), text=txt, offset=off) for p, txt, off in calls],
                                      path_checks=checks)
        bad = [c for c in checks if not c["ok"]]
        print(f"[render] {T.NUM[key]:2d} {key:14s} moves={len(checks)} "
              + ("path OK" if not bad else "PATH BLOCKED: " + "; ".join(f"{c['part']} hits {c['hits']} ({c['overlap_mm3']} mm3)" for c in bad)),
              flush=True)
    # positive control: the old one-piece cam must be reported as un-assemblable
    G.reset_state(); GS.control_one_piece_cam(); ctl = G.path_check()
    caught = any(not c["ok"] for c in ctl)
    manifest["positive_control"] = dict(caught=caught, checks=ctl)
    print("[render] positive control (one-piece cam): " + ("caught, path checker works" if caught else "NOT CAUGHT - path checker is broken"), flush=True)
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"[render] done in {time.time() - t0:.0f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
