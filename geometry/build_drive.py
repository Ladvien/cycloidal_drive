"""
build_drive.py - reference bpy build of the NEMA17 cycloidal drive (tested on Blender 5.0.1).

Run:  blender --background --python build_drive.py -- <out_dir>
  or: python build_drive.py <out_dir>        (with the `bpy` pip module)

Builds every printed part in ASSEMBLY position in collection "drive", reference hardware in
"reference", runs the checks in section 4 of the spec, writes <out_dir>/cycloidal_drive.blend
and one STL per part (in print orientation) to <out_dir>/stl/.
"""
import math, os, sys
import bpy, bmesh
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from params import *                       # noqa
import cycloid_geom as cg

# ============================================================== 0. scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    us = bpy.context.scene.unit_settings
    us.system, us.length_unit, us.scale_length = "METRIC", "MILLIMETERS", 0.001   # 1 BU = 1 mm
    for name in ("drive", "reference", "cutters"):
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)

def coll(name):
    return bpy.data.collections[name]

# ============================================================== 1. primitive helpers
def _obj_from_bm(name, bm, collection="cutters"):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    coll(collection).objects.link(ob)
    return ob

def prism(name, pts, z0, z1, collection="cutters"):
    """Extrude a closed CCW 2D polyline (Nx2) from z0 to z1."""
    bm = bmesh.new()
    vs = [bm.verts.new((float(x), float(y), z0)) for x, y in pts]
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    top = [v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=top, vec=(0, 0, z1 - z0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj_from_bm(name, bm, collection)

def circle_pts(r, segs, cx=0.0, cy=0.0, circumscribe=True):
    """n-gon whose FLATS sit at radius r when circumscribe=True (holes print true to size)."""
    R = r / math.cos(math.pi/segs) if circumscribe else r
    a = np.linspace(0, 2*np.pi, segs, endpoint=False)
    return np.c_[cx + R*np.cos(a), cy + R*np.sin(a)]

def cyl(name, d, z0, z1, cx=0.0, cy=0.0, segs=None, hole=True, collection="cutters"):
    """Cylinder along Z. hole=True -> circumscribed (for holes); False -> inscribed vertices on d/2 (for shafts)."""
    segs = segs or (CIRC_SEGS["small"] if d < 8 else CIRC_SEGS["medium"] if d < 30 else CIRC_SEGS["large"])
    return prism(name, circle_pts(d/2, segs, cx, cy, circumscribe=hole), z0, z1, collection)

def polar(r, deg):
    return r*math.cos(math.radians(deg)), r*math.sin(math.radians(deg))

def box(name, x0, x1, y0, y1, z0, z1):
    return prism(name, np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]), z0, z1)

# ============================================================== 2. boolean helpers
def _bake(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear(); ob.data = me
    bpy.data.meshes.remove(old)

def _join(objs, name):
    bm = bmesh.new()
    for o in objs:
        bm.from_mesh(o.data)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    return _obj_from_bm(name, bm)

def boolean(target, cutters, op="DIFFERENCE"):
    """Apply the boolean with each cutter in turn, then delete the cutters.
    Solver: MANIFOLD (Blender >= 4.5) - fast and exact for closed meshes; falls back to EXACT."""
    if not isinstance(cutters, (list, tuple)):
        cutters = [cutters]
    for c in cutters:
        m = target.modifiers.new("bool", "BOOLEAN")
        m.operation, m.object = op, c
        try:
            m.solver = "MANIFOLD"
        except TypeError:
            m.solver = "EXACT"
        _bake(target)
        bpy.data.objects.remove(c, do_unlink=True)
    return target

def finish(ob, name):
    ob.name = ob.data.name = name
    coll("cutters").objects.unlink(ob)
    coll("drive").objects.link(ob)
    return ob

# ============================================================== 3. parts (built in ASSEMBLY position)
S3, S2 = SCREW["M3"], SCREW["M2"]
hc = FIT["hole_comp"]

def build_P1_base():
    z0, z1 = Z["base_bot"], Z["base_top"]
    b = cyl("P1", HOUSING_OD, z0, z1, hole=False)
    cut = [cyl("pilot", MOTOR["boss_d"] + 0.4 + hc, z0 - 1, Z["pilot_top"]),
           cyl("bore", BASE_BORE_D + hc, z0 - 1, z1 + 1)]
    h = MOTOR["bolt_square"]/2
    for sx in (-1, 1):
        for sy in (-1, 1):
            cut += [cyl("m_clr", S3["clear"] + hc, z0 - 1, z1 + 1, sx*h, sy*h),
                    cyl("m_cb", S3["head_d"] + CBORE_EXTRA_D + hc, z1 - (S3["head_h"] + 0.5), z1 + 1, sx*h, sy*h)]
    for a in BOLT_ANGLES:
        cut.append(cyl("ins", S3["ins_d"], z1 - S3["ins_depth"], z1 + 1, *polar(BOLT_PCD_R, a)))
    for a in ALIGN_ANGLES:
        cut.append(cyl("dwl", FIT["dowel_press"], z0 - 1, z1 + 1, *polar(BOLT_PCD_R, a)))
    return finish(boolean(b, cut), "P1_base")

def _apply_rot(ob):
    ob.data.transform(ob.matrix_basis); ob.matrix_basis.identity()

def build_P2_ring():
    z0, z1 = Z["ring_bot"], Z["ring_top"]
    b = cyl("P2", HOUSING_OD, z0, z1, hole=False)
    cut = [prism("pinzone", cg.ring_inner_profile(N_PINS, R_PIN, RP, E, C_PROF, C_WALL), z0 - 1, Z["pinzone_top"]),
           cyl("upper_bore", 52.0 + hc, Z["pinzone_top"] - 0.01, z1 + 1)]
    cut += [cyl("bolt", S3["clear"] + hc, z0 - 1, z1 + 1, *polar(BOLT_PCD_R, a)) for a in BOLT_ANGLES]
    cut += [cyl("dwl", FIT["dowel_slip"], z0 - 1, z1 + 1, *polar(BOLT_PCD_R, a)) for a in ALIGN_ANGLES]
    return finish(boolean(b, cut), "P2_ring")

def build_P3_cap():
    z0, z1 = Z["cap_bot"], Z["cap_top"]
    b = cyl("P3", HOUSING_OD, z0, z1, hole=False)
    cut = [cyl("brg", BRG_OUT["D"] + FIT["bearing_press"], z0 - 1, Z["cap_lip_bot"]),
           cyl("lip", 52.0 + hc, Z["cap_lip_bot"] - 0.01, z1 + 1)]
    for a in BOLT_ANGLES:
        cut += [cyl("bolt", S3["clear"] + hc, z0 - 1, z1 + 1, *polar(BOLT_PCD_R, a)),
                cyl("cb", S3["head_d"] + CBORE_EXTRA_D + hc, z1 - (S3["head_h"] + CBORE_EXTRA_H), z1 + 1, *polar(BOLT_PCD_R, a))]
    cut += [cyl("dwl", FIT["dowel_slip"], z0 - 1, z1 + 1, *polar(BOLT_PCD_R, a)) for a in ALIGN_ANGLES]
    cut += [cyl("mnt", S3["ins_d"], z1 - S3["ins_depth"], z1 + 1, *polar(BOLT_PCD_R, a)) for a in MOUNT_ANGLES]
    return finish(boolean(b, cut), "P3_cap")

def build_disc(name):
    """Built at z=0..5, centred on its own axis; placed by pose()."""
    t = BRG_CAM["B"]
    b = prism(name, cg.disc_profile(N_PINS, R_PIN, RP, E, C_PROF), 0, t)
    cut = [cyl("brg", BRG_CAM["D"] + FIT["bearing_press"], -1, t + 1)]
    cut += [cyl("out", OUT_HOLE_D + hc, -1, t + 1, *polar(R_OUT, 360/N_OUT*i)) for i in range(N_OUT)]
    cut.append(cyl("mark", 1.2, t - 0.4, t + 1, *polar(19.8, 30)))     # orientation dimple, top face
    return finish(boolean(b, cut), name)

def _cam_bore(z0, z1):
    """Cutters for the cam bore over z0..z1: round below the motor's D-flat, D-shaped where the flat exists.
    Both use the same 160-gon so the round and D sections share vertices (no sliver faces where they meet)."""
    z_flat = Z["base_bot"] + MOTOR["shaft_len"] - MOTOR["flat_len"] + 0.5
    r = (CAM["bore_d"] + hc)/2; f = CAM["flat_from_axis"]
    circ = circle_pts(r, 160)                     # circumscribed circle ...
    dpts = circ.copy(); dpts[:, 1] = np.minimum(dpts[:, 1], f)   # ... with the +Y side cut flat at the D-flat
    cut = []
    if z0 < z_flat:
        cut.append(prism("bore_round", circ, z0 - 1, z_flat))
    cut.append(prism("bore_D", dpts, max(z0 - 1, z_flat), z1 + 1))
    return cut

def build_P5a_cam_lower():
    """Lower cam: collar (set screw) + lobe A. A one-piece cam cannot be assembled: disc A's 6802 would be
    trapped between the collar and the spacer, both wider than its 15 mm bore. Split at z = discA_top."""
    lob = CAM["lobe_d"] + FIT["shaft_press"]
    cam = cyl("collar", CAM["collar_d"], Z["cam_bot"], Z["cam_collar_top"], hole=False)
    boolean(cam, [cyl("lobeA", lob, Z["discA_bot"] - 0.01, Z["discA_top"], E, 0, hole=False)], "UNION")
    cut = _cam_bore(Z["cam_bot"], Z["discA_top"])
    # radial M2 insert from r=0 outward + head counterbore so an M2x5 SHCS seats at r=7 and reaches the shaft
    r_seat = CAM["collar_d"]/2 - S2["head_h"]
    for nm, d, r0, r1 in (("ss_ins", S2["ins_d"], 0.0, CAM["collar_d"]/2 + 1),
                          ("ss_cb", S2["head_d"] + CBORE_EXTRA_D, r_seat, CAM["collar_d"]/2 + 1)):
        c = cyl(nm, d, r0, r1, hole=True)
        c.rotation_euler = (math.radians(-90), 0, math.radians(CAM["setscrew_angle"] - 90)); _apply_rot(c)
        c.location.z = CAM["setscrew_z"]; c.data.transform(c.matrix_basis); c.matrix_basis.identity()
        cut.append(c)
    return finish(boolean(cam, cut), "P5a_cam_lower")

def build_P5b_cam_upper():
    """Upper cam: spacer + lobe B, keyed to the shaft's D-flat (so lobe B is automatically 180 deg from lobe A).
    Goes on after disc A; the spacer rests on lobe A and separates the two 6802 inner races."""
    lob = CAM["lobe_d"] + FIT["shaft_press"]
    cam = cyl("spacer", CAM["spacer_d"], Z["discA_top"], Z["cam_spacer_top"], hole=False)
    boolean(cam, [cyl("lobeB", lob, Z["discB_bot"] - 0.01, Z["discB_top"], -E, 0, hole=False)], "UNION")
    return finish(boolean(cam, _cam_bore(Z["discA_top"], Z["discB_top"])), "P5b_cam_upper")

def build_P6_lower_carrier():
    b = cyl("P6", 48.0, Z["carrier_bot"], Z["shoulder_top"], hole=False)
    boolean(b, [cyl("seat", BRG_OUT["d"] + FIT["shaft_press"], Z["shoulder_top"] - 0.01, Z["brg_out_top"], hole=False)], "UNION")
    cut = [cyl("tip", BRG_TIP["D"] + FIT["bearing_press"], Z["carrier_bot"] - 1, Z["tip_pocket_top"]),
           cyl("tip_relief", 8.0, Z["tip_pocket_top"] - 0.01, Z["tip_pocket_top"] + 1.0)]
    cut += [cyl("pin", FIT["dowel_press"], Z["carrier_bot"] - 1, Z["brg_out_top"] + 1, *polar(R_OUT, 360/N_OUT*i)) for i in range(N_OUT)]
    cut += [cyl("ins", S3["ins_d"], Z["brg_out_top"] - S3["ins_depth"], Z["brg_out_top"] + 1, *polar(CARRIER_JOIN_R, a)) for a in CARRIER_JOIN_ANGLES]
    return finish(boolean(b, cut), "P6_carrier_lower")

def build_P7_upper_carrier():
    b = cyl("P7", 49.0, Z["ucar_bot"], Z["flange_bot"], hole=False)
    boolean(b, [cyl("flange", 56.0, Z["flange_bot"] - 0.01, Z["output_face"], hole=False)], "UNION")
    zt = Z["output_face"]
    cut = [cyl("pin", FIT["dowel_slip"], Z["ucar_bot"] - 1, zt + 1, *polar(R_OUT, 360/N_OUT*i)) for i in range(N_OUT)]
    for a in CARRIER_JOIN_ANGLES:
        cut += [cyl("clr", S3["clear"] + hc, Z["ucar_bot"] - 1, zt + 1, *polar(CARRIER_JOIN_R, a)),
                cyl("cb", S3["head_d"] + CBORE_EXTRA_D + hc, zt - (S3["head_h"] + CBORE_EXTRA_H), zt + 1, *polar(CARRIER_JOIN_R, a))]
    cut += [cyl("ins", S3["ins_d"], zt - S3["ins_depth"], zt + 1, *polar(OUTPUT_INSERT_R, a)) for a in OUTPUT_INSERT_ANGLES]
    return finish(boolean(b, cut), "P7_carrier_upper")

def build_P0_coupon():
    """Tolerance coupon: print this FIRST, test-fit real parts, then set FIT/SCREW values in params.py.
    Back row: bearing seats 23.9/24.0/24.1 and 15.9/16.0/16.1 (5 deep). Front row, left to right: dowel 2.90-3.20, M3 insert 3.9-4.1, M2 insert 3.1-3.3, cam bore 5.10. Dowel, insert and clearance holes (through / insert depth)."""
    b = box("P0", -75, 75, -20, 22, 0, 6.0)
    cut = []
    for x, d in zip((-60, -34, -8), (23.9, 24.0, 24.1)):              # 6802 OD 24, 5 deep
        cut.append(cyl("s", d, 1.0, 7, x, 8))
    for x, d in zip((16, 36, 56), (15.9, 16.0, 16.1)):                # 625 OD 16, 5 deep
        cut.append(cyl("s", d, 1.0, 7, x, 8))
    x = -66
    for d in (2.90, 2.95, 3.00, 3.05, 3.10, 3.20):                    # dowel press / slip, through
        cut.append(cyl("h", d, -1, 7, x, -12)); x += 6
    for d in (3.9, 4.0, 4.1):                                         # M3 insert
        cut.append(cyl("h", d, 6 - SCREW["M3"]["ins_depth"] + 0.5, 7, x, -12)); x += 8
    for d in (3.1, 3.2, 3.3):                                         # M2 insert
        cut.append(cyl("h", d, 6 - SCREW["M2"]["ins_depth"], 7, x, -12)); x += 7
    cut.append(cyl("h", 5.10, -1, 7, x + 2, -12))                     # cam bore slip test on the motor shaft
    ob = finish(boolean(b, cut), "P0_coupon")
    ob.location.x = 150                                   # keep it away from the assembly
    return ob

# ============================================================== reference hardware (never exported)
def ref(ob, name):
    ob.name = name; coll("cutters").objects.unlink(ob); coll("reference").objects.link(ob); return ob

def build_reference():
    m = MOTOR
    ref(box("motor", -m["body"]/2, m["body"]/2, -m["body"]/2, m["body"]/2, -40, 0), "REF_motor")
    ref(cyl("boss", m["boss_d"], 0, m["boss_h"], hole=False), "REF_motor_boss")
    zf = m["shaft_len"] - m["flat_len"]
    sh = cyl("shaft", m["shaft_d"] - 0.02, 0, zf + 0.01, hole=False)
    dp = circle_pts((m["shaft_d"] - 0.02)/2, 96, circumscribe=False)
    dp[:, 1] = np.minimum(dp[:, 1], m["shaft_flat"] - m["shaft_d"]/2)      # D-flat on +Y, same side as the cam's flat
    boolean(sh, [prism("shaftD", dp, zf, m["shaft_len"])], "UNION")
    ref(sh, "REF_shaft")
    for i in range(N_OUT):
        ref(cyl("pin", DOWEL["d"], Z["discA_bot"], Z["discA_bot"] + DOWEL["L"], *polar(R_OUT, 360/N_OUT*i), hole=False), f"REF_out_pin_{i}")
    for a in ALIGN_ANGLES:
        ref(cyl("dwl", DOWEL["d"], 0, DOWEL["L"], *polar(BOLT_PCD_R, a), hole=False), f"REF_align_pin_{a}")

# ============================================================== pose (kinematics)
def pose(theta_deg):
    """Place moving parts for motor angle theta. Cam turns +theta, discs orbit, carrier turns -theta/15."""
    th = math.radians(theta_deg)
    for nm, ph, zb in (("P4_disc_A", 0.0, Z["discA_bot"]), ("P4_disc_B", math.pi, Z["discB_bot"])):
        (cx, cy), rot = cg.disc_pose(th, E, N_PINS, ph)
        ob = bpy.data.objects[nm]; ob.location = (cx, cy, zb); ob.rotation_euler = (0, 0, rot)
    for nm in ("P5a_cam_lower", "P5b_cam_upper"):
        bpy.data.objects[nm].rotation_euler = (0, 0, th)
    bpy.data.objects["REF_shaft"].rotation_euler = (0, 0, th)
    out = -th/(N_PINS - 1)
    for nm in ("P6_carrier_lower", "P7_carrier_upper"):
        bpy.data.objects[nm].rotation_euler = (0, 0, out)
    for i in range(N_OUT):
        o = bpy.data.objects[f"REF_out_pin_{i}"]; o.rotation_euler = (0, 0, out)
    bpy.context.view_layer.update()

# ============================================================== 4. checks
def mesh_stats(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    nm = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    vol = bm.calc_volume(signed=True); bm.free()
    return nm, vol

def overlap_volume(a, b):
    """Volume of a ∩ b in world space via a temporary MANIFOLD intersect."""
    dg = bpy.context.evaluated_depsgraph_get()
    tmp = a.copy(); tmp.data = a.data.copy(); coll("cutters").objects.link(tmp)
    m = tmp.modifiers.new("i", "BOOLEAN"); m.operation = "INTERSECT"; m.object = b
    try: m.solver = "MANIFOLD"
    except TypeError: m.solver = "EXACT"
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(tmp.matrix_world)
    v = abs(bm.calc_volume()); bm.free()
    bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.meshes.remove(me)
    return v

def run_checks():
    ok = True
    print("\n== part meshes ==")
    for ob in list(coll("drive").objects) + [bpy.data.objects["P0_coupon"]]:
        nm, vol = mesh_stats(ob)
        good = nm == 0 and vol > 0
        ok &= good
        print(f"{ob.name:18s} non-manifold edges={nm:3d}  volume={vol/1000:7.2f} cm3  {'OK' if good else 'FAIL'}")
    pairs = [("P1_base", "P2_ring"), ("P2_ring", "P3_cap"), ("P1_base", "P5a_cam_lower"), ("P1_base", "P4_disc_A"),
             ("P2_ring", "P4_disc_A"), ("P2_ring", "P4_disc_B"), ("P4_disc_A", "P4_disc_B"),
             ("P4_disc_B", "P6_carrier_lower"), ("P2_ring", "P6_carrier_lower"), ("P3_cap", "P6_carrier_lower"),
             ("P3_cap", "P7_carrier_upper"), ("P6_carrier_lower", "P7_carrier_upper"), ("P1_base", "REF_motor_boss"),
             ("P5a_cam_lower", "REF_shaft"), ("P5b_cam_upper", "REF_shaft"), ("P5a_cam_lower", "P5b_cam_upper"),
             ("P5b_cam_upper", "P6_carrier_lower"), ("P4_disc_A", "REF_out_pin_0"), ("P4_disc_B", "REF_out_pin_3")]
    print("\n== interference sweep (mm3, must be ~0) ==")
    worst = {}
    for th in np.linspace(0, 360, 25):
        pose(th)
        for a, b in pairs:
            v = overlap_volume(bpy.data.objects[a], bpy.data.objects[b])
            worst[(a, b)] = max(worst.get((a, b), 0), v)
    for (a, b), v in worst.items():
        good = v < 0.05
        ok &= good
        print(f"{a:18s} x {b:18s} {v:8.4f}  {'OK' if good else 'FAIL'}")
    # positive control: disc A mis-indexed by half a lobe MUST collide with the ring pins
    pose(0); dA = bpy.data.objects["P4_disc_A"]; dA.rotation_euler.z += math.pi/(N_PINS - 1)
    bpy.context.view_layer.update()
    v = overlap_volume(dA, bpy.data.objects["P2_ring"])
    ok &= v > 1.0
    print(f"positive control (disc half-lobe off): {v:.2f} mm3  {'OK (detector works)' if v > 1.0 else 'FAIL'}")
    pose(0)
    return ok

# ============================================================== 5. export (print orientation)
PRINT_XFORM = {   # name: (flip_upside_down, z_of_face_that_goes_on_the_bed)
    "P1_base": (False, Z["base_bot"]), "P2_ring": (False, Z["ring_bot"]), "P3_cap": (True, Z["cap_top"]),
    "P0_coupon": (False, 0.0), "P4_disc_A": (False, None), "P4_disc_B": (False, None), "P5a_cam_lower": (False, Z["cam_bot"]),
    "P5b_cam_upper": (False, Z["discA_top"]),
    "P6_carrier_lower": (False, Z["carrier_bot"]), "P7_carrier_upper": (True, Z["output_face"]),
}

# print order -> file stem (fit-critical small parts first, the long ring print late)
PRINT_ORDER = {
    "P0_coupon": "01_P0_coupon", "P3_cap": "02_P3_cap", "P6_carrier_lower": "03_P6_carrier_lower",
    "P5a_cam_lower": "04a_P5a_cam_lower", "P5b_cam_upper": "04b_P5b_cam_upper", "P4_disc_A": "05_P4_disc_PRINT_2",
    "P1_base": "06_P1_base", "P2_ring": "07_P2_ring", "P7_carrier_upper": "08_P7_carrier_upper",
}

def export_stls(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    pose(0)
    for ob in list(coll("drive").objects) + [bpy.data.objects["P0_coupon"]]:
        if ob.name == "P4_disc_B":
            continue                                    # identical to disc A: print disc A twice
        tmp = ob.copy(); tmp.data = ob.data.copy(); coll("cutters").objects.link(tmp)
        tmp.location = (0, 0, 0); tmp.rotation_euler = (0, 0, 0)
        if ob.name == "P0_coupon": tmp.data.transform(__import__("mathutils").Matrix.Identity(4))
        flip, zbed = PRINT_XFORM[ob.name]
        bm = bmesh.new(); bm.from_mesh(tmp.data)
        zs = [v.co.z for v in bm.verts]
        if flip:
            bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(math.pi, 3, "X"))
            zs = [v.co.z for v in bm.verts]
        xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]
        bmesh.ops.translate(bm, verts=bm.verts, vec=(-(max(xs)+min(xs))/2, -(max(ys)+min(ys))/2, -min(zs)))
        bm.to_mesh(tmp.data); bm.free()
        bpy.ops.object.select_all(action="DESELECT"); tmp.select_set(True)
        bpy.context.view_layer.objects.active = tmp
        fn = os.path.join(out_dir, PRINT_ORDER[ob.name] + ".stl")
        bpy.ops.wm.stl_export(filepath=fn, export_selected_objects=True, global_scale=1.0,
                              use_scene_unit=False, ascii_format=False, apply_modifiers=True)
        bpy.data.objects.remove(tmp, do_unlink=True)
        print("wrote", fn)

# ============================================================== main
def main(out_dir):
    reset_scene()
    build_P1_base(); build_P2_ring(); build_P3_cap()
    build_disc("P4_disc_A"); build_disc("P4_disc_B")
    build_P5a_cam_lower(); build_P5b_cam_upper(); build_P6_lower_carrier(); build_P7_upper_carrier()
    build_reference(); pose(0)
    coupon = build_P0_coupon(); coll("drive").objects.unlink(coupon); coll("reference").objects.link(coupon)
    ok = run_checks()
    export_stls(os.path.join(out_dir, "stl"))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "cycloidal_drive.blend"))
    print("\nALL CHECKS PASSED" if ok else "\nCHECKS FAILED")
    return ok

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    main(argv[0] if argv else os.path.join(HERE, "build_out"))
