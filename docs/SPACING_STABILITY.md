# Stable measurement support for blurred scans

The v6 [paired-section refinement](SPACING_REFINEMENT.md) kept counts stable but its measurement point sets still expanded with the detection allowance. The worst case was G–H, seed 123 / 25 mm: measured 179.33 mm versus published tape 146.05 mm, error **+33.28 mm**. Off-axis/depth support and the measured axial span changed with the candidate envelope. Without point-level semantic truth, removed real-scan points cannot all be certified as clutter.

The v7 method separates candidate detection from measurement support. At the identical worst-case setting G–H now measures **167.21 mm**, error **+21.16 mm** (36.4% lower). Baseline seed 123 / 20 mm MAE falls **9.51 → 8.06 mm**, maximum **22.19 → 21.16 mm**, D–E **+16.35 → +15.81 mm**. Every interval remains scored; none is discarded to lower the error.

## Two explicit support sets

Detection is unchanged. The supplied allowance still affects the candidate depth/envelope, support, endpoints, confidence heuristic and acceptance decision. Native bars/groups keep the detector's original source IDs. Baseline native bars/evidence/straight spacing are exactly unchanged; straight-representative MAE remains **11.56 mm**. Default mode (allowance zero) does not run the extra measurement fit.

Measurement starts from the same ROI after broad-surface rejection **before** the allowance-dependent depth crop. The selected depth-mode centre/normal/rank still identify the requested layer. A fixed half-width of **two design diameters** selects its metrology band. Three-of-four scale consensus proposals are refined in a radial window of **three diameters**, with the existing support, continuity, length, coverage, direction and residual checks. These are fixed geometric heuristics, not estimated sensor blur, an uncertainty bound, or a new measured diameter. They are applied uniformly to every case without using reference spacings, labels or expected counts.

For this #5/15.875 mm input the half-band is 31.75 mm and radial window 47.625 mm. Both are recorded with their geometric basis. Measurement track source IDs, endpoints, residuals and coverage remain separate from native candidate evidence. The fixed pipeline is recomputed on each analysis; it does not reuse previously measured distances.

Require unique candidate-to-measurement matches in both directions: transverse 3D centre distance at most two diameters, axial overlap at least the configured minimum length and 80% of the weaker span. Both one-to-many and many-to-one ambiguities remain unmatched; no assignment is forced by lowest error. A reported adjacent native pair also needs adjacent matched measurement tracks. Unsupported/ambiguous cases remain null, with no fallback to the native straight distance.

The same paired-section metric is retained: full cells of width two diameters inside the **measurement tracks' common observed extent**, at least three points on both sides, 75% paired coverage and the minimum occupied length. It never extrapolates beyond those measurement supports. These extents may differ from the native detection envelope; original native and measurement extents are both preserved. Section centre/support ordering is explicitly rebound to native bar IDs. Spatial quantiles remain spatial variation, not calibrated uncertainty. Endpoint review leaves these pre-review scan measurements unchanged and the UI explains the separate measurement window.

## All tested settings

Same hash-verified source, physical label registration, tape references, assisted ROI, 180,000-point uniform sample and design diameter as before. The runner now also checks sampling seed 789 in addition to 123/456: **15 cases** over allowance 15/17.5/20/22.5/25 mm. Every case detects **12/12 and 8/8**, passes the frozen identity regions and scores **18/18** intervals.

| Seed | Allowance mm | Count X/Y | Verified intervals | MAE mm | Maximum error mm | Prior maximum mm |
|---:|---:|---|---:|---:|---:|---:|
| 123 | 15.0 | 12/8 | 18/18 | 8.06 | 21.16 | 20.44 |
| 123 | 17.5 | 12/8 | 18/18 | 8.06 | 21.16 | 21.98 |
| 123 | 20.0 | 12/8 | 18/18 | 8.06 | 21.16 | 22.19 |
| 123 | 22.5 | 12/8 | 18/18 | 8.06 | 21.16 | 27.03 |
| 123 | 25.0 | 12/8 | 18/18 | 8.06 | 21.16 | 33.28 |
| 456 | 15.0 | 12/8 | 18/18 | 7.98 | 18.20 | 18.83 |
| 456 | 17.5 | 12/8 | 18/18 | 7.98 | 18.20 | 18.86 |
| 456 | 20.0 | 12/8 | 18/18 | 7.98 | 18.20 | 20.03 |
| 456 | 22.5 | 12/8 | 18/18 | 7.98 | 18.20 | 22.85 |
| 456 | 25.0 | 12/8 | 18/18 | 7.98 | 18.20 | 29.02 |
| 789 | 15.0 | 12/8 | 18/18 | 7.79 | 18.79 | — |
| 789 | 17.5 | 12/8 | 18/18 | 7.79 | 18.79 | — |
| 789 | 20.0 | 12/8 | 18/18 | 7.79 | 18.79 | — |
| 789 | 22.5 | 12/8 | 18/18 | 7.79 | 18.79 | — |
| 789 | 25.0 | 12/8 | 18/18 | 7.79 | 18.79 | — |

Within each seed, every interval and the full measurement-evidence fingerprint are identical across the five allowances: **0 mm observed allowance-induced drift**. This invariance follows from separating the measurement window; it is not zero measurement error or proof of general robustness. Changing the actual scan in a controlled synthetic test changes the measured spacing, demonstrating that measurements are not frozen constants.

Across the three resamples MAE is **7.79–8.06 mm**, maximum error **18.20–21.16 mm**. The greatest per-interval range between these resamples is **2.96 mm**; resampling one acquisition does not establish independent field accuracy. The prior narrow seed-123 / 15 mm case had MAE 7.83 mm versus current 8.06 mm, a 0.23 mm tradeoff; all prior values remain in the table.

The JSON runner stores all detailed profiles/source IDs once per SHA-256 evidence fingerprint, with references from every independently computed case. There are three unique evidence sets in this grid, one per sampled source. Hashes are checked against the exact serialized profiles; numeric summaries never substitute for source evidence. [Compact complete results](data/wingwall_stability_summary.json).

## Every baseline interval

| Interval | Tape mm | v6 baseline error mm | v7 measured mm | v7 error mm |
|---|---:|---:|---:|---:|
| X:1-2 | 215.90 | +13.03 | 227.81 | +11.91 |
| X:2-3 | 223.52 | +0.64 | 226.07 | +2.55 |
| X:3-4 | 223.52 | -8.56 | 215.17 | -8.35 |
| X:4-5 | 241.30 | +5.46 | 246.76 | +5.46 |
| X:5-6 | 236.22 | +12.36 | 235.85 | -0.37 |
| X:6-7 | 223.52 | -15.95 | 224.73 | +1.21 |
| X:7-8 | 236.22 | -2.18 | 234.35 | -1.87 |
| X:8-9 | 223.52 | +4.83 | 228.50 | +4.98 |
| X:9-10 | 210.82 | +7.17 | 218.27 | +7.45 |
| X:10-11 | 190.50 | +2.98 | 194.28 | +3.78 |
| X:11-12 | 210.82 | -8.46 | 201.00 | -9.82 |
| Y:A-B | 248.92 | -18.10 | 231.20 | -17.72 |
| Y:B-C | 223.52 | +5.84 | 229.53 | +6.01 |
| Y:C-D | 241.30 | -3.80 | 237.13 | -4.17 |
| Y:D-E | 203.20 | +16.35 | 219.01 | +15.81 |
| Y:E-F | 139.70 | -11.94 | 128.19 | -11.51 |
| Y:F-G | 190.50 | +11.28 | 201.37 | +10.87 |
| Y:G-H | 146.05 | +22.19 | 167.21 | +21.16 |

Remaining substantial baseline errors include G–H +21.16 mm, A–B −17.72 mm and D–E +15.81 mm. Fixed windows remove coupling to this particular allowance, not sensitivity to design diameter, ROI, direction, layer rank or the metrology-window design itself. Crooked/partially scanned steel, nearby layers/clutter and scanner scale/calibration remain unresolved. The published tape does not locate an exact axial station, so observed-section medians are not independently registered tape stations. No construction compliance verdict or millimetre-accuracy claim is produced.

## Verification and scope

**124 tests pass on each core**, zero failures/skips: custom IngeTrazo `1ee32a6` and upstream `69d9400468e81c5a91ba88a56a824cd240994a17`. New tests use known clutter that enters wider detection bands but lies outside the independent measurement layer, preserve three bars and 150/150 mm in five settings and two frames, verify response to an actual 10 mm geometry change, reject ambiguous/missing/nonoverlapping/far matches, maintain native-to-measurement index ordering, and refuse unsupported measurements. Original tests cover source precision/units/ROI/LAZ, surface rejection, native Undo/Redo, offscreen UI and IGZ persistence of both evidence sets.

The original real Rohbau floor patch and rotated wall still yield zero bars in default/noise modes. Original blurred synthetic 150/150/300 mm spacings remain within 2 mm; paired adjacent 150/150 mm remain within 2 mm. Final t1/t8 reruns preserve bars, point IDs, evidence and straight spacing exactly (0/0 and 4/4). t8 still has no independent Figure 13 label anchors: 0/32 verified tape pairs, error null. No missing fifth line is manufactured.

Reproduce with the existing `tools/fetch_wingwall_data.py` and `tools/run_wingwall_trial.py --data-dir ... --output-dir ... --sensitivity` in disposable checkouts using the documented PYTHONPATH/offscreen setup. This still uses an assisted crop/direction/layer and a point-count cap; it is not automatic full-scan processing. Two support fits add synchronous analysis work; background cancellation remains future work.

All source/reference attribution and discrepancies remain in [WINGWALL_TRIAL.md](WINGWALL_TRIAL.md). No operational checkout, plugin installation, live CAD document or production file was modified. PR remains draft. Survey calibration/uncertainty, additional independent acquisitions, curved native geometry, live OpenGL validation and automatic cloud-array reload remain incomplete.
