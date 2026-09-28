# Print order: NEMA17 cycloidal drive

All files are binary STL in **millimetres**, already in print orientation, centred and flat on the bed.
Bambu Studio imports them at the right size. If it ever asks to convert units, answer **No**.

| # | File | Qty | Filament | Walls / infill | Why this position |
|---|---|---|---|---|---|
| 01 | `01_P0_coupon.stl` | 1 | PETG | 3 / 20% | Tests hole fits for your printer + filament. **Stop here and report results.** |
| 02 | `02_P3_cap.stl` | 1 | PETG | 4 / 40% | Tests the biggest press fit (6809 outer race, Ø58) on a quick, flat part |
| 03 | `03_P6_carrier_lower.stl` | 1 | PETG | 4 / 50% | Other half of the 6809 fit (Ø45), 625 pocket, dowel press holes |
| 04a | `04a_P5a_cam_lower.stl` | 1 | PETG | — / 100% | Lower cam: collar, set-screw insert and lower lobe. Tests the motor-shaft bore and the 6802 inner-race fit. |
| 04b | `04b_P5b_cam_upper.stl` | 1 | PETG | — / 100% | Upper cam: spacer and upper lobe, keyed to the shaft's D-flat. Small and quick. |
| 05 | `05_P4_disc_PRINT_2.stl` | **2** | PETG | — / 100% | 6802 outer-race fit plus the gear profile. In Bambu: right-click → Set instances → 2. |
| 06 | `06_P1_base.stl` | 1 | PETG | 4 / 40% | Motor mount. Not fit-critical, since it's located by the pilot and bolts. |
| 07 | `07_P2_ring.stl` | 1 | PETG | 5 / 40% | Pin ring, the longest print. Once the discs exist, you can test the gear mesh by hand as soon as it's off the bed. |
| 08 | `08_P7_carrier_upper.stl` | 1 | PETG | 4 / 50% | Output flange. Finishes the drive. |

## Checkpoint after 01

Parts 02–05 (including 04a and 04b) depend on the hole fits the coupon measures. Report back:

- **6802 pocket** (23.9 / 24.0 / 24.1): which one presses in firmly by hand.
- **625 pocket** (15.9 / 16.0 / 16.1): same.
- **Dowel holes** (2.90–3.20): which one grips the pin, and which one it slides through.
- **Insert holes** (M3 3.9–4.1, M2 3.1–3.3): which size the inserts melt into cleanly.
- **5.10 hole**: whether it slides onto the motor shaft.

If any fit needs changing, the affected files get re-exported with the same numbered names. 06 (base) and 07 (ring) are safe to print on the defaults while you wait for bearings.

## Slicer notes (Bambu)

- **Supports:** none needed on any part. The cam is now two pieces (04a, 04b), which also removed the old 2 mm overhang.
- **05 (discs):** turn on elephant-foot compensation (≈0.15 mm). The gear profile's bottom edge matters.
- **Seam:** "Aligned" or "Back". On 05 and 07, paint the seam off the gear flanks if you can.
- **Layer height:** 0.16–0.20 mm.

## Change log

- **2026-09-27:** The one-piece cam `04_P5_cam.stl` was replaced by `04a` + `04b`. The one-piece version cannot be assembled: the lower disc's bearing is trapped between the cam's collar and spacer. The old file was moved to `_to_delete/`; don't print it.
