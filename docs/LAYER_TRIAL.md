# Guided depth selection and duplicate proposal grouping (v4)

The previous same-ROI t8 trial returned 10/7 continuous candidates because noisy depth bands could become separate tracks. The current workflow optionally selects a thin depth band along a user-supplied world normal, and preserves weak overlapping duplicate proposals as reviewable evidence under a stronger track. The result is **4/4 groups**, compared with the provisional specimen count of 5/5. **Count validation still fails; this does not establish physical bar identities or field readiness.**

## Layer selection

Broad-surface rejection runs first, before depth cropping: otherwise a cropped wall could become a narrow bar-like strip. The user enables depth selection inside an already guided section box, supplies a normal perpendicular to the bar direction, and chooses a depth-mode rank. It is off by default. The review dialog accepts X/Y/Z or a numeric world vector. Rank 1 means strongest smoothed histogram peak, not frontmost layer.

Depth bins are a quarter of the design diameter. Histogram counts are smoothed with weights `[1,2,3,2,1]`; local maxima closer than two diameters are suppressed. At most 32 modes are listed, with truncation recorded. A selected band's half-width is 0.75 diameters. Reports retain the normal, selected depth/rank, mode strengths/support, histogram/band parameters and excluded original source record IDs. Histogram coordinates are relative to the ROI depth minimum; large world translations do not allocate huge arrays.

This is guided scan-support selection, not automatic recognition of steel layers. Dense supports can dominate; nearby layers or ribbed/noisy surfaces may not resolve into separate modes. A fixed normal cannot follow curved/warped layers. Users must crop unrelated objects and inspect the retained layer before acceptance. Diameter remains design input.

## Duplicate handling

Compatible surface proposals still merge only when their combined support fits the existing envelope. Consolidation now repeats after disconnected islands have been split off; each successful pass reduces track count. Exact retained source IDs remain attached to the refitted track.

Within an explicitly selected layer, a separate grouping rule handles a weak proposal that overlaps a stronger track but cannot be honestly included in its cylinder fit:

- Stronger support must be at least four times weaker support, and axial overlap must cover at least 80% of the weaker track.
- Centreline distance and normal depth difference must each be at most one design diameter; in-plane lateral distance must be at most 0.75 diameters.
- The stronger fit/support/residual stay unchanged. The complete weaker proposal, endpoints and point IDs are retained in `grouped_duplicate_proposals`, marked `review_required` and `used_for_primary_fit=false`.
- The UI reports grouped proposals and draws their original lines dashed. Explicit acceptance still applies to the retained representative. Ambiguous similar-strength tracks, distinct nearby bars, different depth layers and disjoint fragments are not forcibly grouped by this rule.

Grouping is a review heuristic. Closely spaced bars, incomplete surfaces or a wrong diameter can defeat it. A grouped proposal is not a verified duplicate or added evidence for the primary cylinder's confidence.

## Actual-data results

Same raw t1/t8 hashes, broad scanner ROIs, original record IDs, rigid transforms, manually guided depth slab and geometry-only bar directions as the v3 baseline. Only the optional depth mode is enabled; reference count/spacing values are not inputs to the detector. Neither directions nor an output subset are selected by minimizing error to reference measurements.

| Stage | t1 groups A/B | t8 groups A/B |
|---|---:|---:|
| v3 baseline, fixed depth slab | 0 / 0 | 10 / 7 |
| Current code, layer selection disabled | 0 / 0 | 10 / 7 |
| Strongest depth band, before weak-proposal grouping | 0 / 0 | 5 / 4 |
| Strongest band + grouping | 0 / 0 | 4 / 4 |
| Provisional complete-specimen reference | 5 / 5 | 5 / 5 |

The t8 selected depth is -102.122 mm in the rigid scan-local frame, half-width 11.906 mm. It retains 16,943 of the original slab's 26,550 points and excludes 9,607. One weak proposal in family A is grouped; none in B. Sparse t1 retains 110 of 173 points and still detects no continuous tracks. No candidate was accepted or committed to CAD.

Adjacent retained-track centreline spacings (scan-local ordering, not paper H/V registration):

| Family | Candidate adjacent spacings, mm |
|---|---|
| A | 137.901, 123.903, 125.736 |
| B | 122.572, 137.251, 124.226 |

These six derived candidate intervals are **not** the paper's 32 registered mid-bay measurements. Count mismatch, partial ROI visibility and absent individual bar/bay correspondence remain unresolved. All spacing MAE/max errors remain null (0/32 verified reference intervals). A value inside the paper's measurement range is not proof of accuracy.

Sources, license and original raw hashes are in [the real-data trial](REAL_REBAR_TRIAL.md). The numeric current comparison is [layer_trial_summary.json](data/layer_trial_summary.json). Reproduce in a disposable environment with:

```
python tools/run_real_rebar_trial.py --data-dir /path/to/original-ply \
  --output-dir /path/to/results --layer-mode dominant
```

Omit the final flag or use `--layer-mode roi` for the same-code control. The runner does not open an IngeTrazo document.

## Validation and remaining work

62 software tests pass on each isolated core: customized `1ee32a6` and upstream `69d9400468e81c5a91ba88a56a824cd240994a17`, without failures or skips. Tests cover independent selection of two synthetic layers and their known spacing, rotated layers with source-ID separation, large coordinate translations, invalid normals/ranks, floor/wall negatives with layer selection enabled, retained duplicate evidence, rejection of distinct bars/layers/fragments, post-split reconsolidation, offscreen layer UI and native Undo/Redo/IGZ persistence with layer evidence. Existing phantom-line, LAS/LAZ precision, original floor patch (zero bars) and synthetic three-bar 150/150/300 mm spacing checks still pass.

The complete physical specimen still does not match the retained counts. ROI completeness and individual bar/bay registration need independent annotations before accuracy can be scored. Automatic foreground/layer segmentation and calibrated scan uncertainty remain unresolved. Live OpenGL interaction remains unvalidated. Production files and the installed plugin were not touched.
