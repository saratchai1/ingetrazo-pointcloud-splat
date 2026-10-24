# SPDX-License-Identifier: GPL-3.0-or-later
"""Group weak overlapping proposals within one explicitly selected thin layer.

Keep the strongest fit, without pretending the additional noisy support fits its
cylinder. Grouped proposals remain separate evidence and need human review.
"""
import numpy as np


def group_layer_duplicates(bars, direction, normal, diameter):
    normal = np.asarray(normal, dtype=float)
    direction = np.asarray(direction, dtype=float)
    side = np.cross(normal, direction)
    side /= np.linalg.norm(side)
    info = {'grouped_proposals': 0, 'max_distance_m': diameter,
            'max_in_plane_distance_m': .75 * diameter, 'max_depth_distance_m': diameter,
            'minimum_weaker_overlap': .8, 'minimum_support_ratio': 4.}
    retained = []
    for bar in sorted(bars, key=lambda b: -b['evidence']['support']):
        ends = np.array([bar['start'], bar['end']])
        interval = sorted(ends @ direction)
        for primary in retained:
            if primary['evidence']['support'] < 4 * bar['evidence']['support']:
                continue
            other = np.array([primary['start'], primary['end']])
            other_interval = sorted(other @ direction)
            overlap = min(interval[1], other_interval[1])-max(interval[0], other_interval[0])
            if overlap < .8 * (interval[1]-interval[0]):
                continue
            delta = ends.mean(0)-other.mean(0)
            distance = float(np.linalg.norm(delta-(delta@direction)*direction))
            if (distance > diameter or abs(delta@side) > .75*diameter or
                    abs(delta@normal) > diameter):
                continue
            primary.setdefault('grouped_duplicate_proposals', []).append({
                'proposal': bar, 'centreline_distance_m': distance,
                'weaker_axial_overlap_fraction': float(overlap/(interval[1]-interval[0])),
                'reason': 'weak_overlapping_proposal_in_selected_layer',
                'review_required': True, 'used_for_primary_fit': False})
            info['grouped_proposals'] += 1
            break
        else:
            retained.append(bar)
    return retained, info
