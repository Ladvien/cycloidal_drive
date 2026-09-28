# NEMA17 Cycloidal Drive: Blender Build Spec for a 3D-Modeling Agent

**Date:** 2026-09-27
**Status:** Design complete. The reference build passes every check in Blender 5.0.1. Nothing has been printed yet.
**Audience:** an agent working in Blender through `bpy`, and the human who prints and assembles the parts.

Companion files in the repo (all paths relative to the repo root):

| File | What it is |
|---|---|
| `geometry/params.py` | **Single source of truth** for every dimension. The agent reads numbers from here and never hard-codes them. |
| `geometry/cycloid_geom.py` | numpy-only disc profile, ring-wall profile and disc kinematics. Runs inside Blender's Python. |
| `geometry/disc_profile.csv`, `geometry/ring_inner_profile.csv` | The two 2D outlines for the default parameters, in mm. |
| `geometry/build_drive.py` | Reference build, tested headless on Blender 5.0.1. Builds all parts, runs the checks and exports STLs. |
| `docs/design/img/*.png` | Reference renders the agent compares its own output against. |

The source article ([Firgelli, "Cycloidal Drive"](https://www.firgelliauto.com/blogs/mechanisms/cycloidal-drive)) covers the principles only: the ratio, one fewer lobe than pins, an eccentric bearing, and output holes of pin diameter plus 2e. Its tolerances (±0.005 mm eccentricity, ±0.002 mm pins) and its hardened-steel assumptions are for industrial drives and **do not apply** to a printed build. Everything below is derived for FDM printing and the hardware on hand.

---

## 1. Design summary

| Property | Value |
|---|---|
| Architecture | Fixed ring pins, two discs 180° out of phase, steel output pins, rotating output carrier |
| Ring pins / disc lobes | 16 / 15 |
| Ratio | **15 : 1, output turns the opposite way to the motor** (with the ring fixed and output taken from the disc, i = −N_lobes / (N_pins − N_lobes) = −15; the article's `Np/(Np−NL)` = 16 applies to the other arrangement) |
| Eccentricity e | 1.2 mm (k = e·N/R = 0.768) |
| Pin pitch radius R / pin Ø | 25.0 mm / 3.0 mm (printed, the same size as the steel dowels so they can drop in later) |
| Housing | Ø76 mm, 37.5 mm tall above the motor face (motor not included) |
| Output | Ø56 flange with 6× M3 heat-set inserts on a Ø44 bolt circle |
| Resolution | 200 steps × 15 = 3000 full steps per output rev (0.12° per full step) |
| Printed volume | ~ 127 cm³ solid across all parts (the discs are printed twice) |

The geometry was verified numerically. Profile: 15 lobes, valid polygon. Disc-to-pin clearance is the designed 0.10 mm. Disc-to-ring-wall clearance stays at 0.094 mm or more for both discs over one full motor revolution, with zero interference between any pair of parts at 25 poses. A disc mis-indexed by half a lobe produces 183 mm³ of collision, which proves the checker actually detects collisions.

---

## 2. Bill of materials

### 2.1 Printed parts (8 types, 9 prints)

| ID | Object name | Qty | Notes |
|---|---|---|---|
| P0 | `P0_coupon` | 1 | Tolerance coupon. **Print it first** and use it to tune `FIT` in `params.py`. |
| P1 | `P1_base` | 1 | Motor mount and housing floor |
| P2 | `P2_ring` | 1 | Pin ring with 16 printed pins and the relieved wall between them |
| P3 | `P3_cap` | 1 | Output bearing housing |
| P4 | `P4_disc_A`, `P4_disc_B` | 2 | Identical part printed twice. Disc B is installed rotated 180°. |
| P5a | `P5a_cam_lower` | 1 | Lower cam: collar with M2 set screw + lower lobe |
| P5b | `P5b_cam_upper` | 1 | Upper cam: spacer + upper lobe, keyed to the shaft's D-flat |
| P6 | `P6_carrier_lower` | 1 | Output pins press into it. Holds the 625 shaft-tip bearing. |
| P7 | `P7_carrier_upper` | 1 | Output flange. Clamps the output bearing's inner race against P6. |

### 2.2 Bearings to buy (not in the current parts stock)

| Qty | Bearing | d × D × B (mm) | Where |
|---|---|---|---|
| 2 | 6802-2RS | 15 × 24 × 5 | One in each disc, running on the cam lobes |
| 1 | 6809-2RS (61809) | 45 × 58 × 7 | Output carrier inside P3 |
| 1 | 625-2RS | 5 × 16 × 5 | Motor-shaft tip, inside P6. Optional, but it stiffens the input a lot. |

### 2.3 Hardware from stock

| Qty | Item | Use |
|---|---|---|
| 6 | 3 × 30 dowel | Output pins: pressed into P6, running through both discs, flush with P7's face |
| 2 | 3 × 30 dowel | Housing alignment through P1 + P2 + P3 (7 + 14 + 9 = 30 mm, flush both ends) |
| 2 | 3 × 30 dowel | Spare |
| 4 | M3 × 8 SHCS | Motor to P1. The heads recess into P1's top face. |
| 6 | M3 × 25 SHCS | P3 → P2 → heat-set inserts in P1 (5.2 mm engagement; 22 is too short and 30 bottoms out) |
| 3 | M3 × 12 SHCS | P7 → heat-set inserts in P6 |
| 1 | M2 × 5 SHCS | Cam set screw, radial, into an M2 insert, head counterbored flush |
| 19 | M3 heat-set insert | 6 in P1, 3 in P6, 6 in P7 (output face), 4 in P3 (drive mounting) |
| 1 | M2 heat-set insert | P5a collar |
| — | Grease | PTFE or lithium grease on the pins, the disc profiles and the output-pin holes |

The default insert holes are M2 Ø3.2 × 4, M3 Ø4.0 × 6 and M4 Ø5.6 × 8.5 (common "Ruthex/CNC Kitchen" style sizes). **Measure your inserts** and change `SCREW[...]["ins_d"/"ins_depth"]` if yours differ.

---

## 3. Conventions the agent must follow

1. **Units:** `scene.unit_settings.system='METRIC'`, `length_unit='MILLIMETERS'`, `scale_length=0.001`. That makes 1 Blender unit equal 1 mm. Export STL with `global_scale=1.0, use_scene_unit=False` so the numbers in the file are millimetres.
2. **Frame:** the origin is the centre of the NEMA17 mounting face. +Z runs from the motor toward the output. Motor angle θ = 0 puts lobe A's offset on +X.
3. **Build in assembly position.** Every part is modeled where it sits in the assembled drive. Print orientation is applied only on export (section 8).
4. **Collections:** `drive` holds the printable parts, `reference` holds the motor, shaft, dowels and coupon (never exported as drive parts), and `cutters` holds temporary tools and must be empty at the end.
5. **Names:** use exactly the object names in 2.1. The checks look them up by name.
6. **Holes are circumscribed n-gons** (the flats sit at the nominal radius, `circle_pts(..., circumscribe=True)`), so polygon holes never print undersize. Shafts and outer diameters use inscribed n-gons. Segment counts: 64 below Ø8, 96 below Ø30, 192 above that.
7. **Booleans:** use a Boolean modifier with solver `MANIFOLD` (Blender 4.5 or later; fall back to `EXACT`). Bake it with `bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))` rather than `bpy.ops.object.modifier_apply` (no context problems in background mode). Let cutters overshoot every face they pierce by at least 1 mm. For a union, overlap the joined solids by 0.01 mm so they don't share a coplanar face.
8. **2D outlines to solids:** make a bmesh face from the CSV points, `extrude_face_region`, translate in Z, then `recalc_face_normals`. Keep the full point resolution (1800 disc points, 1440 ring points). Do not decimate the disc profile.
9. **Never hand-type a dimension.** Import `params.py` and `cycloid_geom.py`. Changing a parameter and re-running must give a consistent drive.

---

## 4. Cycloid geometry

For N ring pins on pitch radius R, pin radius r_p, eccentricity e and profile clearance c, the disc outline (N − 1 lobes, in the disc's own frame) is the equidistant curve of the epitrochoid:

```
ψ(t) = atan2( sin((1−N)t),  R/(e·N) − cos((1−N)t) )
x(t) =  R·cos t − (r_p + c)·cos(t + ψ) − e·cos(N·t)
y(t) = −R·sin t + (r_p + c)·sin(t + ψ) + e·sin(N·t)        t ∈ [0, 2π)
```

This is implemented as `cycloid_geom.disc_profile()`. For the defaults the disc radius runs from 22.20 to 24.60 mm.

**Kinematics** (`cycloid_geom.disc_pose(θ, phase)`):

- Disc centre = e·(cos(θ + phase), sin(θ + phase)).
- Disc rotation = −θ/(N − 1) + phase.
- Disc A has phase = 0. Disc B has phase = π: the **same part rotated 180°**. This works because 15 lobes and 6 holes both map onto themselves under a 180° turn.
- The output carrier rotates by −θ/(N − 1) about the main axis.

**Ring wall.** The lobe tips sweep out to r = 25.8 mm, which is past the pin circle (25.0). A plain bore through the pin centres would collide with the disc. The ring's inner outline is therefore (the swept envelope of the disc over a full revolution + 0.40 mm), with the 16 pin circles added back as solid (`cycloid_geom.ring_inner_profile()`). The wall runs from r = 23.50 at a pin face to 26.20 midway between pins. About 88% of each printed pin's cross-section is embedded in the wall, so the pins are well supported.

**Output holes** in each disc: 6 × Ø(3.0 + 2e + 0.2) = **Ø5.6** on R_out = **17.1** at 0°, 60°, … 300°. The web is 2.2–2.3 mm from the bearing bore to a hole and from a hole to the profile root.

---

## 5. Axial stack

All Z values are in mm from the motor mounting face and come from `params.Z`.

| z from → to | Contents |
|---|---|
| −40 → 0 | NEMA17 (reference only). Pilot boss Ø22 × 2. Shaft Ø5, 24 long, 15 mm D-flat on +Y. |
| 0 → 7.0 | **P1 base** (pilot recess 0 → 2.2) |
| 2.3 → 7.5 | P5a cam collar Ø18, inside P1's Ø21 bore |
| 7.0 → 21.0 | **P2 ring**. Pin zone 7.0 → 19.0, Ø52 bore 19.0 → 21.0. |
| 7.5 → 12.5 | Disc A + 6802 on lobe A (cam lobe Ø15 centred at +e) |
| 12.5 → 13.5 | Cam spacer Ø17, concentric with the shaft. Separates the two inner races. |
| 13.5 → 18.5 | Disc B + 6802 on lobe B (centred at −e) |
| 19.0 → 28.0 | **P6 lower carrier**: shoulder Ø48 19 → 21, bearing seat Ø45 21 → 28, 625 pocket Ø16 19 → 24 |
| 21.0 → 28.0 | 6809 output bearing. The outer race sits between P2's top face and P3's lip; the inner race is clamped between the P6 shoulder and P7. |
| 21.0 → 30.0 | **P3 cap**: bearing bore Ø58 21 → 28, lip Ø52 28 → 30 |
| 28.0 → 37.5 | **P7 upper carrier**: Ø49 28 → 30.5, output flange Ø56 30.5 → 37.5 |
| 7.5 → 37.5 | 6 output dowels (3 × 30) on R 17.1 |
| 0 → 30.0 | 2 alignment dowels on R 34 at 30° and 210° |

Running gaps: 0.5 mm between disc A and P1, between the two discs (the cam spacer), and between disc B and P6. There is also 0.5 mm between P7's flange and P3's top.

See `img/half_section.png` for the stack.

---

## 6. Part-by-part build steps

Angles are measured from +X, counter-clockwise when viewed from +Z. "Insert" means a heat-set insert hole of `SCREW[size]` ins_d × ins_depth. "Cbore" means counterbore Ø(head_d + 0.7), depth head_h + 0.2 unless stated.

### P1 `P1_base` (z 0 → 7)

1. Solid cylinder Ø76, z 0 → 7.
2. Cut the pilot recess: Ø22.4, z −1 → 2.2 (from the motor side).
3. Cut the through bore Ø21. It clears the Ø18 cam collar and lets the base slide over a cam that is already fitted.
4. Motor holes: 4 × Ø3.4 through at (±15.5, ±15.5). Cbore each **from the top face**, Ø6.2 × 3.5 deep, so the M3 × 8 heads sit 0.5 mm below the disc A running face. The 3.5 mm floor gives 4.5 mm of thread engagement in the motor.
5. 6 × M3 inserts from the top face on R 34 at 0°, 60°, … 300°.
6. 2 × Ø2.95 (dowel press fit) through on R 34 at 30° and 210°.

### P2 `P2_ring` (z 7 → 21)

1. Solid cylinder Ø76, z 7 → 21.
2. Cut the pin zone: extrude `ring_inner_profile.csv` over z 6 → 19.0. This leaves the 16 pins and the relieved wall.
3. Cut the upper bore Ø52 over z 18.99 → 22. This makes a seat for the outer race of the 6809 on the top face at r ≥ 26. The inner race runs at r ≤ 24.8, so it can't rub.
4. 6 × Ø3.4 through on R 34 at 0°, 60°, … (housing bolts).
5. 2 × Ø3.10 (dowel slip fit) through on R 34 at 30° and 210°.

### P3 `P3_cap` (z 21 → 30)

1. Solid cylinder Ø76, z 21 → 30.
2. Bearing bore Ø58 (+ `FIT.bearing_press`), z 20 → 28, open at the bottom.
3. Lip bore Ø52, z 27.99 → 31. This leaves a 2 mm lip over the outer race.
4. 6 × Ø3.4 through on R 34 at 0°, 60°, … Cbore each from the top, Ø6.2 × 3.2 (leaves 1.9 mm of wall to the bearing bore).
5. 2 × Ø3.10 slip holes on R 34 at 30° and 210°.
6. 4 × M3 inserts from the top face on R 34 at 90°, 150°, 270° and 330°, for mounting the drive to a bracket. The bracket needs a Ø60 or larger clearance hole for the rotating flange.

### P4 `P4_disc_A` / `P4_disc_B` (built z 0 → 5, centred on their own axis)

1. Extrude `disc_profile.csv` over z 0 → 5.
2. Bearing bore Ø24.0 (+ `FIT.bearing_press`), through.
3. 6 × Ø5.6 through on R 17.1 at 0°, 60°, … 300°.
4. Orientation dimple Ø1.2 × 0.4 deep in the top face on R 19.8 at 30°.
5. Placement: disc A at z = 7.5, pose `disc_pose(θ, phase=0)`. Disc B at z = 13.5, pose `disc_pose(θ, phase=π)`. Export one STL and print it twice.

### P5a `P5a_cam_lower` and P5b `P5b_cam_upper` (split at z 12.5)

The cam is two pieces. A one-piece cam cannot be assembled: disc A's 6802 (15 mm bore) would be trapped on the lower lobe between the Ø18 collar and the Ø17 spacer. Both pieces key to the shaft's D-flat, so the lobes are 180° apart automatically.

1. **P5a:** collar Ø18, z 2.3 → 7.5, centred on the axis, unioned with lobe A Ø14.95 (15 + `FIT.shaft_press`), z 7.5 → 12.5, centre (+1.2, 0).
2. **P5b:** spacer Ø17, z 12.5 → 13.5, centred on the axis, unioned with lobe B Ø14.95, z 13.5 → 18.5, centre (−1.2, 0). The spacer touches both inner races (inner-ring OD ≈ 17.9) and stays at least 0.85 mm inside the outer races (≈ 21.1).
3. **Bore** (`_cam_bore`): Ø5.10 round up to z_flat = shaft_len − flat_len + 0.5 = **9.5**, D-shaped above it (a Ø5.10 circle cut flat at y = +2.05). P5a is round from 2.3 to 9.5 and D-shaped from 9.5 to 12.5. P5b is D-shaped over its whole length.
4. **Set screw in P5a**, radial along +Y (setscrew_angle 90°) at z 4.6:
   - M2 insert hole Ø3.2 from the axis out through the collar;
   - counterbore Ø4.5 from r 7 to r 9 so an **M2 × 5** SHCS seats flush and its tip reaches the shaft.
5. **Retention:** nothing clamps P5b. The 625's inner ring on the shaft tip sits 0.5 mm above it. Print both pieces at 100% infill. Neither has an overhang worth supporting.

### P6 `P6_carrier_lower` (z 19 → 28)

1. Shoulder Ø48, z 19 → 21, unioned with the bearing seat Ø44.95 (45 + `FIT.shaft_press`), z 20.99 → 28.
2. 625 pocket Ø16 (+ `FIT.bearing_press`), z 18 → 24. Shaft-tip relief Ø8, z 24 → 25.
3. 6 × Ø2.95 dowel press holes through on R 17.1 at 0°, 60°, …
4. 3 × M3 inserts from the top face (z 28) on R 12 at 30°, 150° and 270°.

### P7 `P7_carrier_upper` (z 28 → 37.5)

1. Hub Ø49, z 28 → 30.5 (it clamps the 6809 inner race and clears P3's Ø52 lip). Unioned with the output flange Ø56, z 30.49 → 37.5.
2. 6 × Ø3.10 dowel slip holes through on R 17.1 at 0°, 60°, … The dowel tops end flush with the output face.
3. 3 × Ø3.4 through on R 12 at 30°, 150° and 270°. Cbore each from the output face, Ø6.2 × 3.2. With M3 × 12 screws that gives 5.7 mm of engagement in P6's inserts.
4. 6 × M3 inserts from the output face on R 22 at 30°, 90°, … 330° (the output bolt pattern).

### P0 `P0_coupon` (150 × 42 × 6 plate)

- **Back row:** blind seats 5 mm deep (1 mm floor): Ø23.9 / 24.0 / 24.1 (for the 6802) and Ø15.9 / 16.0 / 16.1 (for the 625).
- **Front row:** dowel holes through at Ø2.90 / 2.95 / 3.00 / 3.05 / 3.10 / 3.20; M3 insert holes Ø3.9 / 4.0 / 4.1; M2 insert holes Ø3.1 / 3.2 / 3.3; a Ø5.10 slip-test bore for the motor shaft.

The Ø58 and Ø45 fits are tested on P3 and P6 directly, because those parts are cheap.

---

## 7. Verification gates (the agent must pass all of these before exporting)

`build_drive.py → run_checks()` implements every gate.

1. **Manifold:** every exported part has 0 edges with a face count other than 2, and positive signed volume (normals facing out).
2. **Interference sweep:** at 25 motor angles over 0 → 360°, pose the moving parts (`pose(θ)`: cam +θ, discs per `disc_pose`, carriers and output dowels −θ/15). Measure the intersection volume of each pair below with a MANIFOLD `INTERSECT` boolean. It must be under 0.05 mm³.
   - Pairs: base–ring, ring–cap, base–P5a, base–disc A, ring–disc A, ring–disc B, disc A–disc B, disc B–lower carrier, ring–lower carrier, cap–lower carrier, cap–upper carrier, lower–upper carrier, base–motor boss, P5a–shaft and P5b–shaft (with the D-flat modeled), P5a–P5b, P5b–lower carrier, disc A–output pin, disc B–output pin.
3. **Positive control:** rotate disc A by half a lobe (π/15). Its intersection with P2 **must** be over 1 mm³. If it isn't, the checker is broken and gate 2 means nothing.
4. **Visual checks** (the agent's multi-angle inspection): render the assembly, an exploded view, a top view of the pin zone (P3, P6, P7 and disc B hidden) and a half-section cut at the XZ plane. Compare them with `img/assembly.png`, `img/exploded.png`, `img/top_pinzone.png` and `img/half_section.png`. In the top view the disc must show 15 lobes inside 16 pins with a thin even gap. In the section, the pins must pass through both discs.
5. **Parametric re-run:** change `E` to 1.0 and `C_PROF` to 0.15, rebuild, and confirm that gates 1–3 still pass. Then restore the defaults.
6. **Assembly paths:** `python3 guide/make_guide.py` slides every part along its insertion path, in assembly order, and measures collisions with the parts already installed. It exits 1 on any blocked step. Gates 1–5 check the finished assembly only; this gate is what catches a part that can't physically get to its place. It has its own positive control: the old one-piece cam must be reported as blocked, or the run fails.

Expected mesh volumes at the defaults (cm³): P1 28.12, P2 34.30, P3 16.74, P4 5.77 each, P5a 1.93, P5b 0.99, P6 13.07, P7 20.61, P0 27.31. A difference of more than 2% means a feature is missing or doubled.

---

## 8. Export and printing

| Part | Face on the bed | Supports | Notes |
|---|---|---|---|
| P0 | bottom | none | Print first |
| P1 | z = 0 (motor side) | none | |
| P2 | z = 7 (bottom) | none | Pins print as vertical ribs. 4+ perimeters. |
| P3 | **top face** (flipped) | none | The lip is on the bed and the bearing bore opens upward |
| P4 ×2 | either face | none | XY accuracy matters most here. Turn on elephant-foot compensation (≈ 0.15) or chamfer the bottom edge. |
| P5a | collar end | none | 100% infill |
| P5b | spacer end | none | 100% infill |
| P6 | z = 19 (shoulder down) | none | |
| P7 | **output face** (flipped) | none | The Ø49 hub prints last, on top |

- **STL export:** `bpy.ops.wm.stl_export(filepath, export_selected_objects=True, global_scale=1.0, use_scene_unit=False, apply_modifiers=True)`, run on a copy that has been zeroed, flipped if needed, and moved to z_min = 0. `export_stls()` writes the numbered, print-ordered names in `PRINT_ORDER` (e.g. `04a_P5a_cam_lower.stl`) to `<out>/stl/`. There is one disc STL, `05_P4_disc_PRINT_2.stl`.
- **Material:** PLA+ or PETG. PLA is stiffer and more accurate; PETG is tougher and creeps less under heat. Use 0.16–0.20 mm layers, 4–6 perimeters, and 40%+ infill (100% on P5a/P5b, and on P4 if you like).
- **Seams:** "aligned" or "rear". On the discs, keep the seam off the lobe flanks if the slicer lets you paint seams.

---

## 9. Assembly order (for the human)

The illustrated guide is generated from the design: `python3 guide/make_guide.py` writes `docs/assembly/<date>-cycloidal-drive-assembly-guide.pdf` and a `.md` alongside it. Regenerate it after any change to `geometry/`. In short:

1. Tune `FIT` from the P0 coupon, rebuild, then print the rest.
2. Heat-set every insert: P1 (6), P3 (4), P6 (3), P7 (6), P5a (1 × M2).
3. Press a 6802 into each disc and the 625 into P6. Press the 6 output dowels into P6, using P7 (9.5 mm thick) as the depth stop.
4. P5a onto the shaft, collar on a 0.3 mm paper shim, then tighten the M2 × 5. Base over it with 4 × M3 × 8. Press the 2 alignment dowels into the base.
5. Ring over the alignment dowels (grease the pins). Then disc A onto the lower lobe, **then P5b**, then disc B (dimple opposite disc A's).
6. 6809 into the cap (lip down). Stand P6 on its long pin ends and lower the cap onto it. Fit P7 through the lip with 3 × M3 × 12.
7. Lower the output assembly onto the drive. Fit 6 × M3 × 25 and tighten in a star pattern.

---

## 10. Known risks and upgrade paths

- **Shaft length:** the 625 tip bearing needs `MOTOR.shaft_len` ≥ 23. On a shorter motor, drop the 625 and leave the pocket empty. The input then runs cantilevered on the motor's own bearings.
- **D-flat length:** the cam's D-section starts at z = shaft_len − flat_len + 0.5. Measure your motor and set `flat_len`. If the flat is too short, the cam won't slide on.
- **Printed ring pins wear.** This is the first thing to fail under load. Upgrade: 16 more 3 × 30 dowels (two more packs), cut to 20 mm and held in holes in P1 and a thicker P2. That needs a small geometry change: add pin holes at R 25 and rotate the pin pattern 11.25° so it misses the motor-screw counterbores at 45°.
- **Backlash** mostly comes from `C_PROF` (0.10), the Ø5.6 output holes and printer accuracy. Once the drive runs smoothly, reprint the discs with `C_PROF` 0.05.
- **Torque:** a typical NEMA17 gives 0.3–0.5 N·m. At 15:1 the ideal output is 4–7 N·m before losses. The printed pins and disc webs will likely set the real limit lower. This hasn't been tested, so measure it before relying on it.

---

## 11. Paste-ready prompt for the modeling agent

```text
You are building a 3D-printable NEMA17 cycloidal drive in Blender via bpy.

Inputs (in repo): geometry/params.py (ALL dimensions), geometry/cycloid_geom.py (disc/ring
profiles + disc_pose kinematics), docs/design/2026-09-27-cycloidal-drive-blender-build-spec.md
(sections 3-8 are the contract), docs/design/img/*.png (reference renders).

Rules:
- 1 BU = 1 mm (scale_length 0.001). Origin = motor face centre, +Z toward output.
- Import params.py and cycloid_geom.py; never hand-type a dimension.
- Build each part in assembly position, exact object names P0_coupon, P1_base, P2_ring, P3_cap,
  P4_disc_A, P4_disc_B, P5a_cam_lower, P5b_cam_upper, P6_carrier_lower, P7_carrier_upper, in collection "drive";
  motor/shaft(with D-flat)/dowels in "reference".
- Holes = circumscribed n-gons (64/96/192 segs). Booleans: MANIFOLD solver (EXACT fallback),
  cutters overshoot 1 mm, bake via new_from_object on the evaluated object.
- Work one part at a time: build -> manifold check -> render 3 views -> compare with spec table.
- Then run spec section 7 gates 1-5. Do not export until all pass; report the gate table.
- Export STLs per spec section 8 to stl/, save cycloidal_drive.blend.
If a gate fails, fix the geometry; never loosen a gate or edit params.py to make a check pass
without saying so. geometry/build_drive.py is a working reference implementation - diff your
result against it (volumes in section 7) when stuck.
```

---

## Change log

- **2026-09-27:** Split the cam into P5a + P5b. The one-piece cam could not be assembled (disc A's bearing was trapped between collar and spacer); the assembly-guide path check found it. Added gate 6 (assembly paths), `SCREWS_USED`/`INSERT_LEN` in `params.py`, and numbered STL export.
