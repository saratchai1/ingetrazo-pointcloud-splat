# SPDX-License-Identifier: GPL-3.0-or-later
"""Independent geometric measurement support for noisy straight-bar candidates.

Detection allowance controls proposals/acceptance, not the sampling window of
an already matched measurement. Fixed diameter-based windows are geometric
heuristics, never scanner calibration or a claimed measurement uncertainty.
"""
from copy import deepcopy
import numpy as np
from .bar_tracks import axial_cell_centre, continuous_tracks
from .density_tracks import density_proposals
from .profile_spacing import paired_profile_spacing


def match_tracks(bars, tracks, direction, diameter, min_length):
    """Require unique matches in both directions; do not choose a best subset."""
    direction = np.asarray(direction, dtype=float)
    candidates = []
    for bar in bars:
        ends = np.asarray([bar['start'],bar['end']]);interval = np.sort(ends@direction)
        options = []
        for j, track in enumerate(tracks):
            other = np.asarray([track['start'],track['end']]);span = np.sort(other@direction)
            delta = ends.mean(0)-other.mean(0)
            distance = np.linalg.norm(delta-(delta@direction)*direction)
            overlap = min(interval[1],span[1])-max(interval[0],span[0])
            if distance <= 2*diameter and overlap >= max(min_length,.8*min(np.ptp(interval),np.ptp(span))):
                options.append(j)
        candidates.append(options)
    return [{'bar':i, 'candidate_measurement_tracks':options,
             'measurement_track':options[0] if len(options)==1 and
                 sum(options[0] in others for others in candidates)==1 else None}
            for i,options in enumerate(candidates)]


def fixed_support_spacing(points, source_ids, bars, direction, normal, diameter,
                          layer_depth, min_support=30, min_length=.25):
    direction = np.asarray(direction, dtype=float)
    normal = np.asarray(normal, dtype=float)
    radius = 3*diameter
    info = {'basis':'surface_rejected_roi_before_noise_dependent_depth_crop',
            'layer_depth_m':layer_depth,'layer_half_width_m':2*diameter,
            'support_radius_m':radius,'window_basis':'fixed_design_diameter_heuristic',
            'mapping_distance_m':2*diameter,'minimum_weaker_overlap':.8,
            'measurement_tracks':[], 'matches':[]}
    keep = np.zeros(len(points), dtype=bool) if layer_depth is None else abs(points@normal-layer_depth)<=2*diameter
    points = points[keep];source_ids = source_ids[keep]
    info['retained_points'] = len(points)
    clusters, info['density_proposals'] = density_proposals(
        points,direction,normal,diameter,0.,min_support,support_radius_m=radius)
    transverse = points-np.outer(points@direction,direction)
    refined = []
    for cluster in clusters:
        for _ in range(8):
            centre = axial_cell_centre(points[cluster],direction,diameter,radius)
            centre -= (centre@direction)*direction
            ids = cluster[np.linalg.norm(transverse[cluster]-centre,axis=1)<=radius]
            if len(ids)<min_support or len(ids)==len(cluster):
                cluster = ids
                break
            cluster = ids
        if len(cluster)>=min_support:
            refined.append(cluster)
    tracks, info['track_filter'] = continuous_tracks(
        points,refined,direction,diameter,min_support,min_length,
        support_radius=radius,robust_centres=True)
    fitted = info['measurement_tracks']
    for ids,centre,lo,hi,coverage,q95 in tracks:
        fitted.append({'start':(centre+lo*direction).tolist(),'end':(centre+hi*direction).tolist(),
                       'evidence':{'point_indices':source_ids[ids].tolist(),'support':len(ids),
                                   'residual_p95_m':q95,'axial_coverage':coverage}})
    matches = info['matches'] = match_tracks(bars,fitted,direction,diameter,min_length)
    profile = paired_profile_spacing(points,source_ids,fitted,direction,normal,diameter,min_length)
    lookup = {tuple(p['bars']):p for p in profile['pairs']}
    side = np.cross(normal,direction);side /= np.linalg.norm(side)
    order = sorted(range(len(bars)),key=lambda i:np.asarray(bars[i]['start'])@side)
    pairs = []
    for ia,ib in zip(order,order[1:]):
        row = {'bars':sorted([ia,ib]),'basis':'independent_measurement_support_before_manual_review',
               'status':'unavailable_scan_support','median_m':None,'sections':[],
               'reason':'missing_or_ambiguous_measurement_track'}
        ma,mb = matches[ia]['measurement_track'],matches[ib]['measurement_track']
        if ma is not None and mb is not None:
            key = tuple(sorted([ma,mb]))
            if key in lookup:
                row = deepcopy(lookup[key])
                native_pair = sorted([ia,ib])
                mapped = [matches[i]['measurement_track'] for i in native_pair]
                permutation = [key.index(i) for i in mapped]
                for section in row['sections']:
                    for field in ('centres_transverse_m','support_counts'):
                        section[field] = [section[field][i] for i in permutation]
                row.update(bars=native_pair,measurement_tracks=mapped,
                           basis='independent_measurement_support_before_manual_review')
            else:
                row['reason'] = 'measurement_tracks_not_adjacent'
        pairs.append(row)
    return {'enabled':True,'method':'fixed_support_paired_axial_sections',
            'variation_is_uncertainty':False,'measurement_support':info,'pairs':pairs}
