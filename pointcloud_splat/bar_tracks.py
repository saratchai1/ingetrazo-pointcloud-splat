# SPDX-License-Identifier: GPL-3.0-or-later
"""Continuity checks for guided straight tracks, in metres.

Thresholds scale with the supplied design diameter, never reference bar counts
or spacing. Missing scan support is a reason to withhold a candidate.
"""
import numpy as np


def axial_cell_centre(sample, direction, diameter, radius):
    """Equal axial-cell influence limits dense crossings and local anchors."""
    axial = sample @ direction
    transverse = sample-np.outer(axial,direction)
    keys = np.floor((axial-np.quantile(axial,.01))/max(2*diameter,.5*radius)).astype(int)
    medians = [np.median(transverse[keys==key],axis=0)
               for key in np.unique(keys) if np.count_nonzero(keys==key)>=3]
    if not medians:
        return sample.mean(0)
    return np.median(medians,axis=0)+axial.mean()*direction


def _track_pass(points, clusters, direction, diameter, min_support, min_length, support_radius=None, robust_centres=False):
    """Consolidate nearby proposals, then split at unsupported axial gaps."""
    radius = diameter * .8 if support_radius is None else support_radius
    diagnostics = {'merged_proposals': 0, 'rejected_short_or_sparse': 0,
                   'rejected_coverage': 0, 'rejected_direction': 0, 'rejected_width': 0,
                   'max_gap_m': diameter * 3, 'coverage_cell_m': diameter * 2,
                   'minimum_coverage': .75, 'merge_distance_m': diameter,
                   'max_residual_p95_m': radius}
    axial = points @ direction
    transverse = points - np.outer(axial, direction)
    # Largest supports first, with deterministic tie-breaking. Merge only when
    # the combined support still fits one physical bar envelope. All original
    # indices are retained, and a second pass tests its actual continuity.
    pending = sorted(clusters, key=lambda ids: (-len(ids), int(np.min(ids))))
    consolidated = []
    for ids in pending:
        centre = transverse[ids].mean(0)
        interval = np.quantile(axial[ids], [.01, .99])
        for k, previous in enumerate(consolidated):
            other_centre = transverse[previous].mean(0)
            other_interval = np.quantile(axial[previous], [.01, .99])
            if np.linalg.norm(centre-other_centre) > diameter:
                continue
            if min(interval[1], other_interval[1]) <= max(interval[0], other_interval[0]):
                continue
            combined = np.union1d(previous, ids)
            residual = np.linalg.norm(transverse[combined]-transverse[combined].mean(0), axis=1)
            if np.quantile(residual, .95) <= radius:
                consolidated[k] = combined
                diagnostics['merged_proposals'] += 1
                break
        else:
            consolidated.append(ids)
    tracks = []
    for ids in consolidated:
        ordered = ids[np.argsort(axial[ids], kind='stable')]
        cuts = np.flatnonzero(np.diff(axial[ordered]) > diagnostics['max_gap_m']) + 1
        for segment in np.split(ordered, cuts):
            if len(segment) < min_support:
                diagnostics['rejected_short_or_sparse'] += 1
                continue
            low, high = np.quantile(axial[segment], [.01, .99])
            if high-low < min_length:
                diagnostics['rejected_short_or_sparse'] += 1
                continue
            bins = max(1, int(np.ceil((high-low)/diagnostics['coverage_cell_m'])))
            coverage = np.count_nonzero(np.histogram(axial[segment], bins=bins, range=(low, high))[0])/bins
            if coverage < diagnostics['minimum_coverage']:
                diagnostics['rejected_coverage'] += 1
                continue
            sample = points[segment]
            centre = sample.mean(0)
            if robust_centres:
                centre = axial_cell_centre(sample, direction, diameter, radius)
            _, _, axes = np.linalg.svd(sample-centre, full_matrices=False)
            if abs(axes[0] @ direction) < np.cos(np.radians(5)):
                diagnostics['rejected_direction'] += 1
                continue
            residual = np.linalg.norm(transverse[segment]-(centre-(centre@direction)*direction), axis=1)
            q95 = float(np.quantile(residual, .95))
            if q95 > radius:
                diagnostics['rejected_width'] += 1
                continue
            tracks.append((segment, centre, low-centre@direction, high-centre@direction,
                           float(coverage), q95))
    return tracks, diagnostics


def continuous_tracks(points, clusters, direction, diameter, min_support, min_length, support_radius=None, robust_centres=False):
    """Consolidate again after disconnected support has been removed.

    Raw proposal centres can be biased by isolated points at other depths. Once
    split, overlapping valid segments may fit one envelope even if their raw
    proposals could not merge. Each successful pass strictly reduces tracks.
    """
    tracks, diagnostics = _track_pass(points, clusters, direction, diameter, min_support, min_length, support_radius, robust_centres)
    diagnostics['post_split_merges'] = 0
    while len(tracks) > 1:
        refined, stats = _track_pass(points, [track[0] for track in tracks], direction,
                                     diameter, min_support, min_length, support_radius, robust_centres)
        if not stats['merged_proposals']:
            break
        diagnostics['post_split_merges'] += stats['merged_proposals']
        diagnostics['merged_proposals'] += stats['merged_proposals']
        for key in ('rejected_short_or_sparse', 'rejected_coverage', 'rejected_direction', 'rejected_width'):
            diagnostics[key] += stats[key]
        if len(refined) >= len(tracks):
            raise RuntimeError('Track consolidation did not reduce candidates')
        tracks = refined
    return tracks, diagnostics
