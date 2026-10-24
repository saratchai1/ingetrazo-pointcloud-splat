# Spacing refinement and parameter stability

This builds on the [source-anchored wingwall trial](WINGWALL_TRIAL.md). The original checkout was clean at `5b6b1ac`; work remains in the isolated feature branch. Source hashes, ROI, sampling, diameter, reference values, manual identity regions and physical label registration are unchanged.

## What changed

The old proposal finder could lose an edge peak because its histogram ended before the Gaussian tail, and accepted some peaks at only one smoothing scale. Histograms now extend three smoothing sigmas past both observed limits. Proposals need matching peaks (within two design diameters) at three of four fixed diameter-based scales: 0.75, 1, 1.25 and 1.5 diameters. Every scale inventory, match distance and vote is retained. The supplied noise allowance still sets the support/depth envelope, but no longer selects a single proposal scale. There is no expected-count, spacing, equal-grid, label or reference-error input.

Spacing also needs a measurement matched to observed geometry. D and E have lateral drift and unequal axial visibility: one whole-track median samples a different part of the structure than the other. A new **scan support spacing** uses transverse median positions in paired axial sections at the same observed locations. It is an additional explicitly named metric; it does not replace or relabel CAD centreline distance.

For adjacent candidates ordered along the supplied layer plane, intersect the detected endpoint spans. Start cells at the common overlap boundary (translation invariant), use cell width two design diameters, and discard an incomplete terminal cell. Each section needs at least three source points on each bar. Require at least 75% paired coverage and at least the configured minimum length of shared occupied cells. Without this support, the pair remains unavailable; no extrapolation or fallback to the straight model is allowed. Each section stores its axial interval, both transverse centres, both support counts and distance. The aggregate is the median distance, with a 10–90% **spatial variation** range, explicitly not calibrated uncertainty. Original source IDs in each bar make the section evidence reconstructible.

UI/export retain both straight centreline spacing and scan support spacing. The latter is explicitly based on detected points **before endpoint edits**, so manual geometry review cannot silently change or validate it. Native geometry and one-command Undo/Redo remain unchanged. Original fit support/residuals still describe the straight representative, not a newly fitted curved native bar.

## Baseline results: distinguish the metrics

| Detector and measurement | MAE mm | Maximum absolute error mm | D–E signed error mm |
|---|---:|---:|---:|
| Previous detector, whole-track straight representatives | 11.33 | 24.23 | +24.23 |
| Current detector, whole-track straight representatives | 11.56 | 24.38 | +24.38 |
| Previous detector, new paired-section metric (ablation) | 9.20 | 23.73 | +16.50 |
| Current detector, new paired-section metric | **9.51** | **22.19** | **+16.35** |

The measured scan support D–E interval is **219.55 mm**, versus tape **203.20 mm**. Its discrepancy falls by about 32.5% compared with the previously reported straight interval. Baseline aggregate discrepancy falls about 16.1%. This improvement comes from comparing co-located observed sections; the unchanged straight-family representation has not become more accurate. The consensus detector principally improves count stability and slightly worsens baseline straight MAE. The ablation exposes that tradeoff instead of attributing the metric improvement to detection alone.

Tape readings do not declare an exact axial measurement station. Paired-section medians summarize shared visible support, not an independently established tape station. Local curvature, partial surfaces, depth, blur and unknown calibration remain. These are development comparisons on one source, not held-out evidence or a compliance decision.

| Interval | Tape mm | Old straight error mm | Paired-section measured mm | Paired error mm |
|---|---:|---:|---:|---:|
| X:1-2 | 215.90 | +15.27 | 228.93 | +13.03 |
| X:2-3 | 223.52 | +1.73 | 224.16 | +0.64 |
| X:3-4 | 223.52 | -13.06 | 214.96 | -8.56 |
| X:4-5 | 241.30 | +5.88 | 246.76 | +5.46 |
| X:5-6 | 236.22 | +7.94 | 248.58 | +12.36 |
| X:6-7 | 223.52 | -16.19 | 207.57 | -15.95 |
| X:7-8 | 236.22 | -0.52 | 234.04 | -2.18 |
| X:8-9 | 223.52 | +3.59 | 228.35 | +4.83 |
| X:9-10 | 210.82 | +8.13 | 217.99 | +7.17 |
| X:10-11 | 190.50 | +3.54 | 193.48 | +2.98 |
| X:11-12 | 210.82 | -11.26 | 202.36 | -8.46 |
| Y:A-B | 248.92 | -20.38 | 230.82 | -18.10 |
| Y:B-C | 223.52 | +2.59 | 229.36 | +5.84 |
| Y:C-D | 241.30 | +4.13 | 237.50 | -3.80 |
| Y:D-E | 203.20 | +24.23 | 219.55 | +16.35 |
| Y:E-F | 139.70 | -20.32 | 127.76 | -11.94 |
| Y:F-G | 190.50 | +22.06 | 201.78 | +11.28 |
| Y:G-H | 146.05 | +23.20 | 168.24 | +22.19 |

## Complete tested parameter grid

Five noise allowances, 15/17.5/20/22.5/25 mm, with independent uniform-sampling seeds 123 and 456. **All ten cases detect 12/12 and 8/8 positions, pass the frozen identity regions, and score 18/18 paired intervals.** Previous 15/25 mm cases gave 13/9 and 11/8. These are finite tested settings, not a guarantee over arbitrary parameters, layers or scans.

| Seed | Allowance mm | Count X/Y | Paired intervals | Paired MAE / max mm | Worst interval |
|---:|---:|---|---:|---|---|
| 123 | 20.0 | 12/8 | 18/18 | 9.51 / 22.19 | Y:G-H |
| 123 | 15.0 | 12/8 | 18/18 | 7.83 / 20.44 | Y:G-H |
| 123 | 17.5 | 12/8 | 18/18 | 8.56 / 21.98 | Y:G-H |
| 123 | 22.5 | 12/8 | 18/18 | 9.57 / 27.03 | Y:G-H |
| 123 | 25.0 | 12/8 | 18/18 | 9.75 / 33.28 | Y:G-H |
| 456 | 15.0 | 12/8 | 18/18 | 8.15 / 18.83 | Y:A-B |
| 456 | 17.5 | 12/8 | 18/18 | 8.28 / 18.86 | Y:G-H |
| 456 | 20.0 | 12/8 | 18/18 | 9.71 / 20.03 | Y:G-H |
| 456 | 22.5 | 12/8 | 18/18 | 9.79 / 22.85 | Y:G-H |
| 456 | 25.0 | 12/8 | 18/18 | 9.93 / 29.02 | Y:G-H |

Errors remain parameter sensitive despite stable counts. Across the grid paired MAE ranges 7.83–9.93 mm; the worst error reaches **33.28 mm** at seed 123 / 25 mm. Wide envelopes admit more off-centre/clutter support. Baseline still has substantial G–H +22.19 mm, A–B −18.10 mm and D–E +16.35 mm errors. No tested result is hidden, and no interval is dropped to improve the average.

## Verification and safe scope

**115 tests pass on each of custom IngeTrazo `1ee32a6` and upstream `69d9400468e81c5a91ba88a56a824cd240994a17`, zero failures/skips.** New cases cover sparse boundary peaks, synthetic bar counts and known spacing at three allowances and two orientations, perpendicular-only crossings, unequal visibility with shared lateral drift, rigid-frame invariance, incomplete shared support, unavailable overlap, shuffled nonconsecutive source IDs, auditable section distances, strict metric selection without fallback, unchanged scan evidence after endpoint edits, and persistence of new evidence through native Undo/Redo/IGZ.

The original 6,000-point Rohbau floor patch and rotated wall still yield zero bars in default and noise modes. Blurred synthetic bars retain 150/150/300 mm straight distances within 2 mm, and paired adjacent distances 150/150 mm within 2 mm. Final t1/t8 reruns remain 0/0 and 4/4; retained endpoints, source IDs and straight spacing are exactly identical to the prior baseline. Unanchored t8 tape pairs remain 0/32; this new metric is not retroactively used to claim a t8 error.

Offline reproduction:

```sh
# Disposable checkouts/environment; same PYTHONPATH/offscreen setup as before.
python tools/run_wingwall_trial.py --data-dir /absolute/scratch/wingwall \
  --output-dir /absolute/scratch/results --sensitivity
```

The output explicitly records `measurement_metric=paired_profile`, the separate `centreline_assessment`, all ten settings, all source point IDs and section evidence. [Full numeric summary](data/wingwall_refinement_summary.json). Source attribution, hash-checked acquisition and anchor caveats remain in [WINGWALL_TRIAL.md](WINGWALL_TRIAL.md).

No production checkout, operational plugin installation, live CAD document or work file was modified. PR remains draft. Automatic calibration, general automatic segmentation, native curved-bar reconstruction, live OpenGL review, worker/cancellation and automatic cloud-array reload remain incomplete.

## Subsequent stability fix

This page preserves the v6 results. [SPACING_STABILITY.md](SPACING_STABILITY.md) documents the v7 independent measurement support, all 15 cases, unchanged native detection and remaining nonzero errors.
