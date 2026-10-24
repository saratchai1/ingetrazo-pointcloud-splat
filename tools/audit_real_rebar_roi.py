# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only original-record visibility audit; never opens a CAD document.

Requires original t8 PLY and the saved --layer-mode dominant trial.json. RGB
corridors and organized record reconstruction are explicitly manual/provisional.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from pointcloud_splat.roi_audit import audit_traces, trace_records
from pointcloud_splat.grid_measurement import measure_grid
from pointcloud_splat.cell_validation import compare_cell_pairs, bound_matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ply', type=Path, required=True)
    parser.add_argument('--trial', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--matches', type=Path,
                        help='Optional independently anchored matches; use the emitted hash-bound template')
    args = parser.parse_args()
    root = Path(__file__).parents[1]
    annotations = json.loads((root/'docs/data/t8_rgb_traces.json').read_text())
    digest = hashlib.sha256(args.ply.read_bytes()).hexdigest()
    if digest != annotations['source_sha256']:
        raise ValueError('Annotations apply only to the exact original t8 source')
    with args.ply.open() as stream:
        header = []
        while True:
            line = stream.readline()
            if not line:
                raise ValueError('Truncated PLY')
            header.append(line.strip())
            if line.strip() == 'end_header':
                break
        if 'format ascii 1.0' not in header:
            raise ValueError('Expected original ASCII PLY')
        data = np.loadtxt(stream)
    width, height = annotations['width'], annotations['height']
    if data.shape != (width*height, 6):
        raise ValueError('Unexpected original record layout')
    xyz = data[:, :3]/1000
    valid = np.isfinite(xyz).all(1) & np.any(xyz != 0, 1)
    runs = [r for r in json.loads(args.trial.read_text())['runs'] if r['scan'] == 'drone-t8']
    row = runs[0]; report = row['report']
    if report['source_sha256'] != digest or not report['layer_filter']['enabled']:
        raise ValueError('Need original-source dominant-layer evidence')
    for run in runs[1:]:
        if (run['report']['source_sha256'] != digest or
                not np.allclose(run['rotation'], row['rotation']) or
                not np.allclose(run['centre_m'], row['centre_m']) or
                run['report']['world_roi_m'] != report['world_roi_m'] or
                run['report']['layer_filter'] != report['layer_filter']):
            raise ValueError('Family reports must use the same source, frame, ROI and layer')
    q = (xyz-row['centre_m']) @ np.array(row['rotation']).T
    raw = valid & np.all((xyz >= [-.03,-.6,.80]) & (xyz <= [.68,.14,1.12]), axis=1)
    low, high = np.array(report['world_roi_m'])
    slab = raw & np.all((q >= low) & (q <= high), axis=1)
    surface = slab.copy()
    for plane in report['background_filter']['planes']:
        surface[plane['removed_point_indices']] = False
    layer = surface.copy(); layer[report['layer_filter']['excluded_point_indices']] = False
    stages = {'source_box': raw, 'depth_slab': slab, 'surface_filter': surface, 'selected_layer': layer}
    audits = {str(radius): audit_traces(xyz, width, height, annotations['traces'], stages, radius=radius)
              for radius in (5, 15)}
    for records in audits.values():
        for trace in records:
            axis = np.array(runs[0 if trace['trace_id'].startswith('V') else 1]['report']['direction'])
            source_ids, _ = trace_records(trace['pixel_endpoints'], width, height, trace['radius_px'])
            source_ids = source_ids[valid[source_ids]]
            trace['valid_source_corridor_axial_p01_p99_span_m'] = (
                float(np.ptp(np.quantile(q[source_ids] @ axis, [.01,.99]))) if len(source_ids) else None)
            ids = trace['retained_original_record_ids']
            trace['retained_corridor_axial_p01_p99_span_m'] = (
                float(np.ptp(np.quantile(q[ids] @ axis, [.01,.99]))) if ids else None)
    assignments = []; named = {}
    for run in runs:
        for index, bar in enumerate(run['report']['bars']):
            ids = np.array(bar['evidence']['point_indices'], dtype=int)
            uv = np.column_stack([ids % width, ids // width])
            _, _, axes = np.linalg.svd(uv-uv.mean(0), full_matrices=False)
            alternatives = []
            for name, ends in annotations['traces'].items():
                ends = np.array(ends); delta = ends[1]-ends[0]; delta = delta/np.linalg.norm(delta)
                if abs(delta @ axes[0]) < np.cos(np.radians(20)):
                    continue
                normal = np.array([-delta[1], delta[0]])
                distance = abs((uv-ends[0]) @ normal)
                alternatives.append((float(np.median(distance)), name, float(np.quantile(distance,.95))))
            alternatives.sort()
            if not alternatives:
                continue
            distance, name, p95 = alternatives[0]
            margin = alternatives[1][0]-distance if len(alternatives)>1 else None
            matched = distance <= 25 and (margin is None or margin >= 25) and name not in named
            assignments.append({'candidate_id': f"F{run['family']}B{index+1}", 'scan_trace_id': name,
                                'median_distance_px': distance, 'p95_distance_px': p95,
                                'next_trace_margin_px': margin, 'matched': matched,
                                'basis': 'manual RGB trace alignment; not reference-diagram verification'})
            if matched:
                named[name] = bar
    columns = {name:named[name] for name in annotations['traces'] if name.startswith('V') and name in named}
    rows = {name:named[name] for name in annotations['traces'] if name.startswith('H') and name in named}
    grid = measure_grid(columns, rows, report['layer_filter']['normal'])
    reference_path = root/'docs/data/real_rebar_reference.json'
    ref = json.loads(reference_path.read_text())
    references = {}
    for kind, key in [('H','horizontal_midbay_spacing_mm'), ('V','vertical_midbay_spacing_mm')]:
        for ri, values in enumerate(ref[key]):
            for ci, value in enumerate(values):
                references[f'{kind}:{chr(65+ri)}{chr(66+ri)}/{ci+1}{ci+2}'] = value/1000
    measurements = {f"{kind}:{cell['scan_cell_id']}":cell[key] for cell in grid['cells']
                    for kind,key in [('H','horizontal_m'),('V','vertical_m')]}
    # Do not select a rotation/reflection/offset by minimizing tape errors.
    crosswalk = [{'reference_id': key, 'reference_m': value, 'measurement_id': None,
                  'verified': False, 'status': 'unavailable_unanchored_reference_labels'}
                 for key,value in references.items()]
    template = {'source_sha256': digest,
                'reference_sha256': hashlib.sha256(reference_path.read_bytes()).hexdigest(),
                'measurement_sha256': hashlib.sha256(json.dumps(
                    {'grid':grid, 'assignments':assignments},sort_keys=True,allow_nan=False).encode()).hexdigest(),
                'matches': []}
    matches = []
    if args.matches:
        supplied = json.loads(args.matches.read_text())
        matches = bound_matches(supplied, template)
    assessment = compare_cell_pairs(references, measurements, matches)
    crosswalk_by_id = {r['reference_id']:r for r in crosswalk}
    for pair in assessment['pairs']:
        crosswalk_by_id[pair['reference_id']].update(pair)
        crosswalk_by_id[pair['reference_id']]['measured_m'] = measurements[pair['measurement_id']]
    summary = {'source_sha256': digest, 'organized_record_layout': annotations['record_order_basis'],
               'record_order_independently_verified': False, 'annotations': annotations,
               'stage_counts': {k:int(v.sum()) for k,v in stages.items()},
               'trace_audits': audits, 'candidate_trace_assignments': assignments,
               'scan_grid': grid, 'reference_crosswalk': crosswalk, 'assessment': assessment,
               'candidate_measurements_m': measurements, 'match_template': template,
               'reference_mapping_blocker': annotations['reference_mapping_blocker'],
               'production_modified': False}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir/'audit.json').write_text(json.dumps(summary,indent=2)+'\n')
    (args.output_dir/'matches-template.json').write_text(json.dumps(template,indent=2)+'\n')
    print('Named scan tracks:', list(named), 'measured cells:', sum(c['status']=='measured' for c in grid['cells']))
    for r in audits['5']:
        print(r['trace_id'], r['in_image_records'], 'valid', r['valid_source_depth_records'],
              'selected', r['stages'][-1]['retained_records'])
    print('Reference assessment:', assessment['status'], assessment['scored_cells'])


if __name__ == '__main__':
    main()
