"""
params.py - single source of truth for the NEMA17 3D-printed cycloidal drive.
All lengths in mm, angles in degrees. Origin = centre of the NEMA17 mounting face,
+Z points from the motor toward the output. The agent must read every dimension
from here; never hard-code a number in the build.

Items marked MEASURE must be checked against the user's actual parts with calipers.
Items marked TUNE come from the tolerance coupon (P0) print.
"""

# ---------------------------------------------------------------- printer fit (TUNE)
FIT = dict(
    hole_comp=0.00,        # added to every printed hole diameter (after coupon); + if holes print small
    bearing_press=0.00,    # added to bearing-seat bores (bore = bearing OD + this)
    shaft_press=-0.05,     # added to printed shafts that go INTO bearing bores (shaft = bearing ID + this)
    dowel_press=2.95,      # hole dia for press-fit dowels
    dowel_slip=3.10,       # hole dia for dowels that must slide (alignment through ring/cap, upper carrier)
    gap_axial=0.50,        # axial running gap between moving and stationary faces
)
CIRC_SEGS = dict(small=64, medium=96, large=192)   # n-gon counts; holes are circumscribed

# ---------------------------------------------------------------- NEMA17 motor (MEASURE)
MOTOR = dict(
    body=42.3, bolt_square=31.0, bolt="M3", bolt_thread_depth=4.5,
    boss_d=22.0, boss_h=2.0,
    shaft_d=5.0, shaft_flat=4.5,       # D-flat: 4.5 across flat
    shaft_len=24.0,                    # from mounting face to tip (MEASURE, must be >= 23 for the 625 tip bearing)
    flat_len=15.0,                     # length of the D-flat measured back from the tip (MEASURE)
)

# ---------------------------------------------------------------- bought parts
BRG_CAM   = dict(name="6802-2RS", d=15.0, D=24.0, B=5.0, d1=17.9, D1=21.1)  # x2, one per disc
BRG_OUT   = dict(name="6809-2RS (61809)", d=45.0, D=58.0, B=7.0)             # x1, output
BRG_TIP   = dict(name="625-2RS", d=5.0, D=16.0, B=5.0)                       # x1, motor-shaft tip support (optional)
DOWEL     = dict(d=3.0, L=30.0)            # uxcell 304 SS 3 x 30, 10 pcs: 6 output pins + 2 housing alignment + 2 spare

SCREW = {  # clearance hole, SHCS head dia / height, heat-set insert hole dia / depth (insert values MEASURE)
    "M2": dict(clear=2.4, head_d=3.8, head_h=2.0, ins_d=3.2, ins_depth=4.0),
    "M3": dict(clear=3.4, head_d=5.5, head_h=3.0, ins_d=4.0, ins_depth=6.0),
    "M4": dict(clear=4.5, head_d=7.0, head_h=4.0, ins_d=5.6, ins_depth=8.5),
}
CBORE_EXTRA_D, CBORE_EXTRA_H = 0.7, 0.2

# screws by job: (size, length mm). Counts come from the hole patterns below. Drives the BOM and the guide.
SCREWS_USED = {
    "motor":   ("M3", 8),    # P1 base -> motor (4, square pattern)
    "housing": ("M3", 25),   # P3 -> P2 -> inserts in P1 (len(BOLT_ANGLES))
    "carrier": ("M3", 12),   # P7 -> inserts in P6 (len(CARRIER_JOIN_ANGLES))
    "set":     ("M2", 5),    # radial set screw in the P5a collar (1)
}
INSERT_LEN = {"M2": 4.0, "M3": 5.7, "M4": 8.1}   # heat-set insert body length (MEASURE)

# ---------------------------------------------------------------- cycloid core
N_PINS  = 16          # ring pins; disc lobes = 15; ratio 15:1, output turns opposite to motor
R_PIN   = 25.0        # ring-pin pitch radius
RP      = 1.5         # ring-pin radius (printed; = dowel radius so steel pins are a drop-in upgrade)
E       = 1.2         # eccentricity
C_PROF  = 0.10        # disc profile clearance
C_WALL  = 0.40        # wall relief clearance between pins
N_OUT   = 6           # output pins (steel dowels)
R_OUT   = 17.1        # output-pin pitch radius
OUT_HOLE_D = DOWEL["d"] + 2*E + 2*0.10   # 5.6 hole in each disc

# ---------------------------------------------------------------- housing envelope
HOUSING_OD  = 76.0
BOLT_PCD_R  = 34.0
BOLT_ANGLES = [0, 60, 120, 180, 240, 300]      # 6x M3 housing bolts
ALIGN_ANGLES = [30, 210]                       # 2x 3x30 dowels through P1+P2+P3
MOUNT_ANGLES = [90, 150, 270, 330]             # 4x M3 inserts in P3 top face for mounting the drive

# ---------------------------------------------------------------- axial stack (z of each face)
Z = dict(
    base_bot=0.0, pilot_top=2.2, base_top=7.0,
    discA_bot=7.5, discA_top=12.5,
    cam_spacer_top=13.5,
    discB_bot=13.5, discB_top=18.5,
    carrier_bot=19.0, shoulder_top=21.0,      # lower-carrier shoulder / bearing seat start
    ring_bot=7.0, pinzone_top=19.0, ring_top=21.0,
    brg_out_bot=21.0, brg_out_top=28.0,
    cap_bot=21.0, cap_lip_bot=28.0, cap_top=30.0,
    ucar_bot=28.0, flange_bot=30.5, output_face=37.5,
    cam_bot=2.3, cam_collar_top=7.5,
    tip_pocket_top=24.0,
)

# ---------------------------------------------------------------- misc feature sizes
BASE_BORE_D   = 21.0     # clears the 18 mm cam collar
CAM = dict(collar_d=18.0, lobe_d=BRG_CAM["d"], spacer_d=17.0, bore_d=5.10, flat_from_axis=2.05,
           setscrew="M2", setscrew_z=4.6, setscrew_angle=90)   # M2x5 SHCS radially into an M2 insert, head counterbored flush
CARRIER_JOIN_R, CARRIER_JOIN_ANGLES = 12.0, [30, 150, 270]      # 3x M3x12, into inserts in P6
OUTPUT_INSERT_R, OUTPUT_INSERT_ANGLES = 22.0, [30, 90, 150, 210, 270, 330]  # 6x M3 inserts, output face

