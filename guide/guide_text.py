"""
guide_text.py - the words of the assembly guide (no bpy).

Every number comes from geometry/params.py, so the text follows the design when it changes.
Step order lives in STEPS; the Blender side has one scene function per step key (guide_steps.py).
Cross-references use {n[key]} and are resolved to step numbers at compose time.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "geometry"))
import params as P   # noqa: E402

def _f(x):  # 9.5 -> "9.5", 23.0 -> "23"
    return f"{x:.1f}".rstrip("0").rstrip(".")

def scr(job):
    size, L = P.SCREWS_USED[job]; return f"{size} x {L}"

N_MOTOR_SCR = 4
N_HOUSING_SCR = len(P.BOLT_ANGLES)
N_CARRIER_SCR = len(P.CARRIER_JOIN_ANGLES)
INS = {"P1": len(P.BOLT_ANGLES), "P3": len(P.MOUNT_ANGLES), "P6": len(P.CARRIER_JOIN_ANGLES), "P7": len(P.OUTPUT_INSERT_ANGLES)}
N_INS_M3 = sum(INS.values())
N_DOWELS = P.N_OUT + len(P.ALIGN_ANGLES)
SHIM = P.Z["cam_bot"] - P.MOTOR["boss_h"]
PIN_ABOVE = P.Z["output_face"] - P.Z["brg_out_top"]        # output pins above P6's insert face
PIN_BELOW = P.Z["carrier_bot"] - P.Z["discA_bot"]           # ... and below P6's shoulder face
P7_THICK = P.Z["output_face"] - P.Z["ucar_bot"]
P7_IS_GAUGE = abs(P7_THICK - PIN_ABOVE) < 0.05
ALIGN_ABOVE = P.DOWEL["L"] - P.Z["base_top"]
MIN_SHAFT = P.Z["tip_pocket_top"] - 1.0
RATIO = P.N_PINS - 1
B6802, B6809, B625 = P.BRG_CAM["name"].split(" ")[0], P.BRG_OUT["name"].split(" ")[0], P.BRG_TIP["name"].split(" ")[0]
def bdim(b): return f"{_f(b['d'])} x {_f(b['D'])} x {_f(b['B'])}"
N_PRINTS = 10   # P1, P2, P3, P4 x2, P5a, P5b, P6, P7

SPECS = [
    ("Ratio", f"{RATIO} : 1, output turns opposite to the motor"),
    ("Housing", f"Ø{_f(P.HOUSING_OD)} mm, {_f(P.Z['output_face'])} mm above the motor face"),
    ("Cycloid", f"{P.N_PINS} pins on R{_f(P.R_PIN)}, {P.N_PINS - 1} lobes, e = {_f(P.E)} mm, two discs at 180°"),
    ("Output", f"{INS['P7']} x M3 inserts on a Ø{_f(2*P.OUTPUT_INSERT_R)} bolt circle"),
    ("Mounting", f"{INS['P3']} x M3 inserts in the cap face"),
    ("Prints", f"{N_PRINTS} prints from 9 files, all PETG"),
]

STEPS = [
dict(key="parts", title="Check the printed parts",
    need=[("1", "P1 base", "P1_base"), ("1", "P2 pin ring", "P2_ring"), ("1", "P3 cap", "P3_cap"),
          ("2", "P4 disc", "P4_disc_A"), ("1", "P5a lower cam", "P5a_cam_lower"), ("1", "P5b upper cam", "P5b_cam_upper"),
          ("1", "P6 lower carrier", "P6_carrier_lower"), ("1", "P7 upper carrier", "P7_carrier_upper")],
    do=[f"Lay out all {N_PRINTS} prints. Remove brims, and trim any elephant-foot flare from the bottom edges.",
        f"Run a fingertip around the {P.N_PINS} pins inside P2 and the lobes of both discs. Scrape off any blobs or seam zits; these are the surfaces that roll against each other.",
        f"Drop a dowel through each of the {P.N_OUT} Ø{_f(P.OUT_HOLE_D)} holes in both discs. It should pass with visible play. That play is the disc's {_f(2*P.E)} mm wobble and is intended."],
    check="Both discs sit flat on the table without rocking. Nothing is warped or lifted at the corners.",
    tip="The coupon (P0) is not part of the drive. Keep it: it records the hole fits your printer produced."),
dict(key="hardware", title="Check the hardware and tools",
    need=[("1", "NEMA17 stepper motor", "motor"), ("1", f"{B6809} bearing", "steel"), ("2", f"{B6802} bearing", "steel"),
          ("1", f"{B625} bearing", "steel"), (str(N_DOWELS), f"3 x 30 mm dowel ({10 - N_DOWELS} spare)", "steel"),
          (str(N_HOUSING_SCR), f"{scr('housing')} screw", "screw"), (str(N_CARRIER_SCR), f"{scr('carrier')} screw", "screw"),
          (str(N_MOTOR_SCR), f"{scr('motor')} screw", "screw"), ("1", f"{scr('set')} screw", "screw"),
          (str(N_INS_M3), "M3 heat-set insert", "brass"), ("1", "M2 heat-set insert", "brass")],
    tools="Soldering iron with an insert tip, 2.5 mm and 1.5 mm hex keys, bench vise or clamp, a flat scrap board, calipers, printer paper (for a shim), PTFE or white-lithium grease.",
    do=[f"Measure the motor shaft from the mounting face to the tip. It needs to be at least {_f(MIN_SHAFT)} mm. If it is shorter, leave out the {B625} bearing in step {{n[p6_625]}}.",
        f"Check each bearing turns smoothly. Measure the {B6809}'s outside diameter: it should read {P.BRG_OUT['D']:.2f} mm.",
        f"Sort the screws by length now. The {scr('housing')} and {scr('carrier')} look alike at a glance."],
    check=f"{N_DOWELS} dowels, {N_HOUSING_SCR + N_CARRIER_SCR + N_MOTOR_SCR} M3 screws, 1 M2 screw, {N_INS_M3 + 1} inserts, 4 bearings.",
    tip="A 1.5 mm hex key fits the M2 set screw; 2.5 mm fits every M3 socket-head screw."),
dict(key="inserts", title="Install the heat-set inserts",
    need=[(str(N_INS_M3), "M3 heat-set insert", "brass"), ("1", "M2 heat-set insert", "brass")],
    tools="Soldering iron with an insert tip (a fine tip for the cam's M2 insert).",
    do=["Heat the iron to about 240 °C for PETG (about 210 °C for PLA).",
        "Set each insert on its hole and let the iron sink it straight down until it is flush with the surface. Guide it; don't push hard.",
        f"P1 base: {INS['P1']} inserts in the flat top face (the face without the round motor recess).",
        f"P3 cap: {INS['P3']} inserts in the face with the narrow lip. P6 lower carrier: {INS['P6']} inserts in the end opposite the wide shoulder.",
        f"P7 upper carrier: {INS['P7']} inserts in the wide flange face. P5a lower cam: 1 M2 insert, sideways into the collar, at the bottom of the small counterbore."],
    check="Every insert is flush, or up to 0.2 mm below the surface, and none is tilted. Run a screw into each one to confirm the thread is straight.",
    tip="If an insert goes in crooked, reheat it at once and press it square with a flat piece of metal. The cam's M2 insert sits deep in its counterbore, so use a fine tip."),
dict(key="disc_bearings", title=f"Press the {B6802} bearings into the discs",
    need=[("2", f"{B6802} bearing ({bdim(P.BRG_CAM)})", "steel"), ("2", "P4 disc", "P4_disc_A")],
    do=[f"Lay a disc flat on a hard surface and start a bearing square in its Ø{_f(P.BRG_CAM['D'])} bore.",
        f"Press it in with a flat board or a vise jaw, pushing only on the bearing's outer ring, until it is flush with both faces. Disc and bearing are both {_f(P.BRG_CAM['B'])} mm thick.",
        "Repeat with the second disc. The two discs are identical at this point."],
    check="Each bearing is flush on both sides, its inner ring spins freely, and the disc still sits flat.",
    tip="Too tight to press by hand? Chill the bearing in the freezer for 10 minutes. Too loose? Reprint the discs with a smaller bearing_press in params.py."),
dict(key="p6_625", title=f"Press the {B625} into the lower carrier",
    need=[("1", f"{B625} bearing ({bdim(P.BRG_TIP)})", "steel"), ("1", "P6 lower carrier", "P6_carrier_lower")],
    do=[f"Turn P6 so its wide shoulder faces up. The Ø{_f(P.BRG_TIP['D'])} pocket is in the middle of that face.",
        "Press the bearing into the pocket, pushing on its outer ring, until it bottoms out flush with the face.",
        f"Motor shaft shorter than {_f(MIN_SHAFT)} mm (step {{n[hardware]}})? Skip this bearing."],
    check="The bearing is flush with the shoulder face and spins freely.",
    tip="This bearing catches the tip of the motor shaft, so the cams can't wobble on it."),
dict(key="p6_pins", title="Press in the output pins",
    need=[(str(P.N_OUT), "3 x 30 mm dowel", "steel"), ("1", "P6 (from the last step)", "P6_carrier_lower"),
          ("1", "P7 upper carrier (as a gauge)", "P7_carrier_upper")],
    do=([f"Lay P7 output-face down on a flat, hard surface. It is exactly {_f(P7_THICK)} mm thick, which is how far the pins must stick out of P6's insert face.",
         f"Set P6 on it, shoulder up, with its {P.N_OUT} pin holes over P7's {P.N_OUT} holes. The screw holes line up too.",
         "Press each dowel down through P6 with a vise or a flat punch until it stops on the table, then lift P6 off P7."]
        if P7_IS_GAUGE else
        [f"Set your calipers' depth rod to {_f(PIN_ABOVE)} mm.",
         f"Press each dowel into P6 from the shoulder side until {_f(PIN_ABOVE)} mm sticks out of the insert face."]),
    check=f"All {P.N_OUT} pins stick out {_f(PIN_BELOW)} mm from the shoulder face and {_f(PIN_ABOVE)} mm from the other face, parallel to each other.",
    tip="Press straight. A pin that goes in at an angle will bind in the discs later. Pull it and press it again."),
dict(key="cam_lower", title="Mount the lower cam on the motor",
    need=[("1", "P5a lower cam (with its M2 insert)", "P5a_cam_lower"), ("1", f"{scr('set')} screw", "screw"),
          ("1", "NEMA17 motor", "motor"), ("3", "sheets of printer paper (shim)", "grease")],
    do=[f"Slide P5a onto the motor shaft, collar first. The top {_f(P.Z['discA_top'] - (P.MOTOR['shaft_len'] - P.MOTOR['flat_len'] + 0.5))} mm of its bore is D-shaped: line that up with the flat on the shaft.",
        f"Lay three sheets of printer paper (about {_f(SHIM)} mm) on the motor's round boss, and rest the collar on them.",
        f"Thread the {scr('set')} into the collar's insert and tighten it against the shaft with a 1.5 mm key. Pull out the paper."],
    check=f"The cam doesn't turn or slide on the shaft, and there's a {_f(SHIM)} mm gap between the collar and the boss.",
    tip="The cam's height sets where the discs run. Getting the shim right matters more than tightening hard."),
dict(key="base", title="Fit the base to the motor",
    need=[("1", f"P1 base (with {INS['P1']} inserts)", "P1_base"), (str(N_MOTOR_SCR), f"{scr('motor')} screw", "screw")],
    do=["Lower the base over the cam, insert face up, so the round recess underneath seats on the motor's boss.",
        "Line up the four counterbored holes with the motor's threaded holes.",
        f"Fit the four {scr('motor')} screws with a 2.5 mm key: snug, not tight. They clamp plastic."],
    check="The base sits flat on the motor, the screw heads are below the top surface, and the cam turns freely inside the base's bore.",
    tip=f"If a screw bottoms out before it is snug, your motor's threads are shallow. Use {P.SCREWS_USED['motor'][0]} x {P.SCREWS_USED['motor'][1] - 2} instead."),
dict(key="align_pins", title="Press in the alignment pins",
    need=[(str(len(P.ALIGN_ANGLES)), "3 x 30 mm dowel", "steel")],
    do=["Press a dowel into each of the two small holes near the rim, on opposite sides of the base.",
        "Push until the bottom end is flush with the underside of the base. The holes sit outside the motor body, so the pin can pass straight through."],
    check=f"About {_f(ALIGN_ABOVE)} mm of each pin stands above the base, and both are vertical.",
    tip="These two pins line up the ring and the cap, and with them all six screw holes."),
dict(key="ring", title="Fit the pin ring",
    need=[("1", "P2 pin ring", "P2_ring"), ("", "Grease", "grease")],
    do=[f"Wipe a thin coat of grease on the {P.N_PINS} pins inside the ring.",
        "Lower the ring over the two alignment pins, with the wider stepped opening facing up.",
        "Seat it flat on the base."],
    check="The ring sits flush on the base and its six screw holes line up with the base's inserts.",
    tip="Thin is right: grease only has to fill the gaps between lobes and pins. Extra just gets pushed out."),
dict(key="disc1", title="Fit the first disc",
    need=[("1", f"Disc with {B6802} (from step {{n[disc_bearings]}})", "P4_disc_A")],
    do=["Lower a disc onto the lower cam lobe so its bearing slides over the lobe.",
        "Turn the disc slightly until its lobes drop between the ring's pins. It only goes all the way down when the lobes mesh.",
        "Wipe a little grease on its top face."],
    check="The disc's top face is level with the top of the cam lobe, and turning the motor shaft by hand makes the disc wobble around the pins without binding.",
    tip="If it won't drop, turn the motor shaft a few degrees; the lobe may be pushing the disc against a pin."),
dict(key="cam_upper", title="Fit the upper cam",
    need=[("1", "P5b upper cam", "P5b_cam_upper")],
    do=["Line up P5b's D-shaped bore with the flat on the shaft and slide it down, spacer end first.",
        "Push it down until the spacer rests on the lower cam lobe."],
    check="The two lobes point in opposite directions (the flat forces this), and P5b turns with the shaft.",
    tip=f"Nothing clamps P5b. The {B625} in the carrier (step {{n[cap_on]}}) stops it from riding up."),
dict(key="disc2", title="Fit the second disc, turned 180°",
    need=[("1", f"Disc with {B6802} (from step {{n[disc_bearings]}})", "P4_disc_B")],
    do=["Turn the second disc so its small dimple is on the opposite side from the first disc's dimple.",
        "Lower it onto the upper lobe and let its lobes drop between the pins.",
        f"Look down through the {P.N_OUT} holes: the two discs' holes overlap, offset by {_f(2*P.E)} mm."],
    check="Both discs are down, and the shaft turns by hand with smooth, even resistance.",
    tip=f"Only a few orientations let all {P.N_OUT} holes clear the output pins in step {{n[cap_on]}}. Dimples on opposite sides is one of them."),
dict(key="cap_bearing", title=f"Press the {B6809} into the cap",
    need=[("1", f"P3 cap (with {INS['P3']} inserts)", "P3_cap"), ("1", f"{B6809} bearing ({bdim(P.BRG_OUT)})", "steel")],
    do=[f"Lay the cap on a flat surface with its narrow lip face down, so the Ø{_f(P.BRG_OUT['D'])} bore opens upward.",
        "Press the bearing in evenly, pushing on its outer ring, until it seats against the lip."],
    check="The bearing is flush with the cap's face and turns freely.",
    tip="A flat board across the bearing works: until it's seated, the bearing sits proud of the cap."),
dict(key="carrier_in", title="Fit the cap onto the lower carrier",
    need=[("1", "P6 with pins and bearing (steps {n[p6_625]} and {n[p6_pins]})", "P6_carrier_lower"),
          ("1", "Cap with bearing (last step)", "P3_cap")],
    do=[f"Stand P6 on the ends of its pins, long ends down ({_f(PIN_BELOW)} mm side).",
        "Turn the cap lip-side up and lower it over P6, so the bearing's inner ring slides onto P6's hub.",
        "Push down until the inner ring rests on P6's shoulder."],
    check="P6 turns freely in the bearing, and its short pin ends stick up through the cap's lip.",
    tip="Push only on the bearing's inner ring (or on the cap evenly). Levering on one edge can crack the lip."),
dict(key="p7", title="Fit the upper carrier",
    need=[("1", f"P7 upper carrier (with {INS['P7']} inserts)", "P7_carrier_upper"), (str(N_CARRIER_SCR), f"{scr('carrier')} screw", "screw")],
    do=["Keep the assembly standing on its pins.",
        f"Lower P7 over the {P.N_OUT} short pin ends, flange up, so its hub passes through the cap's lip.",
        f"Fit the {N_CARRIER_SCR} {scr('carrier')} screws into P6's inserts and tighten them evenly. This clamps the bearing's inner ring between P6 and P7."],
    check="The pin ends are flush with P7's face, and the carrier turns freely in the cap with no rocking.",
    tip="If the carrier binds after tightening, the screws are pulling P6 and P7 crooked. Loosen them and tighten again in rotation."),
dict(key="cap_on", title="Lower the output assembly onto the drive",
    need=[("1", "Output assembly (last step)", "P3_cap")],
    do=["Lower the assembly straight down over the two alignment pins.",
        f"The {P.N_OUT} output pins go into the discs' holes and the {B625} onto the shaft tip. Turn the output flange slightly until the pins drop in.",
        "Seat the cap flat on the ring."],
    check=f"The cap sits flat. Turning the output flange by hand turns the motor shaft {RATIO} times as fast, the opposite way.",
    tip="If the pins won't find the holes, rock the motor shaft back and forth a few degrees while pressing lightly on the flange."),
dict(key="screws", title="Fit the housing screws",
    need=[(str(N_HOUSING_SCR), f"{scr('housing')} screw", "screw")],
    do=[f"Fit the {N_HOUSING_SCR} {scr('housing')} screws through the cap and ring into the base's inserts.",
        "Tighten them in a star pattern, a little at a time, and stop at snug.",
        f"Turn the output by hand through a full turn ({RATIO} motor turns)."],
    check="It turns smoothly the whole way round, with no tight spots and no clicking.",
    tip="A tight spot that repeats once per output turn usually means one screw is over-tightened and squeezing the ring. Back it off a little."),
dict(key="done", title="Mount it and run it",
    need=[],
    do=[f"Mount the drive by the {INS['P3']} M3 inserts in the cap face. The bracket needs a Ø60 or larger hole for the output flange.",
        f"Bolt your load to the {INS['P7']} M3 inserts in the output flange (Ø{_f(2*P.OUTPUT_INSERT_R)} bolt circle).",
        f"{RATIO} motor turns make 1 output turn, and the output turns the opposite way to the motor."],
    check="Run the motor slowly first (about 60 rpm) and listen for clicks or tight spots before loading it.",
    tip="Re-grease the pins after the first hour of running, once the high spots have worn in."),
]

KEYS = [s["key"] for s in STEPS]
NUM = {k: i + 1 for i, k in enumerate(KEYS)}

def resolved(step):
    """Step dict with {n[key]} cross-references replaced by step numbers."""
    fmt = lambda s: s.format(n=NUM) if isinstance(s, str) else s
    out = dict(step)
    for k in ("title", "check", "tip", "tools"):
        if k in out: out[k] = fmt(out[k])
    out["do"] = [fmt(s) for s in step["do"]]
    out["need"] = [(q, fmt(t), c) for q, t, c in step["need"]]
    return out
