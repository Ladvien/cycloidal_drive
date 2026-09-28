"""
guide_scene.py - Blender side of the assembly-guide generator (runs inside Blender).

Builds the drive from geometry/build_drive.py (read-only), adds bought hardware (bearings, screws,
inserts, dowels, motor), and provides the helpers the step scripts use:
  show / rest / follow      put objects on stage (assembled pose, offsets, free layout)
  move                      record an insertion move: (objects, path offset, display offset, exemptions)
  path_check                slide each move from its start to its seat and measure collisions with
                            everything already installed - this is what catches un-assemblable designs
  fit / render / to_px      camera framing, Workbench render, 3D -> pixel projection for callouts
1 Blender unit = 1 mm (build_drive sets scale_length 0.001).
"""
import math, os, sys
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "geometry")); sys.path.insert(0, HERE)
import params as P            # noqa: E402
import build_drive as bd      # noqa: E402
from guide_style import COL, MUTED_TO, base_colour   # noqa: E402

# ------------------------------------------------------------------ colour
def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def rgba(rgb, mute=0.0):
    r = [a + (b - a) * mute for a, b in zip(rgb, MUTED_TO)]
    return (_lin(r[0]), _lin(r[1]), _lin(r[2]), 1.0)

# ------------------------------------------------------------------ mesh helpers (local, centred on the Z axis)
def _obj(name, bm, coll="reference"):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections[coll].objects.link(ob)
    return ob

def _ring(bm, r_in, r_out, z0, z1, n=96):
    """Closed annulus between r_in and r_out (r_in <= 0 gives a solid cylinder)."""
    a = np.linspace(0, 2*np.pi, n, endpoint=False)
    def loop(r, z): return [bm.verts.new((r*math.cos(t), r*math.sin(t), z)) for t in a]
    if r_in <= 0:
        b, t = loop(r_out, z0), loop(r_out, z1)
        bm.faces.new(b[::-1]); bm.faces.new(t)
        for i in range(n): bm.faces.new((b[i], b[(i+1) % n], t[(i+1) % n], t[i]))
        return
    ob_, ot, ib, it = loop(r_out, z0), loop(r_out, z1), loop(r_in, z0), loop(r_in, z1)
    for i in range(n):
        j = (i+1) % n
        bm.faces.new((ob_[i], ob_[j], ot[j], ot[i])); bm.faces.new((ib[j], ib[i], it[i], it[j]))
        bm.faces.new((ot[i], ot[j], it[j], it[i])); bm.faces.new((ob_[j], ob_[i], ib[i], ib[j]))

def _bake_bool(ob, other, op):
    m = ob.modifiers.new("b", "BOOLEAN"); m.operation = op; m.object = other; m.solver = "MANIFOLD"
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg)); ob.modifiers.clear()
    old = ob.data; ob.data = me; bpy.data.meshes.remove(old)
    bpy.data.objects.remove(other, do_unlink=True)

def make_bearing(name, d, D, B):
    """Sealed bearing, centred at origin, axis Z: steel races (one object) + black seals (child)."""
    t = min(1.2, (D - d) * 0.18)
    bm = bmesh.new(); _ring(bm, d/2, d/2 + t, -B/2, B/2); _ring(bm, D/2 - t, D/2, -B/2, B/2)
    steel = _obj(name, bm)
    bm = bmesh.new(); _ring(bm, d/2 + t - 0.01, D/2 - t + 0.01, -B/2 + 0.25, B/2 - 0.25)
    seal = _obj(name + "_seal", bm); seal.parent = steel
    return steel

def make_cyl(name, r, L, n=48):
    bm = bmesh.new(); _ring(bm, 0, r, -L/2, L/2, n); return _obj(name, bm)

def make_insert(name, size):
    s = P.SCREW[size]; L = P.INSERT_LEN[size]
    bm = bmesh.new(); _ring(bm, (s["clear"] - 0.4)/2, (s["ins_d"] + 0.6)/2, -L/2, L/2, n=24)   # 24 facets ~ knurl
    return _obj(name, bm)

def make_shcs(name, size, length):
    """Socket-head cap screw: axis Z, head toward +Z, origin at the underside of the head. One manifold solid."""
    s = P.SCREW[size]; dmaj = float(size[1:])
    bm = bmesh.new(); _ring(bm, 0, s["head_d"]/2, 0, s["head_h"], n=48); ob = _obj(name, bm)
    bm = bmesh.new(); _ring(bm, 0, dmaj/2, -length, 0.3, n=32); _bake_bool(ob, _obj(name + "_sh", bm), "UNION")
    hx = bmesh.new(); r = dmaj * 0.45; a = [math.radians(60*i) for i in range(6)]
    b = [hx.verts.new((r*math.cos(t), r*math.sin(t), s["head_h"]*0.45)) for t in a]
    tt = [hx.verts.new((r*math.cos(t), r*math.sin(t), s["head_h"] + 1)) for t in a]
    hx.faces.new(b[::-1]); hx.faces.new(tt)
    for i in range(6): hx.faces.new((b[i], b[(i+1) % 6], tt[(i+1) % 6], tt[i]))
    _bake_bool(ob, _obj(name + "_hex", hx), "DIFFERENCE")
    return ob

def _prism(name, pts, z0, z1):
    bm = bmesh.new()
    b = [bm.verts.new((x, y, z0)) for x, y in pts]; t = [bm.verts.new((x, y, z1)) for x, y in pts]
    n = len(pts); bm.faces.new(b[::-1]); bm.faces.new(t)
    for i in range(n): bm.faces.new((b[i], b[(i+1) % n], t[(i+1) % n], t[i]))
    return _obj(name, bm)

def make_motor():
    s = P.MOTOR["body"]/2; c = 4.0
    pts = [(s, -s+c), (s, s-c), (s-c, s), (-s+c, s), (-s, s-c), (-s, -s+c), (-s+c, -s), (s-c, -s)]
    _prism("HW_motor_body", pts, -40.0, -8.0); _prism("HW_motor_face", pts, -8.0, 0.0)

def make_arrow(name, p0, p1, r=0.7, head_r=1.9, head_len=4.5):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0; L = d.length
    if L < head_len + 0.5: return None
    bm = bmesh.new(); _ring(bm, 0, r, 0, L - head_len, n=24)
    a = np.linspace(0, 2*np.pi, 32, endpoint=False)
    base = [bm.verts.new((head_r*math.cos(t), head_r*math.sin(t), L - head_len)) for t in a]
    tip = bm.verts.new((0, 0, L)); bm.faces.new(base[::-1])
    for i in range(32): bm.faces.new((base[i], base[(i+1) % 32], tip))
    ob = _obj(name, bm, "arrows")
    ob.matrix_world = Matrix.Translation(p0) @ Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    ob.color = rgba(COL["arrow"]); ob.hide_render = False
    return ob

# ------------------------------------------------------------------ build
ASSEMBLED, LOCAL_CENTRE = {}, {}

def polar(r, deg): return (r*math.cos(math.radians(deg)), r*math.sin(math.radians(deg)))

def _put(ob, loc, rot=(0, 0, 0)):
    ob.matrix_world = Matrix.Translation(Vector(loc)) @ Euler(rot).to_matrix().to_4x4()

def build():
    bd.reset_scene()
    arrows = bpy.data.collections.new("arrows"); bpy.context.scene.collection.children.link(arrows)
    bd.build_P1_base(); bd.build_P2_ring(); bd.build_P3_cap()
    bd.build_disc("P4_disc_A"); bd.build_disc("P4_disc_B")
    bd.build_P5a_cam_lower(); bd.build_P5b_cam_upper(); bd.build_P6_lower_carrier(); bd.build_P7_upper_carrier()
    bd.build_reference(); bd.pose(0)
    bpy.data.objects.remove(bpy.data.objects["REF_motor"], do_unlink=True)
    bpy.data.objects["REF_motor_boss"].name = "HW_motor_boss"; bpy.data.objects["REF_shaft"].name = "HW_shaft"
    for i in range(P.N_OUT): bpy.data.objects[f"REF_out_pin_{i}"].name = f"HW_pin_out_{i}"
    for a in P.ALIGN_ANGLES: bpy.data.objects[f"REF_align_pin_{a}"].name = f"HW_pin_align_{a}"
    make_motor()
    zc = lambda z0, z1: (z0 + z1) / 2
    _put(make_bearing("HW_6802_A", P.BRG_CAM["d"], P.BRG_CAM["D"], P.BRG_CAM["B"]), (P.E, 0, zc(P.Z["discA_bot"], P.Z["discA_top"])))
    _put(make_bearing("HW_6802_B", P.BRG_CAM["d"], P.BRG_CAM["D"], P.BRG_CAM["B"]), (-P.E, 0, zc(P.Z["discB_bot"], P.Z["discB_top"])))
    _put(make_bearing("HW_6809", P.BRG_OUT["d"], P.BRG_OUT["D"], P.BRG_OUT["B"]), (0, 0, zc(P.Z["brg_out_bot"], P.Z["brg_out_top"])))
    _put(make_bearing("HW_625", P.BRG_TIP["d"], P.BRG_TIP["D"], P.BRG_TIP["B"]), (0, 0, P.Z["carrier_bot"] + P.BRG_TIP["B"]/2))
    L3 = P.INSERT_LEN["M3"]; L2 = P.INSERT_LEN["M2"]
    for a in P.BOLT_ANGLES:          _put(make_insert(f"HW_ins_P1_{a}", "M3"), (*polar(P.BOLT_PCD_R, a), P.Z["base_top"] - L3/2))
    for a in P.MOUNT_ANGLES:         _put(make_insert(f"HW_ins_P3_{a}", "M3"), (*polar(P.BOLT_PCD_R, a), P.Z["cap_top"] - L3/2))
    for a in P.CARRIER_JOIN_ANGLES:  _put(make_insert(f"HW_ins_P6_{a}", "M3"), (*polar(P.CARRIER_JOIN_R, a), P.Z["brg_out_top"] - L3/2))
    for a in P.OUTPUT_INSERT_ANGLES: _put(make_insert(f"HW_ins_P7_{a}", "M3"), (*polar(P.OUTPUT_INSERT_R, a), P.Z["output_face"] - L3/2))
    r_seat = P.CAM["collar_d"]/2 - P.SCREW["M2"]["head_h"]              # counterbore floor
    _put(make_insert("HW_ins_P5", "M2"), (0, r_seat - L2/2, P.CAM["setscrew_z"]), (math.radians(-90), 0, 0))
    size, L = P.SCREWS_USED["motor"]; h = P.MOTOR["bolt_square"]/2
    for sx in (-1, 1):
        for sy in (-1, 1):
            _put(make_shcs(f"HW_scr_motor_{'p' if sx > 0 else 'm'}{'p' if sy > 0 else 'm'}", size, L),
                 (sx*h, sy*h, P.Z["base_top"] - (P.SCREW[size]["head_h"] + 0.5)))
    size, L = P.SCREWS_USED["housing"]
    for a in P.BOLT_ANGLES:
        _put(make_shcs(f"HW_scr_housing_{a}", size, L), (*polar(P.BOLT_PCD_R, a), P.Z["cap_top"] - (P.SCREW[size]["head_h"] + P.CBORE_EXTRA_H)))
    size, L = P.SCREWS_USED["carrier"]
    for a in P.CARRIER_JOIN_ANGLES:
        _put(make_shcs(f"HW_scr_carrier_{a}", size, L), (*polar(P.CARRIER_JOIN_R, a), P.Z["output_face"] - (P.SCREW[size]["head_h"] + P.CBORE_EXTRA_H)))
    size, L = P.SCREWS_USED["set"]
    _put(make_shcs("HW_scr_set", size, L), (0, r_seat, P.CAM["setscrew_z"]), (math.radians(-90), 0, 0))
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.parent is not None: continue
        ASSEMBLED[ob.name] = ob.matrix_world.copy()
        LOCAL_CENTRE[ob.name] = sum((Vector(c) for c in ob.bound_box), Vector()) / 8

def names(prefix):
    return sorted(n for n in ASSEMBLED if n.startswith(prefix))

# ------------------------------------------------------------------ staging
MOVES = []          # [(names, path_offset Vector, exempt set, final matrices dict)]

def reset_state():
    MOVES.clear()
    for ob in bpy.data.objects:
        if ob.type != "MESH": continue
        if ob.name in ASSEMBLED: ob.matrix_world = ASSEMBLED[ob.name]
        ob.hide_render = True
    for ob in list(bpy.data.collections["arrows"].objects):
        bpy.data.objects.remove(ob, do_unlink=True)

def show(name, mute=0.0, offset=(0, 0, 0), free=None, rot=None, base=None):
    """Put `name` on stage. Default: assembled pose + offset. `base`: a 4x4 applied before the offset
    (moves a whole sub-assembly). `free`/`rot`: place the part's centre at `free`, rotated by `rot`."""
    ob = bpy.data.objects[name]; M0 = ASSEMBLED[name]
    if free is not None:
        c0 = M0 @ LOCAL_CENTRE[name]
        M = Matrix.Translation(Vector(free)) @ Euler(rot or (0, 0, 0)).to_matrix().to_4x4() @ Matrix.Translation(-c0) @ M0
    else:
        M = (base if base is not None else Matrix.Identity(4)) @ M0
    ob.matrix_world = Matrix.Translation(Vector(offset)) @ M
    ob.hide_render = False
    ob.color = rgba(base_colour(name), mute)
    for ch in ob.children:
        ch.hide_render = False; ch.color = rgba(base_colour(ch.name), mute)
    bpy.context.view_layer.update()
    return ob

def rest(name, x, y, rot=(0, 0, 0), mute=0.0, z=0.0):
    """Free-place a part so it rests on the table (z) at (x, y)."""
    ob = show(name, mute=mute, free=(x, y, 0), rot=rot)
    zmin = min((ob.matrix_world @ Vector(c)).z for c in ob.bound_box)
    ob.matrix_world = Matrix.Translation((0, 0, z - zmin)) @ ob.matrix_world
    bpy.context.view_layer.update()
    return ob

def transform_of(name):
    """The rigid move `name` has had relative to its assembled pose."""
    return bpy.data.objects[name].matrix_world @ ASSEMBLED[name].inverted()

def follow(child, parent, mute=0.0):
    """Give `child` the same rigid move its `parent` has had (keeps sub-assemblies together)."""
    return show(child, mute=mute, base=transform_of(parent))

def centre(name):
    ob = bpy.data.objects[name]; bpy.context.view_layer.update()
    return ob.matrix_world @ LOCAL_CENTRE[name]

def half_extent_along(name, d):
    ob = bpy.data.objects[name]; c = centre(name)
    return max(abs((ob.matrix_world @ Vector(k) - c).dot(d)) for k in ob.bound_box)

def move(group, path, display=None, exempt=(), arrows=None, arrow_r=None, seat_shift=(0, 0, 0)):
    """Record an insertion: objects in `group` start at seat + `path` and slide straight to where they are now
    (their seat). They are drawn at seat + `display` (default = path). Arrows are drawn for the names in
    `arrows` (default: every member if the group is small), pointing at seat + `seat_shift` (use this when the
    part they go into is itself drawn displaced)."""
    group = [group] if isinstance(group, str) else list(group)
    path = Vector(path); display = Vector(display) if display is not None else path; shift = Vector(seat_shift)
    finals = {n: bpy.data.objects[n].matrix_world.copy() for n in group}
    MOVES.append((group, path, set(exempt), finals))
    for n in group:
        bpy.data.objects[n].matrix_world = Matrix.Translation(display) @ finals[n]
    bpy.context.view_layer.update()
    gap = shift - display
    if gap.length > 0:
        d = gap.normalized()
        for n in (arrows if arrows is not None else (group if len(group) <= 8 else group[:1])):
            h = half_extent_along(n, d)
            seat_c = finals[n] @ LOCAL_CENTRE[n]
            start = seat_c + display + d*(h + 1.0)
            end = seat_c + shift - d*(h + 0.3)
            size = max(bpy.data.objects[n].dimensions)
            r = arrow_r or min(max(0.05*size, 0.5), 1.1)
            make_arrow(f"arr_{n}", start, end, r=r, head_r=r*2.7, head_len=r*6.0)
    return finals

# ------------------------------------------------------------------ assembly-path check
GLOBAL_EXEMPT = [  # (prefix a, prefix b): intended press fits / threads that overlap in the model
    ("HW_ins_", "P"),                          # heat-set inserts melt into their holes
    ("HW_pin_align", "P1_base"),               # alignment dowels are a press fit in the base
    ("HW_pin_out", "P6_carrier_lower"),        # output dowels are a press fit in the lower carrier
    ("HW_scr_motor", "HW_motor"),              # motor screws thread into the motor
    ("HW_scr_set", "HW_shaft"),                # the set screw bites the shaft
    ("HW_scr_", "HW_ins_"),                    # screws thread into their inserts
]

def _exempt(a, b, extra):
    if a in extra or b in extra: return True
    return any((a.startswith(x) and b.startswith(y)) or (b.startswith(x) and a.startswith(y)) for x, y in GLOBAL_EXEMPT)

def _aabb(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)]))

def _aabb_hit(a, b, eps=0.01):
    return all(a[0][i] < b[1][i] - eps and b[0][i] < a[1][i] - eps for i in range(3))

def overlap_volume(a, b):
    tmp = a.copy(); tmp.data = a.data.copy(); bpy.context.scene.collection.objects.link(tmp)
    m = tmp.modifiers.new("i", "BOOLEAN"); m.operation = "INTERSECT"; m.object = b; m.solver = "MANIFOLD"
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(tmp.matrix_world)
    v = abs(bm.calc_volume()); bm.free()
    bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.meshes.remove(me)
    return v

def path_check(samples=24, tol=0.05):
    """For each recorded move (in order), slide its group from start to seat and report the worst collision
    with parts already installed (everything visible that is not moving now or later in this step)."""
    shown = {ob.name: ob.matrix_world.copy() for ob in bpy.data.objects if ob.type == "MESH"}
    moving = {n for g, *_ in MOVES for n in g}
    installed = [n for n in ASSEMBLED if not bpy.data.objects[n].hide_render and n not in moving]
    for g, _, _, finals in MOVES:                       # everything to its seat first
        for n in g: bpy.data.objects[n].matrix_world = finals[n]
    results = []
    placed = list(installed)
    for g, path, extra, finals in MOVES:
        worst = (0.0, None, None, None)
        for i in range(samples + 1):
            t = 1.0 - i / samples
            for n in g: bpy.data.objects[n].matrix_world = Matrix.Translation(path * t) @ finals[n]
            bpy.context.view_layer.update()
            boxes = {n: _aabb(bpy.data.objects[n]) for n in g}
            for n in g:
                for o in placed:
                    if _exempt(n, o, extra): continue
                    ob_o = bpy.data.objects[o]
                    if not _aabb_hit(boxes[n], _aabb(ob_o)): continue
                    v = overlap_volume(bpy.data.objects[n], ob_o)
                    if v > worst[0]: worst = (v, n, o, t)
        results.append(dict(group=g, ok=worst[0] < tol, overlap_mm3=round(worst[0], 3), part=worst[1], hits=worst[2],
                            at_travel_mm=None if worst[3] is None else round(worst[3] * path.length, 1)))
        placed += g
    for n, M in shown.items(): bpy.data.objects[n].matrix_world = M
    bpy.context.view_layer.update()
    return results

# ------------------------------------------------------------------ render
def setup_render(w=1800, h=1150):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.film_transparent = True
    sh = sc.display.shading
    sh.light = "STUDIO"; sh.color_type = "OBJECT"; sh.show_cavity = True; sh.cavity_type = "BOTH"
    sh.show_object_outline = True; sh.object_outline_color = (0.05, 0.05, 0.05); sh.show_specular_highlight = True
    sc.view_settings.view_transform = "Standard"; sc.view_settings.exposure = 0.55
    if "CAM" not in bpy.data.objects:
        cd = bpy.data.cameras.new("CAM"); cd.type = "ORTHO"; cd.clip_end = 5000
        cam = bpy.data.objects.new("CAM", cd); sc.collection.objects.link(cam); sc.camera = cam

def fit(az_deg=-30, el_deg=28, margin=0.06, pad_px=(60, 60, 70, 70)):
    """Aim along (az, el) and set centre + ortho scale so every visible object fits."""
    sc = bpy.context.scene; cam = sc.camera
    az, el = math.radians(az_deg), math.radians(el_deg)
    d = Vector((-math.cos(el)*math.sin(az), -math.cos(el)*math.cos(az), math.sin(el)))
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler(); bpy.context.view_layer.update()
    R = cam.rotation_euler.to_matrix(); Ri = R.inverted()
    pts = [Ri @ (ob.matrix_world @ Vector(c)) for ob in bpy.data.objects
           if ob.type == "MESH" and not ob.hide_render for c in ob.bound_box]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]
    W, H = sc.render.resolution_x, sc.render.resolution_y
    uw, uh = W - pad_px[0] - pad_px[1], H - pad_px[2] - pad_px[3]
    mmpp = max((max(xs) - min(xs)) / uw, (max(ys) - min(ys)) / uh) * (1 + 2*margin)
    cx = (min(xs) + max(xs))/2 + (pad_px[1] - pad_px[0])/2 * mmpp
    cy = (min(ys) + max(ys))/2 + (pad_px[3] - pad_px[2])/2 * mmpp
    cam.location = R @ Vector((cx, cy, 0)) + d * 800
    cam.data.ortho_scale = mmpp * W
    bpy.context.view_layer.update()

def to_px(p):
    sc = bpy.context.scene; v = world_to_camera_view(sc, sc.camera, Vector(p))
    return (v.x * sc.render.resolution_x, (1 - v.y) * sc.render.resolution_y)

def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
