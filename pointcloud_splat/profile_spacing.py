# SPDX-License-Identifier: GPL-3.0-or-later
"""Spacing from paired, observed axial sections; never extrapolate a bar.

Straight CAD representatives and their spacing remain separate. This records
spatial variation of scanned support, not statistical measurement uncertainty.
"""
import numpy as np


def theil_sen(x, y):
    """Median pairwise slope: one cluttered section cannot steer the trend."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    i, j = np.triu_indices(len(x), 1)
    keep = x[j] != x[i]
    if not keep.any() or not (np.isfinite(x).all() and np.isfinite(y).all()):
        raise ValueError('Trend needs finite values at two distinct axial positions')
    slope = float(np.median((y[j]-y[i])[keep]/(x[j]-x[i])[keep]))
    return slope, float(np.median(y-slope*x))


def axial_trend(sections, side):
    """Describe how observed spacing changes along the shared support.

    Non-parallel or bowed bars make one summary value station dependent. The
    trend reports that dependence; it never changes or replaces the median.
    """
    axial = np.array([np.mean(s['axial_interval_m']) for s in sections])
    values = np.array([s['spacing_m'] for s in sections])
    slope, intercept = theil_sen(axial, values)
    lateral = np.array([s['centres_transverse_m'] for s in sections])@side
    drift = [float(np.degrees(np.arctan(theil_sen(axial, lateral[:, k])[0]))) for k in range(2)]
    ends = [float(axial.min()), float(axial.max())]
    return {'basis': 'theil_sen_section_spacing_vs_axial_position',
            'slope_m_per_m': slope, 'section_axial_range_m': ends,
            'fitted_spacing_at_range_ends_m': [intercept+slope*ends[0], intercept+slope*ends[1]],
            'fitted_change_m': slope*(ends[1]-ends[0]),
            'section_spacing_range_m': [float(values.min()), float(values.max())],
            'lateral_drift_deg': drift, 'lateral_axis': side.tolist(),
            'station_registered': False, 'is_uncertainty': False}


def paired_profile_spacing(points, source_ids, bars, direction, normal, diameter,
                           min_length=.25):
    direction = np.asarray(direction, dtype=float)
    direction = direction/np.linalg.norm(direction)
    side = np.cross(normal, direction); side /= np.linalg.norm(side)
    order = sorted(range(len(bars)), key=lambda i: np.asarray(bars[i]['start'])@side)
    # Source IDs need not be consecutive or sorted after import/ROI filtering.
    lookup = {int(value): i for i, value in enumerate(source_ids)}
    samples = [points[[lookup[int(k)] for k in bar['evidence']['point_indices']]] for bar in bars]
    cell = 2*diameter
    records = []
    for ia, ib in zip(order, order[1:]):
        pair = sorted([ia,ib])
        intervals = [np.sort(np.asarray([bars[i]['start'],bars[i]['end']])@direction) for i in pair]
        low = float(max(x[0] for x in intervals)); high = float(min(x[1] for x in intervals))
        bins = max(0, int(np.floor((high-low)/cell)))
        row = {'bars': pair, 'basis': 'detected_source_support_before_manual_review',
               'cell_m': cell, 'overlap_m': [low,high], 'minimum_cell_points': 3,
               'minimum_paired_coverage': .75, 'minimum_overlap_m': min_length,
               'status': 'unavailable_scan_support', 'median_m': None, 'sections': []}
        records.append(row)
        if bins*cell < min_length:
            continue
        profiles = []
        for i in pair:
            p = samples[i];axial = p@direction
            keys = np.floor((axial-low)/cell).astype(int)
            profile = {}
            for k in np.unique(keys[(keys>=0)&(keys<bins)]):
                sample = p[keys==k]
                if len(sample)>=3:
                    transverse = sample-np.outer(sample@direction,direction)
                    profile[int(k)] = (np.median(transverse,axis=0),len(sample))
            profiles.append(profile)
        common = sorted(set(profiles[0])&set(profiles[1]))
        row['paired_coverage'] = len(common)/bins
        for k in common:
            a,b=profiles[0][k],profiles[1][k]
            row['sections'].append({'axial_interval_m':[low+k*cell,low+(k+1)*cell],
                                    'centres_transverse_m':[a[0].tolist(),b[0].tolist()],
                                    'support_counts':[a[1],b[1]],
                                    'spacing_m':float(np.linalg.norm(a[0]-b[0]))})
        if len(common)*cell < min_length or row['paired_coverage'] < .75:
            continue
        values = [s['spacing_m'] for s in row['sections']]
        row.update(status='measured',median_m=float(np.median(values)),
                   spatial_q10_q90_m=np.quantile(values,[.1,.9]).tolist())
        if len(values) > 1:  # One section has no observable trend.
            row['axial_trend'] = axial_trend(row['sections'],side)
    return {'enabled':True, 'method':'paired_axial_section_medians',
            'variation_is_uncertainty':False, 'pairs':records}
