# Rohbau3D real-data trial: broad-surface rejection regression

The original a5ab718 detector produced **28 false rebar candidates** on a semantic Floor patch. The current detector first separates broad geometric surfaces and produces **0 candidates on the identical LAZ input and ROI**. It removes 5,995 of 6,000 floor points, leaving five isolated points. The floor fixture is now an automated regression, including a rotated vertical-wall analogue. No production document was opened or modified.

## Source and selection

Lukas Rauch and Thomas Braml, *Rohbau3D: A Shell Construction Site 3D Point Cloud Dataset*. Dataset [DOI 10.60776/ZWJFI4](https://doi.org/10.60776/ZWJFI4), paper [DOI 10.1038/s41597-025-05827-7](https://doi.org/10.1038/s41597-025-05827-7), [authors' repository](https://github.com/RauchLukas/rohbau3d). Data is CC BY 4.0. The inspected class registry has no specific rebar class.

Scene `site_02/scene_02000` contains 10,949,275 points. To avoid downloading a whole multi-gigabyte site archive, the first 1,000,000 XYZ/RGB/class records were streamed from the first scene in these Dataverse archives:

- Coordinates: file ID 1238, member `site_02/scene_02000/coord.npy`.
- Semantic labels: file ID 7375, member `site_02/scene_02000/class.npy`.
- RGB: file ID 1237, member `site_02/scene_02000/color.npy`.
- Class registry: file ID 7447.

This is a contiguous prefix (9.13% of one scene), not a randomized sample or a representative full-scene benchmark. Prefix labels are None 10,346; Ceiling 298,505; Floor 247,285; Wall 443,864. Source XYZ is already float32; converting it cannot recover any precision lost before publication. The paper describes individual scanner-centred coordinate systems; different scans must not be assumed registered together.

## Import result

Every fifth prefix record was selected to make a 200,000-point LAZ preview. Coordinates were promoted to float64 before writing, with a 1 micrometre LAS scale, origin zero, confirmed metres, and `source_index`/`rohbau_class` extra dimensions. Loading through this extension and reconstructing source coordinates gave a maximum absolute error of approximately 0.5 micrometres. This measures software conversion roundtrip, not scanner accuracy or rebar measurement accuracy.

## Negative-control result

Select semantic Floor class 4 in source ROI `[1.2, -0.7, -1.5]` to `[1.8, -0.1, -1.3]` metres. This contains 51,472 points. Retain 6,000 records at `linspace(0, count-1, 6000, dtype=int)` positions in the filtered record sequence. Export these as LAZ with the same coordinate settings. Call `inspect` using direction `[1,0,0]`, design diameter 0.016 m, minimum support 30, minimum length 0.25 m, seed 0, and that same world ROI.

The original a5ab718 detector produced **28 false candidates** on this floor patch. Axis-constrained clustering partitions a continuous planar surface into thin longitudinal bands, which can satisfy the existing line-support/coverage criteria. Heuristic confidence does not reliably distinguish these bands from bars. Candidate acceptance remains false throughout.

## Surface-separation fix and controls

The current geometric prefilter uses deterministic sampled RANSAC with plane refinement. A plane is removed only when it has sufficiently broad support in two directions AND dense 2D cell occupancy at the design-diameter scale. Coplanarity alone is never sufficient: three parallel bars in one plane must not be treated as a solid floor. No semantic labels are used in filtering.

The exact same fixture (SHA-256 checked against the earlier trial evidence) now yields 0 bar candidates; 5,995 points are attributed to an excluded plane and five remain. Reports retain plane equations in world metres, coverage, filter parameters and removed source record indices. A summary of excluded surface points is shown in the review dialog.

Validation: 34 tests pass on each of the customized core and upstream core (24 extension cases plus 10 host plugin-data cases). Controls include this real floor patch, its rotated wall analogue, synthetic bars alone, coplanar bars, and bars mixed with both a floor and wall in ordinary and rotated coordinates. The three synthetic bars remain detected and their pair spacings remain 150, 150 and 300 mm within the existing 1 mm test tolerance. This is not a claim of field measurement accuracy.

Before field use, evaluate against exposed-rebar scans with independently measured geometry. Sparse, perforated or curved backgrounds may remain; points within the removal tolerance of a supporting plane can be lost. The prefilter considers at most four broad planes per ROI. This trial does not establish positive rebar detection precision, recall, diameter accuracy or spacing accuracy. Live OpenGL interaction was not exercised.
