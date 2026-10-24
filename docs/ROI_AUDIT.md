# t8 original-record visibility and scan-local cell audit

The missing fifth lines cannot be attributed simply to the XYZ box. A read-only audit of the **original** t8 PLY, before ROI selection, finds zero usable XYZ records under the annotated rightmost RGB bar (V4). The topmost row is clipped by the source image and has only a short visible fragment. Existing depth filtering further removes support, but widening a downstream ROI cannot create absent source depth.

## Evidence scope and source

The exact original CC BY 4.0 Moreu/Sanei/Lippitt t8 PLY from [Zenodo 7933479](https://doi.org/10.5281/zenodo.7933479) has SHA-256 `17b763895d1e841fba065992a29c540d25d63f64c3610ae053ae69ff34108b0c`. It contains 2,073,600 XYZ/RGB records, including zero-depth records. Reconstructing the RGB records as 1920x1080 produces the recognizable camera image. This layout is **inferred**, not declared by the PLY header; no independently supplied RGB/depth calibration or labeled steel point segmentation is available. Pixel-corridor counts describe those records, not an independently calibrated physical silhouette.

Manual image traces in [t8_rgb_traces.json](data/t8_rgb_traces.json) label visible vertical bars V0–V4 left to right, four visible horizontal bars H0–H3 top to bottom, and the clipped top fragment separately. Trace endpoints were chosen from RGB appearance, without inspecting tape spacing values. The IDs are scan-local and do not assert the paper's A–E/1–5 labels. Source pixel/record IDs are preserved, including invalid records, so source failure is distinguished from each crop stage. Corridors use radii 5 and 15 pixels as a sensitivity check.

## What was lost, and where

| Traced region | Corridor radius | In-image records | Usable original XYZ | After original XYZ box | After depth slab | After selected band |
|---|---:|---:|---:|---:|---:|---:|
| Rightmost V4 | 5 px | 6,281 | 0 | 0 | 0 | 0 |
| Rightmost V4 | 15 px | 17,695 | 0 | 0 | 0 | 0 |
| Clipped top fragment | 5 px | 1,562 | 605 | 605 | 352 | 165 |
| Clipped top fragment | 15 px | 3,881 | 1,913 | 1,913 | 474 | 231 |

Within **all ten annotated corridors**, the original XYZ box excludes zero additional valid records. This does not prove that the box includes every steel point in the whole object. The depth slab and selected band do exclude many records in the corridors; counts are in [roi_audit_summary.json](data/roi_audit_summary.json). A valid corridor record can also belong to ground/support because RGB/depth alignment is not independently calibrated.

The top fragment's valid-source axial 1st–99th percentile span is 146.60 mm at radius 5 (146.06 mm at radius 15). After the existing filters it is 49.04 mm (45.34 mm at radius 15), below the detector's 250 mm minimum length. These are **corridor support spans**, not a recovered full bar length. No full fifth track is fabricated by extending this fragment. For V4, absent valid source depth is the direct observation; a sensor field-of-view boundary is a plausible explanation, not a calibrated sensor diagnosis.

## Line correspondence within the scan

All eight retained representative tracks align uniquely to manual RGB traces, with median perpendicular pixel offsets of 2.83–16.42 pixels and a next-trace median-distance margin over 100 pixels. The offsets themselves warn against treating RGB tracing as exact depth registration:

- Family 1 candidates 1–4 map to V0, V1, V2, V3.
- Family 2 candidates 1–4 map to H3, H2, H1, H0.
- V4 and the clipped top fragment have no retained full track.

This is reproducible **scan-to-RGB-trace correspondence**, not independent verification against the source diagram's labels. The detector still returns 4/4 groups; the complete-specimen reference remains 5/5. The audit does not change the detector, accept any candidate, create CAD geometry or redefine the expected count to make a test pass.

## Candidate mid-bay cells

The new grid helper projects named straight tracks onto the selected plane, intersects both families, and averages opposite edge lengths following the paper's mid-bay definition. It requires every crossing to lie within **both detected endpoint spans**; no line extension completes missing corners. Of the 3x3 scan-local cells bounded by V0–V3 and H0–H3, six have all four supported corners. The three cells adjoining V3 have unsupported corners and return null measurements.

| Scan-local rows | Columns | Horizontal mm | Vertical mm |
|---|---|---:|---:|
| H0:H1 | V0:V1 | 137.895 | 122.496 |
| H0:H1 | V1:V2 | 123.904 | 122.496 |
| H1:H2 | V0:V1 | 137.895 | 137.229 |
| H1:H2 | V1:V2 | 123.904 | 137.229 |
| H2:H3 | V0:V1 | 137.895 | 124.226 |
| H2:H3 | V1:V2 | 123.904 | 124.226 |

These are 12 derived component measurements, not 12 independently observed reference matches. Values repeat because the detector uses one common straight direction per family. They cannot capture actual local bending or bay-specific centre changes. They differ slightly from the prior 3D perpendicular centreline distances because this helper uses projected opposite-edge averages; neither is silently relabeled as the other.

## Why reference spacing errors remain unavailable

[Sanei et al., DOI 10.1016/j.compind.2026.104495](https://doi.org/10.1016/j.compind.2026.104495), Fig.13, provides 32 tape measurements under A–E/1–5 labels. Fig.10 shows a photograph of the specimen, but the available source does not anchor those diagram labels to landmarks in the released t8 frame. The user also confirmed that no such label-to-scan information is available. Ordering, rotation/reflection, or an index offset cannot be chosen by minimizing spacing error. All 32 reference rows remain unassigned, with **0/32 verified comparisons and null MAE/max error**.

`cell_validation.compare_cell_pairs` supports explicit one-to-one reference-cell/measurement IDs, independently documented anchor evidence and partial coverage. It will not score an unverified pair, missing support, duplicate ID, or nonpositive/nonfinite matched spacing. Verified partial subsets remain labeled partial; they are not a whole-grid pass. Caller-supplied verification/anchor text is a claim requiring review, not an automatic semantic proof.

The audit emits an empty `matches-template.json` bound to the source, reference and measured-grid SHA-256 values. A future externally anchored crosswalk may be supplied via `--matches`. Stale source/reference/grid bindings are rejected. No verified entry or guessed orientation is populated in the current template.

## Reproduction and regression checks

In the same disposable environment as the real-data runner:

```
python tools/run_real_rebar_trial.py --data-dir /path/to/original-ply \
  --output-dir /path/to/trial --layer-mode dominant
python tools/audit_real_rebar_roi.py --ply /path/to/original-ply/drone-t8.ply \
  --trial /path/to/trial/trial.json --output-dir /path/to/audit
```

81 software tests pass on **each** isolated core: customized `1ee32a6` and upstream `69d9400468e81c5a91ba88a56a824cd240994a17`, no failures/skips. Nineteen new cases cover source-invalid versus cropped records, clipped trace IDs, stage nesting, known rectangle/trapezoid mid-bay values, rigid transformations, unsupported-corner rejection, explicit verified/partial/unavailable matching, and stale hash-bound crosswalk rejection. The same real Rohbau3D floor/wall negatives still return zero bars; synthetic three-bar spacings remain 150/150/300 mm within 1 mm. Native Undo/Redo/persistence and layer UI checks still pass.

The actual t1/t8 trial was rerun: t1 remains 0/0, t8 remains 4/4; bar evidence and candidate spacings match the saved v4 trial exactly. Live OpenGL interaction and registered real-reference accuracy remain unvalidated. Production, installed plugins and work documents were not touched.
