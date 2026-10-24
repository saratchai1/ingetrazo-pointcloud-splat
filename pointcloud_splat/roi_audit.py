# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline visibility audit in original organized scan-record coordinates.

RGB trace corridors are annotations, not verified steel point segmentation or
camera calibration. Invalid source depth must never be called ROI removal.
"""
import numpy as np


def trace_records(endpoints, width, height, radius=5):
    ends = np.asarray(endpoints, dtype=float)
    if ends.shape != (2, 2) or not np.isfinite(ends).all():
        raise ValueError('Trace needs two finite pixel endpoints')
    delta = ends[1]-ends[0]
    length = np.linalg.norm(delta)
    if not np.isfinite(length) or length == 0 or width <= 0 or height <= 0 or not isinstance(radius, int) or radius < 0:
        raise ValueError('Invalid trace dimensions or radius')
    steps = int(np.ceil(np.max(np.abs(delta))))+1
    if steps*(2*radius+1) > 10000000:
        raise ValueError('Trace corridor is too large')
    centre = ends[0]+np.linspace(0, 1, steps)[:, None]*delta
    normal = np.array([-delta[1], delta[0]])/length
    pixels = np.unique(np.round((centre[:, None]+np.arange(-radius, radius+1)[None, :, None]*normal)
                                .reshape(-1, 2)).astype(int), axis=0)
    inside = np.all((pixels >= [0, 0]) & (pixels < [width, height]), axis=1)
    ids = pixels[inside, 1]*width+pixels[inside, 0]
    return ids, int(np.count_nonzero(~inside))


def audit_traces(xyz, width, height, traces, stages, *, radius=5):
    xyz = np.asarray(xyz)
    if xyz.shape != (width*height, 3):
        raise ValueError('XYZ must preserve every original organized record')
    valid = np.isfinite(xyz).all(axis=1) & np.any(xyz != 0, axis=1)
    stages = {name: np.asarray(mask) for name, mask in stages.items()}
    previous = valid
    for name, mask in stages.items():
        if np.asarray(mask).shape != valid.shape or np.asarray(mask).dtype != np.bool_:
            raise ValueError('Stage masks must be boolean original-record arrays')
        if np.any(mask & ~previous):
            raise ValueError('Stage masks must be nested subsets of valid source depth')
        previous = mask
    rows = []
    for name, endpoints in traces.items():
        ids, outside = trace_records(endpoints, width, height, radius)
        row = {'trace_id': name, 'pixel_endpoints': endpoints, 'radius_px': radius,
               'in_image_records': len(ids), 'out_of_image_corridor_pixels': outside,
               'invalid_source_depth_records': int(np.count_nonzero(~valid[ids])),
               'valid_source_depth_records': int(np.count_nonzero(valid[ids])),
               'stages': [], 'annotation_basis': 'RGB corridor; not verified steel segmentation'}
        prior = valid
        for stage, mask in stages.items():
            row['stages'].append({'stage': stage, 'retained_records': int(np.count_nonzero(mask[ids])),
                                  'removed_at_stage': int(np.count_nonzero((prior & ~mask)[ids]))})
            prior = mask
        row['retained_original_record_ids'] = ids[prior[ids]].tolist()
        rows.append(row)
    return rows
