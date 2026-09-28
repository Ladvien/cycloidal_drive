"""
guide_steps.py - one Blender scene function per step key in guide_text.STEPS (runs inside Blender).

Each function stages the scene with guide_scene helpers, records insertion moves with G.move(...) and
returns (callouts, camera). A callout is (world_point, label, (dx, dy)); the label is drawn at the
projected point + (dx, dy) pixels. camera = dict(az=, el=) plus optional margin/pad.
"""
# NOTE: import this only after guide_scene.build() - the name lists below are read from the built scene.
import math
from mathutils import Matrix, Vector
import bpy
import guide_scene as G
from guide_scene import P

D = math.radians
MUTE = 0.55
FLIP = (math.pi, 0, 0)

MOTOR = ["HW_motor_body", "HW_motor_face", "HW_motor_boss", "HW_shaft"]
def INS(part): return G.names(f"HW_ins_{part}_")
PINS_OUT = [f"HW_pin_out_{i}" for i in range(P.N_OUT)]
PINS_ALIGN = [f"HW_pin_align_{a}" for a in P.ALIGN_ANGLES]
SCR_MOTOR, SCR_HOUSING, SCR_CARRIER = G.names("HW_scr_motor_"), G.names("HW_scr_housing_"), G.names("HW_scr_carrier_")
CAM_LOWER = ["P5a_cam_lower", "HW_ins_P5"]
BASE = ["P1_base"] + INS("P1")
DISC_A, DISC_B = ["P4_disc_A", "HW_6802_A"], ["P4_disc_B", "HW_6802_B"]
P6_SUB = ["P6_carrier_lower", "HW_625"] + INS("P6") + PINS_OUT
CAP_SUB = ["P3_cap", "HW_6809"] + INS("P3")
P7_SUB = ["P7_carrier_upper"] + INS("P7")
OUTPUT = CAP_SUB + P6_SUB + P7_SUB + SCR_CARRIER

# what is installed on the motor after each step (for the "already done" context)
STACK = {
    "cam_lower": MOTOR + CAM_LOWER + ["HW_scr_set"],
}
STACK["base"] = STACK["cam_lower"] + BASE + SCR_MOTOR
STACK["align_pins"] = STACK["base"] + PINS_ALIGN
STACK["ring"] = STACK["align_pins"] + ["P2_ring"]
STACK["disc1"] = STACK["ring"] + DISC_A
STACK["cam_upper"] = STACK["disc1"] + ["P5b_cam_upper"]
STACK["disc2"] = STACK["cam_upper"] + DISC_B
STACK["cap_on"] = STACK["disc2"] + OUTPUT
STACK["screws"] = STACK["cap_on"] + SCR_HOUSING

def stage(names, mute=MUTE, base=None):
    for n in names: G.show(n, mute=mute, base=base)

def side_arrow(name, lift, gap=6.0):
    """Arrow just outside a hollow part's rim, from its displayed height down to its seat (towards the viewer)."""
    ob = bpy.data.objects[name]; c = G.centre(name); lift = Vector(lift)
    r = max(ob.dimensions.x, ob.dimensions.y) / 2 + gap
    d = Vector((0.866, 0.5, 0)) * r                        # right-hand side as seen by the default camera (az -30)
    top = c + d + Vector((0, 0, ob.dimensions.z / 2)); bot = c - lift + d + Vector((0, 0, ob.dimensions.z / 2))
    G.make_arrow(f"arr_side_{name}", top, bot, r=0.9, head_r=2.6, head_len=6.0)

def world(name, local_pt):
    return bpy.data.objects[name].matrix_world @ Vector(local_pt)

# ------------------------------------------------------------------ 1-3: parts on the table
def s_parts():
    items = [("P1_base", -100, 70), ("P2_ring", -10, 70), ("P3_cap", 82, 70),
             ("P4_disc_A", -125, -10), ("P4_disc_B", -68, -10), ("P5a_cam_lower", -28, -10), ("P5b_cam_upper", 2, -10),
             ("P6_carrier_lower", 45, -10), ("P7_carrier_upper", 108, -10)]
    for n, x, y in items: G.rest(n, x, y)
    c = G.centre
    return [(c("P1_base"), "P1  Base", (-40, 120)), (c("P2_ring"), "P2  Pin ring", (-30, 125)),
            (c("P3_cap"), "P3  Cap", (10, 120)), (c("P4_disc_A"), "P4  Disc  (print 2)", (40, 115)),
            (c("P5a_cam_lower"), "P5a  Lower cam", (-60, 120)), (c("P5b_cam_upper"), "P5b  Upper cam", (40, 175)),
            (c("P6_carrier_lower"), "P6  Lower carrier", (-40, 130)), (c("P7_carrier_upper"), "P7  Upper carrier", (10, 115))], \
           dict(az=-30, el=48)

def s_hardware():
    mot = Matrix.Translation((-120, 55, 40))
    for n in MOTOR: G.show(n, base=mot)
    G.rest("HW_6809", -40, 70); G.rest("HW_6802_A", 12, 82); G.rest("HW_6802_B", 12, 52); G.rest("HW_625", 52, 68)
    pins = PINS_OUT + PINS_ALIGN
    for i, n in enumerate(pins): G.rest(n, 115, 95 - i*5.0, rot=(0, D(90), 0))
    def lay(names, x, y0):
        for i, n in enumerate(names): G.rest(n, x, y0 - i*8.0, rot=(0, D(90), 0))
    lay(SCR_HOUSING, -110, -10); lay(SCR_CARRIER, -55, -10); lay(SCR_MOTOR, -20, -10); lay(["HW_scr_set"], 12, -10)
    ins3 = INS("P1") + INS("P3") + INS("P6") + INS("P7")
    for i, n in enumerate(ins3): G.rest(n, 45 + (i % 5)*8.0, -2 - (i // 5)*8.0)
    G.rest("HW_ins_P5", 105, -10)
    c = G.centre
    s = lambda job: f"{P.SCREWS_USED[job][0]} x {P.SCREWS_USED[job][1]}"
    return [(c("HW_shaft") + Vector((0, 0, 6)), "NEMA17 motor", (-60, -110)),
            (c("HW_6809"), f"{P.BRG_OUT['name'].split()[0]}  45x58x7   x1", (-60, -95)),
            (c("HW_6802_A"), f"{P.BRG_CAM['name']}  15x24x5   x2", (-10, -120)),
            (c("HW_625"), f"{P.BRG_TIP['name']}  5x16x5   x1", (-20, 125)),
            (c(pins[0]), f"3 x 30 dowel   x{len(pins)}", (10, -80)),
            (c(SCR_HOUSING[-1]), f"{s('housing')}   x{len(SCR_HOUSING)}", (-40, 70)),
            (c(SCR_CARRIER[-1]), f"{s('carrier')}   x{len(SCR_CARRIER)}", (-30, 95)),
            (c(SCR_MOTOR[-1]), f"{s('motor')}   x{len(SCR_MOTOR)}", (0, 115)),
            (c("HW_scr_set"), f"{s('set')}   x1", (40, 95)),
            (c(ins3[min(17, len(ins3) - 1)]), f"M3 heat-set insert   x{len(ins3)}", (0, 85)),
            (c("HW_ins_P5"), "M2 insert   x1", (40, 60))], dict(az=-30, el=50)

def s_inserts():
    G.rest("P1_base", -92, 45); G.rest("P3_cap", 0, 45); G.rest("P7_carrier_upper", 88, 45)
    G.rest("P6_carrier_lower", -50, -45); G.rest("P5a_cam_lower", 40, -45, rot=(0, 0, D(-142)))
    for part, key in (("P1_base", "P1"), ("P3_cap", "P3"), ("P6_carrier_lower", "P6"), ("P7_carrier_upper", "P7")):
        for n in INS(key):
            G.follow(n, part); G.move(n, (0, 0, 14))
    G.follow("HW_ins_P5", "P5a_cam_lower")
    out = (G.transform_of("P5a_cam_lower").to_3x3() @ Vector((0, 1, 0))).normalized()
    G.move("HW_ins_P5", out * 14)
    c = G.centre
    return [(c("HW_ins_P1_180"), f"P1 base:  {len(INS('P1'))} x M3", (-40, -150)),
            (c(INS("P3")[0]), f"P3 cap:  {len(INS('P3'))} x M3  (lip side)", (-80, -120)),
            (c(INS("P7")[0]), f"P7 upper carrier:  {len(INS('P7'))} x M3", (40, -110)),
            (c(INS("P6")[0]), f"P6 lower carrier:  {len(INS('P6'))} x M3", (-60, 250)),
            (c("HW_ins_P5"), "P5a lower cam:  1 x M2, radial", (60, 90))], dict(az=-30, el=42)

# ------------------------------------------------------------------ 4-6: sub-assemblies on the bench
def s_disc_bearings():
    G.rest("P4_disc_A", -32, 0, mute=0.25); G.rest("P4_disc_B", 32, 0, mute=0.25)
    for disc, brg in (("P4_disc_A", "HW_6802_A"), ("P4_disc_B", "HW_6802_B")):
        G.follow(brg, disc); G.move(brg, (0, 0, 18))
    c = G.centre
    return [(c("HW_6802_A"), f"{P.BRG_CAM['name']}", (-60, -110)),
            (c("HW_6802_B"), "press on the outer ring", (60, -110)),
            (c("P4_disc_A") + Vector((0, -20, 0)), "P4 disc  x2", (-80, 110))], dict(az=-30, el=38)

def s_p6_625():
    G.rest("P6_carrier_lower", 0, 0, rot=FLIP, mute=0.35)
    for n in INS("P6"): G.follow(n, "P6_carrier_lower", mute=0.35)
    G.follow("HW_625", "P6_carrier_lower"); G.move("HW_625", (0, 0, 16))
    c = G.centre
    return [(c("HW_625"), f"{P.BRG_TIP['name']}", (-80, -110)),
            (c("P6_carrier_lower") + Vector((0, -20, 2)), "P6: wide shoulder face up", (40, 140))], dict(az=-30, el=40)

def s_p6_pins():
    G.rest("P7_carrier_upper", 0, 0, rot=FLIP, mute=0.35)
    X = G.transform_of("P7_carrier_upper")
    stage(["P6_carrier_lower", "HW_625"] + INS("P6") + INS("P7"), mute=0.35, base=X)
    stage(PINS_OUT, mute=0.0, base=X)
    G.move(PINS_OUT[1], (0, 0, 30))
    c = G.centre
    return [(c(PINS_OUT[1]), "press each pin down until it stops on the table", (60, -80)),
            (c("P7_carrier_upper") + Vector((0, -24, 0)), "P7 upper carrier, output face down: the stop", (-40, 150)),
            (c("P6_carrier_lower") + Vector((-20, -14, 3)), "P6 lower carrier, shoulder up", (-170, -60))], dict(az=-30, el=30)

# ------------------------------------------------------------------ 7-13: build up on the motor
def s_cam_lower():
    stage(MOTOR, mute=0.0)
    stage(CAM_LOWER + ["HW_scr_set"], mute=0.0)
    lift = Vector((0, 0, 26)); out = Vector((0, 12, 0))
    G.move(CAM_LOWER, lift, arrows=["P5a_cam_lower"])
    G.move("HW_scr_set", out, display=lift + out, seat_shift=lift)
    c = G.centre
    return [(c("P5a_cam_lower") + Vector((-6, 0, 3)), "P5a lower cam, collar down", (-330, 20)),
            (Vector((0, 2.0, P.MOTOR["shaft_len"] - 3)), "line up the D-bore with the shaft's flat", (-330, 90)),
            (c("HW_scr_set"), f"{P.SCREWS_USED['set'][0]} x {P.SCREWS_USED['set'][1]} set screw", (230, 0)),
            (Vector((-8, 6, P.MOTOR["boss_h"])), "rest the collar on 3 sheets of paper here", (-60, 150))], \
           dict(az=150, el=22, pad=(60, 60, 110, 70))

def s_base():
    stage(STACK["cam_lower"])
    stage(BASE + SCR_MOTOR, mute=0.0)
    lift = Vector((0, 0, 30))
    G.move(BASE, lift, arrows=["P1_base"])
    G.move(SCR_MOTOR, (0, 0, 16), display=lift + Vector((0, 0, 16)), seat_shift=lift)
    c = G.centre
    return [(c("P1_base") + Vector((-30, -10, 0)), "P1 base, inserts up", (-120, -60)),
            (c(SCR_MOTOR[0]), f"{P.SCREWS_USED['motor'][0]} x {P.SCREWS_USED['motor'][1]}  x{len(SCR_MOTOR)}", (80, -80)),
            (Vector((0, -11, P.MOTOR["boss_h"])), "recess underneath seats on the motor's boss", (60, 120))], dict(az=-30, el=26)

def s_align_pins():
    stage(STACK["base"])
    stage(PINS_ALIGN, mute=0.0)
    G.move(PINS_ALIGN, (0, 0, 34))
    c = G.centre
    return [(c(PINS_ALIGN[0]), "3 x 30 dowel  x2: press until flush underneath", (80, -60))], dict(az=-30, el=26)

def s_ring():
    stage(STACK["align_pins"])
    G.show("P2_ring"); G.move("P2_ring", (0, 0, 30), arrows=[])
    side_arrow("P2_ring", (0, 0, 30))
    a = D(120); pin = Vector((P.R_PIN*math.cos(a), P.R_PIN*math.sin(a), 13 + 30))
    return [(G.centre("P2_ring") + Vector((34, -12, 4)), "P2 pin ring, wide step up", (140, -40)),
            (pin, f"grease the {P.N_PINS} pins", (-120, -110))], dict(az=-30, el=30)

def s_disc1():
    stage(STACK["ring"])
    stage(DISC_A, mute=0.0); G.move(DISC_A, (0, 0, 26), arrows=["P4_disc_A"])
    return [(G.centre("P4_disc_A") + Vector((-20, -8, 2)), "first disc onto the lower lobe", (-150, -60)),
            (G.centre("P5a_cam_lower") + Vector((P.E + 7, 0, 3)), "lower lobe", (200, 40))], dict(az=-30, el=34)

def s_cam_upper():
    stage(STACK["disc1"])
    G.show("P5b_cam_upper"); G.move("P5b_cam_upper", (0, 0, 24))
    return [(G.centre("P5b_cam_upper"), "P5b upper cam, spacer down: line up the D-bore", (-200, -60))], dict(az=-30, el=34)

def s_disc2():
    stage(STACK["cam_upper"])
    stage(DISC_B, mute=0.0); G.move(DISC_B, (0, 0, 24), arrows=["P4_disc_B"])
    dimple = world("P4_disc_B", (19.8*math.cos(D(30)), 19.8*math.sin(D(30)), P.BRG_CAM["B"]))
    return [(G.centre("P4_disc_B") + Vector((-20, -8, 2)), "second disc onto the upper lobe", (-150, -60)),
            (dimple, "dimple opposite the first disc's", (160, -60))], dict(az=-30, el=38)

# ------------------------------------------------------------------ 14-16: output assembly on the bench
def s_cap_bearing():
    G.rest("P3_cap", 0, 0, rot=FLIP, mute=0.35)
    for n in INS("P3"): G.follow(n, "P3_cap", mute=0.35)
    G.follow("HW_6809", "P3_cap"); G.move("HW_6809", (0, 0, 18))
    return [(G.centre("HW_6809"), f"{P.BRG_OUT['name'].split()[0]}: press on the outer ring", (-120, -100)),
            (G.centre("P3_cap") + Vector((0, -33, 0)), "P3 cap, narrow lip face down", (60, 110))], dict(az=-30, el=40)

BENCH = Matrix.Translation((0, 0, -P.Z["discA_bot"]))   # output assembly standing on its pin ends

def s_carrier_in():
    stage(P6_SUB, mute=0.35, base=BENCH)
    stage(CAP_SUB, mute=0.0, base=BENCH)
    G.move(CAP_SUB, (0, 0, 28), arrows=[])
    side_arrow("P3_cap", (0, 0, 28))
    return [(G.centre("P3_cap") + Vector((-34, -10, 3)), "cap + bearing, lip up", (-130, -60)),
            (G.centre("P6_carrier_lower") + Vector((-20, -14, 0)), "P6 standing on its long pin ends", (-160, 110))], dict(az=-30, el=28)

def s_p7():
    stage(P6_SUB + CAP_SUB, mute=0.35, base=BENCH)
    stage(P7_SUB + SCR_CARRIER, mute=0.0, base=BENCH)
    lift = Vector((0, 0, 24))
    G.move(P7_SUB, lift, arrows=["P7_carrier_upper"])
    G.move(SCR_CARRIER, (0, 0, 16), display=lift + Vector((0, 0, 16)), seat_shift=lift)
    return [(G.centre("P7_carrier_upper") + Vector((-26, -8, 0)), "P7 upper carrier, flange up", (-150, -40)),
            (G.centre(SCR_CARRIER[0]), f"{P.SCREWS_USED['carrier'][0]} x {P.SCREWS_USED['carrier'][1]}  x{len(SCR_CARRIER)}", (90, -70))], dict(az=-30, el=30)

# ------------------------------------------------------------------ 17-19: close up
def s_cap_on():
    stage(STACK["disc2"])
    stage(OUTPUT, mute=0.0)
    G.move(OUTPUT, (0, 0, 40), arrows=[])
    side_arrow("P3_cap", (0, 0, 40))
    return [(G.centre("P3_cap") + Vector((-34, -12, 0)), "output assembly: pins into the discs", (-170, -40)),
            (G.centre(PINS_ALIGN[0]) + Vector((0, 0, 12)), "alignment pins", (120, 40))], dict(az=-30, el=26)

def s_screws():
    stage(STACK["cap_on"])
    stage(SCR_HOUSING, mute=0.0)
    G.move(SCR_HOUSING, (0, 0, 32))
    return [(G.centre(SCR_HOUSING[0]), f"{P.SCREWS_USED['housing'][0]} x {P.SCREWS_USED['housing'][1]}  x{len(SCR_HOUSING)}: star pattern, snug", (80, -80))], dict(az=-30, el=30)

def s_done():
    stage(STACK["screws"], mute=0.0)
    c = G.centre
    return [(c(INS("P7")[0]), f"output: {len(INS('P7'))} x M3 on Ø{2*P.OUTPUT_INSERT_R:g}", (120, -90)),
            (c(INS("P3")[1]), f"mounting: {len(INS('P3'))} x M3", (-150, -90)),
            (c("HW_motor_body"), "NEMA17", (-160, 40))], dict(az=-30, el=30)

def control_one_piece_cam():
    """Positive control for the path check: with P5b already on the shaft the cam is the old one-piece design,
    and disc A's bearing must NOT be able to reach the lower lobe. If this passes, the checker is broken."""
    stage(STACK["ring"] + ["P5b_cam_upper"])
    stage(DISC_A, mute=0.0); G.move(DISC_A, (0, 0, 26), arrows=[])

SCENES = {
    "parts": s_parts, "hardware": s_hardware, "inserts": s_inserts, "disc_bearings": s_disc_bearings,
    "p6_625": s_p6_625, "p6_pins": s_p6_pins, "cam_lower": s_cam_lower, "base": s_base, "align_pins": s_align_pins,
    "ring": s_ring, "disc1": s_disc1, "cam_upper": s_cam_upper, "disc2": s_disc2, "cap_bearing": s_cap_bearing,
    "carrier_in": s_carrier_in, "p7": s_p7, "cap_on": s_cap_on, "screws": s_screws, "done": s_done,
}
LAYOUT_STEPS = {"parts", "hardware"}      # nothing is inserted: skip the path check
