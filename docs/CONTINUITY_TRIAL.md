# Continuity follow-up: fewer false tracks, real validation still fails

The previous detector could connect isolated clusters on perpendicular bars into a long phantom line. Its 10-bin axial coverage only affected a quality score. This follow-up makes support continuity a prerequisite, consolidates compatible overlapping proposals and rejects a track whose support is too wide for one bar. All candidates still require manual acceptance.

## Geometry rules

Thresholds depend on the user-supplied design diameter, not the reference count or spacing:

- Proposals are processed by decreasing support with deterministic ties. Their transverse centres must be within one diameter and their axial intervals must overlap. They merge only if their joint radial residual p95 is at most 0.8 diameters. Original point indices are retained without duplication.
- Ordered axial support splits at gaps exceeding three diameters. Each resulting segment must independently meet minimum support (default 30) and length (default 250 mm).
- Each segment must occupy at least 75% of axial cells, whose width is at most two diameters. This replaces the coarse fixed 10-bin score with a rejection test.
- The fitted PCA direction must be within five degrees of the supplied direction; radial residual p95 must not exceed 0.8 diameters.
- Reports record these thresholds, rejection/merge counters, actual largest support gap, fine axial coverage and retained source record indices. Algorithm identifier is `parallel-continuous-tracks-v3`.

This does not reconstruct hidden steel. Sparse support is deliberately withheld. A gap longer than the threshold splits one physical bar into fragments if both are long enough; fragments are not a verified physical count. No tolerance or compliance claim follows from candidate counts.

## Same-input actual scan comparison

Used the same Zenodo 7933479 real RGB-D PLY files, fixed depth slab, rigid transforms, geometry-derived directions and provisional five-line specimen reference as [the original trial](REAL_REBAR_TRIAL.md). No reference count or spacing was used to tune directions or select a subset of output bars. Raw file hashes, ROI, transforms and directions were programmatically checked against the saved baseline. Numeric results are in [the summary](data/continuity_trial_summary.json); reproduce with `tools/run_real_rebar_trial.py`.

| Actual capture | Before, families A/B | Current, families A/B | Provisional specimen reference |
|---|---:|---:|---:|
| drone-t1, 173 layer points | 1 / 1 | 0 / 0 | 5 / 5 |
| drone-t8, 26,550 layer points | 60 / 65 | 10 / 7 | 5 / 5 |

**Real count validation still FAILS.** The dense t8 surplus decreases from +55/+60 to +5/+2. The sparse t1 discrepancy worsens from -4/-4 to -5/-5: none of its tracks has enough continuous support. This is conservative rejection, not improved recall. Nearby noisy/depth bands still split into several tracks and support/frame geometry can remain. The broad-surface filter still removes zero points from these RGB-D layer ROIs; this change does not solve automatic layer/background segmentation.

There is still no independently registered pairing between the paper's 32 measured mid-bay intervals and released scan bars (0/32 verified). Spacing MAE and maximum error remain unavailable, never zero. Correcting counts alone would not establish a spacing score. No candidate was accepted or committed to CAD.

## Regression evidence

Eight new test cases cover a five-bar perpendicular grid that must not generate phantom lines, retention of those five actual perpendicular bars, small scan gaps, splitting large unsupported gaps without bridging them, duplicate surface-proposal merging with every source ID, preservation of distinct nearby bars/spacing, rejection of wide support and dense isolated islands, and rotated tracks retaining original record IDs. The phantom-line regression was also run against the previous implementation and failed there as expected.

All 46 tests pass on both isolated IngeTrazo cores: customized `1ee32a6` and upstream `69d9400468e81c5a91ba88a56a824cd240994a17`. The original synthetic three-bar spacing remains 150/150/300 mm within 1 mm. The identical real Rohbau3D floor patch and its rotated wall analogue still return zero bars. Native group Undo/Redo, IGZ persistence, precision, ROI and offscreen review UI checks pass. These are software checks; they do not make the real-data count validation pass.

No production checkout, installed plugin or operational model was changed. Registered bar/bay annotations, local surface-direction discrimination and robust foreground/layer segmentation remain necessary before field use.
