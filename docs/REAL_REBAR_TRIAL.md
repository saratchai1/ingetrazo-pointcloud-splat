# Real RGB-D rebar trial: count validation fails

The baseline 851915c detector was tested on real physical rebar scanned with Azure Kinect outdoors, rather than synthetic points. **It does not pass this trial.** After depth-layer isolation and a geometry-only direction estimate, `drone-t1` produces 1/1 candidates and `drone-t8` produces 60/65, compared with the specimen's five grid lines in each direction. No candidate was accepted or added to a production document.

## Sources and reference strength

- Fernando Moreu, Mahsa Sanei and Christopher Lippitt: [Zenodo 7933479](https://doi.org/10.5281/zenodo.7933479), *Increasing Bridge Durability and Service Life with LIDAR Enhanced Unmanned Aerial Systems (UAS)*. CC BY 4.0. The Balloon Fiesta Park archive contains actual RGB-D PLY exports and capture metadata; White Rock is an active construction-site capture.
- Sanei et al., *Computers in Industry* 179 (2026), 104495, [DOI](https://doi.org/10.1016/j.compind.2026.104495), [author-hosted full text](https://fricke.co.uk/Research/SaneiComputersInIndustry2026.pdf). Section 4 describes the Balloon Fiesta Park specimen. Figure 13 (page 12) supplies **32 steel-tape-measured mid-bay spacings** for a 5-by-5 top grid. Values range from 111.13 to 146.05 mm; the nominal design value of 127 mm is not substituted for these measurements. The numeric facts are transcribed in `data/real_rebar_reference.json`.

The released captures and published specimen description agree in site, capture configuration and visible grid. The authors do not supply a figure-bay-to-PLY registration or fiducial transform. Thus this is a **provisional specimen-level count comparison**, not a fully registered per-bay ground-truth accuracy benchmark. No orientation is chosen by minimizing error against the reference table. The raw original paper is retained locally for research, not redistributed here.

## Input integrity and reproduction

Both PLY files have 2,073,600 original records (1920x1080); invalid zero-depth records are excluded. XYZ values are millimetres, consistent with Azure Kinect and the paper's plotted axes, and are explicitly converted to metres. Retained original record IDs travel into the evidence.

The public ZIP is `Balloon Fiesta Park - July.zip` in the Zenodo record. These members can be downloaded with HTTP ranges and verified with the local ZIP CRC32, without downloading large MKV recordings:

| Member | ZIP local-header offset | Compressed bytes | SHA-256 of decompressed PLY |
|---|---:|---:|---|
| `.ply data/drone-t1.ply` | 67 | 5,425,213 | `84d3e007a955dac7a3f05d8ba62e8ae66410a699a7463a89d3c66a5166da0254` |
| `.ply data/drone-t8.ply` | 56,842,700 | 10,229,845 | `17b763895d1e841fba065992a29c540d25d63f64c3610ae053ae69ff34108b0c` |

Install benchmark dependencies in a disposable environment with `requirements-benchmark.txt`, alongside the host core/Qt dependencies. Put the decompressed files in a temporary data directory. With the extension and isolated host on `PYTHONPATH`, run:

```
QT_QPA_PLATFORM=offscreen python tools/run_real_rebar_trial.py \
  --data-dir /path/to/downloaded-ply --output-dir /path/to/disposable-results
```

The script never attaches to a running IngeTrazo document. It uses fixed scanner-space ROIs (visible specimen bounds), rigid scan-plane alignment and a manually chosen relative-depth slab of -140 to -75 mm. It then estimates two directions from the remaining scan geometry using seed 123 and 1,000 long-line hypotheses, without inspecting count/spacing reference values. This is assisted preprocessing, not an automatic layer-selection claim. The t1 depth slab is very sparse and is not evidence of complete visibility of every bar.

## Results and failures

| Stage | t1 candidates, two families | t8 candidates, two families |
|---|---:|---:|
| Broad ROI, initial guided axes | 97 / 94 | 180 / 188 |
| Depth slab, initial guided axes | 0 / 1 | 63 / 60 |
| Depth slab, geometry-only axes | 1 / 1 | 60 / 65 |
| Continuity/width filtering v3, same slab and geometry-only axes | 0 / 0 | 10 / 7 |
| Guided depth band + duplicate grouping v4 | 0 / 0 | 4 / 4 |
| Reference specimen grid | 5 / 5 | 5 / 5 |

The baseline rows above describe the pre-continuity detector. The v3 row was rerun with identical raw hashes, ROI, rigid transform and geometry-only directions. See [continuity follow-up](CONTINUITY_TRIAL.md) for v3 thresholds and regressions; see [the v4 layer trial](LAYER_TRIAL.md) for the latest depth-selection/grouping results and remaining errors.

All runs retain candidates as unaccepted. No broad supporting plane is excluded in these ROIs under the current thresholds. Relative to the specimen count, final t1 count deltas are -4/-4 and final t8 deltas are +55/+60. These are count discrepancies, not independently matched precision/recall measurements.

Visible failures include sparse-capture under-detection, over-segmentation of noisy bars, residual support/frame points and phantom lines supported by points on several perpendicular bars. A high confidence heuristic or many points does not establish a real bar. A successful TLS floor negative control does not establish rejection of noisy RGB-D backgrounds.

**Spacing MAE/max error are unavailable, not zero.** None of the 32 measured intervals has a verified bar/bay pairing. The count gate already fails, and the published H/V bay labels are not registered to the scan. Sorting surplus candidate spacings or selecting the most convenient subset would create misleading accuracy. `reference_validation.compare_reference` refuses to score a count mismatch, unverified correspondence or incomplete verified measurements. It computes signed errors and MAE only when all reference intervals are paired explicitly.

A White Rock PLY and the source paper's tape reference (111.76/142.24 mm for one chosen bay) were inspected, but the chosen bay cannot be registered reliably to the released scan; no spacing score is assigned. A separate author's irregular-rebar repository has PCD scans but no readily verified paired measurements/units/license, so it is not promoted to a ground-truth benchmark.

The next engineering work is bar continuity/local direction discrimination and proper foreground/layer segmentation, followed by a scan with independently registered bar/bay annotations. This trial does not establish field readiness.

## Original-record ROI and cell audit

A follow-up audited original invalid-depth records and source-image clipping, mapped eight retained tracks to manual RGB trace IDs, and measured six scan-local cells without extending unsupported tracks. The rightmost V4 trace has zero usable XYZ even in a 15-pixel corridor, while the top fragment is clipped and short. These observations distinguish missing source evidence from downstream cropping; they do not establish paper-label registration or a whole-specimen count pass. See [ROI and cell audit](ROI_AUDIT.md). Reference errors remain unavailable (0/32 verified pairs).
