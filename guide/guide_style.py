"""guide_style.py - colours shared by the Blender render stage and the PDF/markdown compose stage (no bpy)."""

COL = {  # sRGB 0-255
    "P1_base": (70, 115, 180), "P2_ring": (225, 140, 45), "P3_cap": (85, 165, 100),
    "P4_disc_A": (205, 75, 75), "P4_disc_B": (205, 75, 75),
    "P5a_cam_lower": (230, 195, 55), "P5b_cam_upper": (245, 215, 110),
    "P6_carrier_lower": (55, 170, 175), "P7_carrier_upper": (140, 140, 150), "P0_coupon": (200, 200, 200),
    "steel": (185, 190, 200), "seal": (35, 35, 38), "screw": (55, 55, 62), "brass": (205, 160, 55),
    "motor": (60, 62, 68), "motor_face": (165, 168, 175), "arrow": (255, 95, 20), "grease": (250, 245, 225),
}
MUTED_TO = (232, 232, 234)   # already-installed parts fade toward this

def base_colour(name):
    if name in COL: return COL[name]
    if name.endswith("_seal"): return COL["seal"]
    if name.startswith(("HW_6", "HW_pin")) or name == "HW_shaft": return COL["steel"]
    if name.startswith("HW_ins"): return COL["brass"]
    if name.startswith("HW_scr"): return COL["screw"]
    if name in ("HW_motor_face", "HW_motor_boss"): return COL["motor_face"]
    if name.startswith("HW_motor"): return COL["motor"]
    return (150, 150, 150)

# page palette (hex) for the PDF
INK, MUTE, ACCENT = "#1b1f24", "#5b6470", "#eb5519"
CHECK_FILL, CHECK_EDGE = "#eef7f0", "#3f8f55"
TIP_FILL, TIP_EDGE = "#fff5e8", "#d9822b"
BLOCK_FILL, BLOCK_EDGE = "#fdecec", "#c0392b"
