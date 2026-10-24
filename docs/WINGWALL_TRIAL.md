# Real wingwall: source-anchored tape-spacing trial

The guided noise mode detects 12/12 X positions and 8/8 Y positions on the selected real wingwall layer. All 18 adjacent intervals have source-anchored identities. Mean absolute spacing error is **11.33 mm**, maximum **24.23 mm** (Y:D–E). These results do not establish millimetre accuracy, automatic inspection, or a construction compliance decision. The PR remains experimental/draft.

## Public sources and attribution

Moreu, Lippitt and Yuan, *Bridge Construction Monitoring using LIDAR for Quantified, Objective Quality-Control Quality-Assurance*, TranSET 19STUNM02. [Dataset, CC BY 4.0](https://doi.org/10.5281/zenodo.4273237), [official report](https://rosap.ntl.bts.gov/view/dot/58940/dot_58940_DS1.pdf), PDF page 30 / printed page 20, Figure 14 and Table 5. The red tape values are the reference; the authors' MATLAB/LiDAR estimates are not used as truth. Independent NumPy implementation; no source MATLAB algorithm is executed or copied.

The source MAT contains 4,182,318 finite XYZ rows (the report states 4,182,316). Its SHA-256 is `87cce057c0ffd69d0b5d90f3c93a73afec6e0d7c9635ae53fe7cc99080231f3c`. File identities for the MAT, report, source diagram and physically labeled photos are in [wingwall_reference.json](data/wingwall_reference.json). Raw scans/photos/report are not committed. The companion GeoSLAM E57 uses SI metres; the author MAT is exported XYZ. This workflow records that unit basis, and does not independently calibrate the scanner's length scale.

## Registration before comparison

The stepped/sloping wingwall shape fixes orientation: analysis X = max(source Y) − source Y, analysis Y = source X, Z unchanged. The source `1-5.png` photo labels physical RB1–RB5 at the low/sloping end, `A-C.png` labels RB-A/RB-B/RB-C at the lower edge, and Figure 14 supplies the continuous remaining order. This is manually reviewed source registration, not a calibrated photogrammetric transformation. Frozen scan-side identity windows reject a candidate in the wrong bar region even if the total count agrees. They are used only after detection and are not metric ground truth.

Table 5's third X row says “3–6”; Figure 14 places the third adjacent 8.8 inch interval between bars 3 and 4. The reference explicitly uses Figure 14 for that pair. Figure 14 shows 5.75 inches for G–H whereas Table 5 rounds it to 5.8; the more detailed figure value is used consistently. Most tape values are published at 0.1 inch increments (2.54 mm); G–H is displayed at 0.01 inch. Those display increments are not measurement uncertainty. No orientation, reflection, scale, subset or pairing is selected by minimizing tape errors.

## Reproducible geometric protocol

Source ROI: [0.18, 0.15, 0.18] to [1.72, 2.80, 0.27] m, retaining 733,390 original records. This selects a visible steel layer and excludes peripheral formwork; it is an assisted crop, not automatic layer recognition. Uniform sampling without replacement retains 180,000 records, seed 123, sorted by original source record ID. The full scan exceeds the application's 200,000-point analysis limit. Reference counts and tape spacings are never detector inputs.

Directions are [0,1,0] for X positions and [1,0,0] for Y positions, layer normal [0,0,1], design diameter 15.875 mm (#5). A **user-supplied 20 mm scan blur allowance** enables density proposals. This is a support/filter parameter, not a claimed measurement accuracy. Proposals are pruned around robust centres with equal influence for occupied axial cells; continuity, support, length, direction and coverage checks still apply. Full source IDs, thresholds, residuals and representative centres remain in the reports. Every candidate starts unaccepted.

The same application's spacing function measures perpendicular 3D distance between parallel straight centrelines, requiring axial overlap. It is compared to the field tape's adjacent bar spacing. Curvature, local tape placement and depth differences can bias this comparison; the straight-family model does not recover local per-bay bending. No acceptance threshold is inferred from these errors.

```sh
# Disposable environment only; benchmark also needs scipy (MAT reader).
python tools/fetch_wingwall_data.py --output-dir /absolute/scratch/wingwall
python tools/run_wingwall_trial.py --data-dir /absolute/scratch/wingwall \
  --output-dir /absolute/scratch/results --sensitivity
```

Use the same PYTHONPATH/offscreen setup as [REBAR_INSPECTION.md](REBAR_INSPECTION.md). The fetcher selects only four data/photo ZIP members using byte ranges and downloads the public report; cached files are SHA-256 checked, new ZIP data is CRC/size/hash checked. It does not fetch or execute unrelated archive contents. Both entry points verify the source/anchor hashes. [Compact results](data/wingwall_trial_summary.json) retain all errors and identity assignments; the runner's `trial.json` also retains full point evidence.

## All adjacent spacing errors

Positive error means the detected centreline distance exceeds the published tape value.

| Interval | Tape (mm) | Detected (mm) | Signed error (mm) |
|---|---:|---:|---:|
| X:1-2 | 215.90 | 231.17 | +15.27 |
| X:2-3 | 223.52 | 225.25 | +1.73 |
| X:3-4 | 223.52 | 210.46 | -13.06 |
| X:4-5 | 241.30 | 247.18 | +5.88 |
| X:5-6 | 236.22 | 244.16 | +7.94 |
| X:6-7 | 223.52 | 207.33 | -16.19 |
| X:7-8 | 236.22 | 235.70 | -0.52 |
| X:8-9 | 223.52 | 227.11 | +3.59 |
| X:9-10 | 210.82 | 218.95 | +8.13 |
| X:10-11 | 190.50 | 194.04 | +3.54 |
| X:11-12 | 210.82 | 199.56 | -11.26 |
| Y:A-B | 248.92 | 228.54 | -20.38 |
| Y:B-C | 223.52 | 226.11 | +2.59 |
| Y:C-D | 241.30 | 245.43 | +4.13 |
| Y:D-E | 203.20 | 227.43 | +24.23 |
| Y:E-F | 139.70 | 119.38 | -20.32 |
| Y:F-G | 190.50 | 212.56 | +22.06 |
| Y:G-H | 146.05 | 169.25 | +23.20 |

## Sensitivity and remaining failures

| Seed | Noise allowance (mm) | Count X/Y | Scored intervals | MAE / max (mm) |
|---:|---:|---|---:|---|
| 123 | 20 | 12/8 | 18/18 | 11.33 / 24.23 |
| 456 | 20 | 12/8 | 18/18 | 10.69 / 23.76 |
| 123 | 15 | 13/9 | 0/18 | unavailable |
| 123 | 25 | 11/8 | 7/18 | 18.61 / 31.68 |

All tried sensitivity results are retained. At 15 mm, surplus candidates prevent scoring either family; no best subset is selected. At 25 mm, a missing X candidate prevents scoring X, so the error is explicitly partial over seven Y intervals. A different sampling seed at 20 mm retains complete counts. This is development evidence from one source, not a held-out generalization study or calibrated robustness guarantee.

The largest baseline errors are Y:D–E +24.23 mm, Y:G–H +23.20 mm, Y:F–G +22.06 mm, Y:A–B −20.38 mm and Y:E–F −20.32 mm. Blurred crossings, local anchors/occlusion, departures from the common straight direction and unknown scan calibration remain plausible causes, not individually proven causes. Additional independently calibrated scans and local shape models are required before field acceptance.

## Regression verification and safe scope

**99 tests pass on each core**: custom IngeTrazo `1ee32a6` and upstream `69d9400468e81c5a91ba88a56a824cd240994a17`, zero failures/skips. Tests include original real Rohbau floor and rotated wall negatives in both default/noise modes; blurred synthetic 150/150/300 mm spacings within 2 mm in original and rotated frames; perpendicular crossings; invalid noise parameters; dense-anchor resistance; conservative spatial-grid lookup against exhaustive distances; wrong-position/extra-count/missing-overlap reference rejection; offscreen UI; native Undo/Redo and IGZ evidence persistence.

The final code also reruns the unchanged t1/t8 protocol. t1 remains 0/0, t8 remains 4/4. Every retained endpoint, source point ID and candidate spacing is exactly identical to the previous committed baseline. Its missing fifth line is not manufactured. Its unanchored Figure 13 values remain **0/32 verified matches**, distinct from this wingwall's 18/18. See [ROI_AUDIT.md](ROI_AUDIT.md).

Development used disposable checkouts and offscreen documents only. No operational checkout, plugin installation, live document or production data was modified. Live OpenGL interaction, automatic scan reload after IGZ reopen, background cancellation and calibrated uncertainty remain incomplete.
