# Remaining wingwall spacing residuals

This follows the v7 [stable measurement support](SPACING_STABILITY.md). Goal: reduce the remaining scan-spacing errors, especially G–H, A–B and D–E, without changing the reference, the frozen identities or the 18 scored intervals. Result: **no tested estimator change reduced the errors honestly, and the scored metric is unchanged.** Instead, every measured pair now records how its spacing changes along the shared support, and the benchmark reports how much of each residual cannot be explained by any observed tape station.

## Baseline reproduced first

Starting point: clean `feature/rebar-inspection` at `9e8ab4f`. Same hash-verified source, ROI, 180,000-point uniform samples, seeds 123/456/789, allowances 15–25 mm, reference and identity windows. The rerun matched the handoff exactly: every case 12/12 and 8/8, 18/18 intervals; seed 123 scan MAE **8.0563 mm**, maximum **21.1625 mm**; seed 456 7.9773/18.1977 mm; seed 789 7.7930/18.7902 mm; straight native centreline MAE **11.5566 mm**. 124 tests passed.

## What the scan shows (observation)

Per-section paired spacing was plotted along each Y pair, together with plan-view density of the measurement band. Raw section evidence is in the benchmark JSON. The figure and ablation scripts are workspace deliverables (`outputs/rebar-spacing-residuals/` beside this checkout) and are not committed.

- The Y bars are not mutually parallel in the scan. Section centres drift laterally by about 0–2.7° relative to the supplied direction, and by different amounts per bar. B rises from y≈0.405 m to 0.50 m along x; A only from ≈0.21 to 0.25 m; H stays near 1.66 m while G rises from ≈1.47 to 1.50 m.
- Consequently, spacing changes systematically along each shared support. Robust Theil–Sen trends over the shared extent are A–B **+24.5 mm**, G–H **−24.8 mm**, D–E **−18.0 mm**, F–G −14.8 mm, C–D +14.2 mm (seed 123; seeds 456/789 agree within about 3 mm).
- E has no steel at x≈1.00–1.14 m. Those sections hold 15–30 points against a typical ≈200, sparse returns above the diagonal edge bar. The next few sections follow that diagonal. They give D–E section errors of up to +80 mm, but they are only a few of 54 sections. Excluding them moves the D–E median by under 1 mm.
- At bowed ends a bar leaves its fixed straight window (radius three diameters). B falls to 3–4 points per section at x≈0.38–0.44 m. Such sections measure the tail of the bar, pulled toward the straight line.
- Fixed source-ROI truncation was tested and ruled out for A and H: the straight window around each track never crosses the ROI boundary.
- Figure 14 places the red tape values in the margins. No published text, figure or table locates the tape station along the bars.

## Station bound (diagnostic, not a score)

Station bound: if the tape had been read at the most favourable observed section within the 10–90% section-spacing range, how large would the error still be? This uses the published tape only after measurement. It never selects sections, never changes the median and never enters MAE.

| Interval | v7 error mm (123/456/789) | Nearest 10–90% section error mm | Nearest full section-range error mm | Along-support trend mm (123) |
|---|---|---|---|---:|
| Y:G–H | +21.16 / +18.20 / +18.79 | **+12.44 / +12.24 / +13.40** | +9.78 / +6.60 / +11.02 | −24.8 |
| Y:D–E | +15.81 / +15.46 / +15.55 | **+10.62 / +10.72 / +9.13** | +6.15 / +4.50 / +2.53 | −18.0 |
| Y:A–B | −17.72 / −17.20 / −18.67 | **−5.88 / −6.89 / −8.95** | 0 / 0 / 0 | +24.5 |
| Y:E–F | −11.51 / −12.10 / −10.37 | −6.68 / −4.75 / −5.70 | 0 / 0 / 0 | +8.1 |
| Y:F–G | +10.87 / +10.38 / +9.53 | +3.97 / +3.32 / +3.37 | +0.27 / +0.60 / +2.23 | −14.8 |
| X:1–2 | +11.91 / +11.80 / +12.65 | +5.16 / +6.80 / +5.28 | 0 / +4.43 / 0 | +7.1 |

The tape lies outside the 10–90% observed section range for 11, 10 and 11 of 18 intervals, and outside the full section range for 4, 4 and 3, for the three seeds. Extreme single sections include cluttered ones (for example E above the diagonal edge bar), so the 10–90% band is the more conservative station bound. All rows are in `docs/data/wingwall_residual_summary.json`.

Interpretation: for G–H and D–E, no station inside the central 10–90% of observed sections reproduces the tape value within about 9–13 mm. Even the single most favourable section stays 6.6–11.0 mm (G–H) and 2.5–6.2 mm (D–E) away. Changing the section estimator cannot remove that difference. The remaining candidates are scanner geometry/scale (GeoSLAM, uncalibrated here), tape reading or station, and steel moving between tape and scan. These are plausible explanations, none individually proven. For A–B, more than half the median error comes from station ambiguity on strongly non-parallel bars. Any reduction would need to know where the tape was read.

The Y-pair section errors all converge toward small values near the tall end (x≈2.6–2.7 m). That could be where the tape was read, but no evidence says so. Choosing that station after seeing the errors would fit the reference, so it is **not used**. Field notes, photos or a registered tape station would make a station-registered comparison possible.

## Every estimator variant tested (none adopted)

The measurement support is allowance independent within a seed (0 mm drift verified over all 15 cases). Each variant was therefore evaluated on all three sampling seeds at allowance 20 mm. MAE over fewer scored intervals is **not comparable**: lost intervals are a failure, not an improvement.

| Variant | Seed 123 scored, MAE/max mm | Seed 456 | Seed 789 |
|---|---|---|---|
| v7 committed: median within fixed straight 3d window | 18, 8.06/21.16 | 18, 7.98/18.20 | 18, 7.79/18.79 |
| Median of all band points in the same window | 18, 8.30/21.30 | 18, 8.12/19.76 | 18, 7.97/20.73 |
| Window re-centred on local bar (follows bow) | 18, 8.50/24.10 | 18, 8.31/20.40 | 18, 8.15/22.02 |
| 2D mean-shift mode, σ 0.5d | 18, 8.25/20.37 | 18, 8.33/19.56 | 18, 8.18/22.28 |
| 2D mean-shift mode, σ 1d | 18, 8.01/21.17 | 18, 7.94/20.29 | 18, 8.11/20.63 |
| Drop sections with < 0.1× median support | 18, 8.08/21.16 | 18, 7.96/18.20 | 18, 7.69/18.79 |
| Drop sections with < 0.25× median support | 16, 8.81/21.16 | 16, 8.80/18.20 | 17, 8.12/18.79 |
| Drop sections with < 0.5× median support | 15, 9.06/20.80 | 15, 8.87/17.68 | 14, 8.46/18.23 |
| Drop sections with < 0.75× median support | 4, 10.24/19.92 | 3, 5.51/11.13 | 4, 8.19/18.78 |
| Neighbour filter, median centres, 0.5d | 15, 8.50/19.92 | 13, 9.13/18.20 | 13, 8.97/18.79 |
| Neighbour filter, median centres, 1d | 17, 8.45/21.16 | 18, 8.01/18.20 | 18, 7.91/18.79 |
| Neighbour filter, mean-shift centres, 0.5d | 13, 9.46/19.71 | 14, 9.29/19.41 | 14, 8.86/20.20 |
| Neighbour filter, mean-shift centres, 1d | 18, 8.04/19.94 | 18, 8.43/19.47 | 18, 8.22/21.41 |

Faithful local estimators make A–B *worse* (about −20 to −22 mm). Following the bow measures the true, narrower left-end spacing. Mode estimators reduce G–H by 3–5 mm at σ 0.5d and about 1.4 mm at σ 1d (contamination near the extra vertical element at x≈1.7 m) but give it back elsewhere. Support and neighbour rules either change nothing or lose intervals. Adopting whichever variant scored best would be selection on the reference, so **the v7 metric is retained unchanged**.

## Code change: evidence only

- Each measured paired profile now includes `axial_trend`: Theil–Sen slope of section spacing against axial position, fitted spacing at both ends of the observed section range, fitted change, section min/max, and per-bar lateral drift in degrees, in native bar order. It is labelled `station_registered: false` and `is_uncertainty: false`. Median, quantiles, sections, coverage, matching and source IDs are untouched. The UI shows each scan support spacing with its section range and along-support trend.
- `tools/run_wingwall_trial.py` attaches `station_diagnostic` to every scored profile interval and prints it. It is explicitly unused for scoring or section selection.
- No trend is recorded for a single measured section (no NaN can reach JSON/IGZ). Degenerate or non-finite trend input is refused.
- Twelve new test cases: a known 0.03 m/m fanning pair in original and rotated frames (median unchanged); shared drift gives zero spacing trend with correct per-bar drift; Theil–Sen resists a cluttered section; a single section has no trend and serializes without NaN; degenerate trend input is refused; reversed native ordering keeps each bar's drift with its own bar; the station diagnostic never changes scored errors; its sign follows measured − tape below, inside and above the range (four cases). An existing UI test now also checks that the trend text is shown.

## Verification

All 15 cases rerun after the change and compared with the baseline run field by field: **0 differences** in any measured interval, error, count, identity assignment, native bar, straight spacing, measurement support or section. The only addition is the trend field. There are still 3 unique evidence fingerprints (one per sampling seed, identical across allowances); fingerprint values change because the trend is part of the hashed profile evidence. Scan MAE stays 8.06/7.98/7.79 mm with maxima 21.16/18.20/18.79 mm; native straight centreline MAE stays 11.56 mm and is reported separately. t1/t8 rerun: 0/0 and 4/4, every bar, point ID, evidence and straight spacing identical to the stored baseline. t8 tape pairs remain 0/32 verified. The Rohbau floor and rotated-wall negatives remain zero bars. **136 tests pass on each of custom core `1ee32a6` and upstream `69d9400`** (124 before this change).

## Not achieved / still open

G–H, A–B and D–E errors are **not reduced**: G–H +21.16 mm and D–E +15.81 mm remain over-measured, A–B −17.72 mm under-measured (seed 123). On available evidence they cannot be reduced without an independent tape station, survey-calibrated scale/geometry, or another registered acquisition. Earlier limitations remain: manual ROI/direction/layer, the 200k point cap, fixed geometric windows, heuristic confidence, straight native geometry, synchronous analysis, unvalidated live OpenGL interaction and manual cloud reload after IGZ reopen. No field compliance or millimetre-accuracy claim is made.
