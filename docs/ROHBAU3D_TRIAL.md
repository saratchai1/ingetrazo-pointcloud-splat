# Rohbau3D real-data trial: negative control fails

The a5ab718 detector was exercised against a real scan subset from Rohbau3D, not only synthetic bars. Import/conversion succeeded, but a semantic Floor patch produced **28 false rebar candidates**. All candidates remained unaccepted; no production document was opened or modified. This failure is separate from the passing 29 automated synthetic/host tests.

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

The detector produces **28 false candidates** on this floor patch. Axis-constrained clustering partitions a continuous planar surface into thin longitudinal bands, which can satisfy the existing line-support/coverage criteria. Heuristic confidence does not reliably distinguish these bands from bars. Candidate acceptance remains false throughout.

Before field use, add and validate rejection of broad supporting surfaces/background, and evaluate against exposed-rebar scans with independently measured geometry. This trial does not establish positive rebar detection precision, recall, diameter accuracy or spacing accuracy. Live OpenGL interaction was not exercised.
