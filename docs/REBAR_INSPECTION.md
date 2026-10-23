# Assisted rebar inspection (experimental)

This extension contains an independently implemented, assisted straight-bar workflow. It does not incorporate Modely code, models, assets, or a proprietary engine.

## Dependencies and safe development

Use a disposable IngeTrazo checkout and Python environment with IngeTrazo's dependencies. Install `requirements-dev.txt` in that disposable environment. LAS/LAZ now requires `laspy[lazrs]` for standards-aware decompression. Do not install this experimental build in an operational plugin folder or open production documents for testing.

Set `PYTHONPATH` to the extension repository and the IngeTrazo checkout, then run `python -m pytest tests -q` with `QT_QPA_PLATFORM=offscreen`. Tests create their LAS, LAZ, and IGZ files in temporary directories.

## Coordinates and units

- Confirm source units (m, mm, or international ft) at LAS/LAZ import. LAS coordinate scale is not a unit declaration. Extent-based unit guessing has been removed.
- Source coordinates are decoded in float64, converted to local metres before any render-buffer float32 conversion. Analysis retains float64 local coordinates. The first imported point anchors the default origin; the LAS header offsets, scales, CRS WKT when available, and unit conversion are recorded.
- Subsequent LAS imports reuse the first scan's source origin converted to their units. A different/missing-versus-known CRS is rejected instead of implicitly reprojected. Unidentified CRS imports require externally verified alignment; equal or missing WKT does not prove survey alignment or a common vertical datum.
- `read_las(..., roi=(min,max))` uses inclusive SOURCE-coordinate limits and reads chunks. Original source point-record indices are retained for import ROI. The source file hash identifies those records.
- Inspection section boxes use inclusive transformed WORLD metres. Rendering, snapping, bounds, and inspection use the same point-cloud affine mapping, including native proxy Move/Rotate/Scale. Native CAD geometry uses local coordinates; keep project geometry close to its origin.
- Source coordinates can be reconstructed with `dataset.source_coordinates()`. Reports also store the local-to-world matrix and explicit frame for reproducible alignment.

## Workflow

1. Import a LAS/LAZ and confirm units. Use one parallel bar family in one visible layer.
2. Enable the section box, and narrow it around the desired layer. At most 200,000 retained points are accepted for assisted analysis.
3. Open **Scan-to-BIM → Rebar Inspection…**. Choose X/Y/Z, or enter a precise common direction as `x,y,z`. Input the design diameter in mm. This version uses a guided direction, not arbitrary automatic orientation discovery.
4. Analyze. Review numbered amber centreline overlays against the scan. The modeless window allows view navigation. The table shows support, 95th-percentile radial residual, and an explicitly heuristic quality score. All acceptance boxes start unchecked.
5. Correct endpoint coordinates in metres. Reviewed bars must remain parallel; spacing is perpendicular centreline distance for pairs with overlapping longitudinal extents. All such pairs are reported, not just adjacent pairs. Evidence remains associated with the original detected endpoints and records manual adjustments.
6. Check accepted bars. Green overlays identify them. Create native 12-sided capped cylinder groups, with `IfcReinforcingBar` tags and per-bar evidence. The diameter remains labelled **design input**. One history command adds geometry and evidence together; one Undo removes both and Redo restores both.
7. Save a disposable IGZ to retain groups, tags, extension data, and complete inspection reports. Export JSON evidence separately if needed.

## Evidence and limits

Reports include source SHA-256, exact source point indices, source units/origin/CRS, local-to-world affine matrix, ROI, detector parameters/seed, endpoints before and after review, support, residual, axial coverage, quality heuristic, all overlapping pair spacings, accepted group UIDs, and UTC review time.

This is an experimental P0/P1 prototype. Quality is not a calibrated probability or a compliance decision. Partial-surface visibility, occlusion, noise, very close bars, an inaccurate supplied direction, multiple layers/families, and bent bars can produce biased or missed candidates. Diameter is not measured from the scan. Concrete cover is not calculated. No tolerance-based compliance report is generated. Analyze again after any document edit or scan movement.

Analysis and hashing currently run synchronously. Very large source files and ROIs need a background worker and cancellation before field use. The existing cloud manager does not automatically reload point-cloud arrays from a reopened IGZ; inspection results/native geometry persist, but clouds must be imported again. A real Rohbau3D floor negative control has been exercised and produces false positives: see [trial report](ROHBAU3D_TRIAL.md). No positive exposed-rebar scan ground truth or live OpenGL interaction has been validated here. CRS conversion, vertical-datum reconciliation, survey calibration, automatic layer segmentation, and a calibrated uncertainty model remain future work.
