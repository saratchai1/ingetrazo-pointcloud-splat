# SPDX-License-Identifier: GPL-3.0-or-later
"""Assisted depth-band selection along an explicitly supplied world normal.

The strongest depth mode is a scan-support heuristic, not a semantic rebar
classifier. Users must crop out unrelated foreground/background first.
"""
import numpy as np


def select_layer(points, ids, normal, diameter, *, rank=0):
    normal = np.asarray(normal, dtype=float)
    if normal.shape != (3,) or not np.isfinite(normal).all() or np.linalg.norm(normal) < 1e-12:
        raise ValueError('Provide a finite nonzero layer normal')
    if not isinstance(rank, int) or rank < 0:
        raise ValueError('Layer rank must be a nonnegative integer')
    normal = normal / np.linalg.norm(normal)
    info = {'enabled': True, 'normal': normal.tolist(), 'selected_rank': rank,
            'bin_m': diameter / 4, 'half_width_m': .75 * diameter,
            'mode_separation_m': 2 * diameter, 'modes': [],
            'mode_inventory_limit': 32, 'inventory_truncated': False,
            'excluded_point_indices': [], 'removed_points': 0, 'retained_points': len(points)}
    if not len(points):
        return points, ids, info
    depth = points @ normal
    # Relative histogram avoids allocating a world-origin-sized bin array.
    anchor = float(depth.min())
    count = int(np.floor((depth.max()-anchor)/info['bin_m'])) + 1
    if count > 100000:
        raise ValueError('Narrow depth ROI before selecting a layer')
    hist, edges = np.histogram(depth, bins=count, range=(anchor, anchor+count*info['bin_m']))
    smooth = np.convolve(np.pad(hist, (2, 2)), [1, 2, 3, 2, 1], mode='valid')
    centres = (edges[:-1]+edges[1:])/2
    # Nonmaximum suppression lists resolved depth modes in support order.
    peaks = np.flatnonzero((smooth >= np.r_[0, smooth[:-1]]) &
                           (smooth >= np.r_[smooth[1:], 0]) & (smooth > 0))
    for i in peaks[np.argsort(-smooth[peaks], kind='stable')]:
        centre = float(centres[i])
        if any(abs(centre-m['depth_m']) < info['mode_separation_m'] for m in info['modes']):
            continue
        support = int(np.count_nonzero(abs(depth-centre) <= info['half_width_m']))
        info['modes'].append({'depth_m': centre, 'support': support, 'peak_score': int(smooth[i])})
        if len(info['modes']) == info['mode_inventory_limit']:
            info['inventory_truncated'] = True
            break
    if rank >= len(info['modes']):
        raise ValueError('Requested layer rank is unavailable')
    centre = info['modes'][rank]['depth_m']
    keep = abs(depth-centre) <= info['half_width_m']
    info['selected_depth_m'] = centre
    info['removed_points'] = int(np.count_nonzero(~keep))
    info['excluded_point_indices'] = ids[~keep].tolist()
    info['retained_points'] = int(np.count_nonzero(keep))
    return points[keep], ids[keep], info
