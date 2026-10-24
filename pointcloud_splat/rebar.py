# SPDX-License-Identifier: GPL-3.0-or-later
"""Assisted, single-layer parallel straight-bar inspection; all distances in metres.

A user supplies approximate bar direction and design diameter. Confidence is a
sampling-quality heuristic, never a probability of compliance. Partial surface
scans can bias centre estimates: review against the scan before acceptance.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import numpy as np


def inspect(dataset, minimum, maximum, direction, diameter_m=.016,
            min_support=30, min_length=.25, seed=0, viewport=None,
            layer_normal=None, layer_rank=0, scan_noise_m=0.):
    if not getattr(dataset, 'coordinate_frame', None):
        raise ValueError('Inspection needs a LAS/LAZ dataset with confirmed units')
    if not .001 <= diameter_m <= .1 or min_support < 3 or min_length <= 0:
        raise ValueError('Invalid detection parameters')
    direction = np.asarray(direction, dtype=float)
    if direction.shape != (3,) or not np.isfinite(direction).all() or np.linalg.norm(direction) < 1e-12:
        raise ValueError('Provide a finite nonzero direction')
    direction /= np.linalg.norm(direction)
    points, ids = dataset.world_roi(minimum, maximum, viewport)
    if dataset.source_point_indices is not None:
        ids = dataset.source_point_indices[ids]
    if len(points) > 200000:
        raise ValueError('Narrow ROI to at most 200,000 points for assisted analysis')
    if not np.isfinite(scan_noise_m) or not 0 <= scan_noise_m <= .05:
        raise ValueError('Scan noise allowance must be between 0 and 50 mm')
    if scan_noise_m and layer_normal is None:
        raise ValueError('Density analysis needs a supplied layer normal')
    roi_points = len(points)
    from .background import separate_surfaces
    points, ids, background = separate_surfaces(points, ids, diameter_m, seed=seed, min_support=min_support)
    layer = {'enabled': False, 'removed_points': 0}
    if layer_normal is not None:
        from .layers import select_layer
        points, ids, layer = select_layer(points, ids, layer_normal, diameter_m, rank=layer_rank, noise_m=scan_noise_m)
        if abs(np.dot(layer['normal'], direction)) > np.sin(np.radians(5)):
            raise ValueError('Layer normal must be perpendicular to the bar direction')
    transverse = points - np.outer(points @ direction, direction)
    remaining = np.arange(len(points))
    rng = np.random.default_rng(seed)
    bars = []
    clusters = []
    radius = diameter_m * .8 + 2*scan_noise_m
    from .bar_tracks import continuous_tracks, axial_cell_centre
    density = {'enabled': False}
    if scan_noise_m:
        from .density_tracks import density_proposals
        clusters, density = density_proposals(points, direction, layer['normal'], diameter_m, scan_noise_m, min_support)
        refined = []
        for cluster in clusters:
            for _ in range(8):
                centre = axial_cell_centre(points[cluster], direction, diameter_m, radius)
                centre -= (centre@direction)*direction
                keep = cluster[np.linalg.norm(transverse[cluster]-centre,axis=1)<=radius]
                if len(keep)<min_support or len(keep)==len(cluster):
                    cluster = keep
                    break
                cluster = keep
            if len(cluster)>=min_support:
                refined.append(cluster)
        clusters = refined
    else:
        from .spatial_candidates import TransverseIndex
        index = TransverseIndex(transverse, direction, radius)
        active = np.ones(len(points), dtype=bool)
        while len(remaining) >= min_support:
            candidates = rng.choice(remaining, min(128, len(remaining)), replace=False)
            best = np.empty(0, dtype=int)
            for idx in candidates:
                nearby = index.nearby(transverse[idx], radius*2, active)
                chosen = nearby[np.linalg.norm(transverse[nearby]-transverse[idx], axis=1) <= radius*2]
                if len(chosen) > len(best):
                    best = chosen
            if len(best) < min_support:
                break
            centre = np.median(transverse[best], axis=0)
            nearby = index.nearby(centre, radius, active)
            best = nearby[np.linalg.norm(transverse[nearby]-centre, axis=1) <= radius]
            if len(best) < min_support:
                active[candidates] = False
                remaining = np.flatnonzero(active)
                continue
            active[best] = False
            remaining = np.flatnonzero(active)
            clusters.append(best)
    tracks, track_filter = continuous_tracks(points, clusters, direction, diameter_m, min_support, min_length, support_radius=radius, robust_centres=bool(scan_noise_m))
    for best, centre, low, high, occupied, q95 in tracks:
        bars.append({'start': (centre+low*direction).tolist(), 'end': (centre+high*direction).tolist(),
                     'diameter_m': diameter_m, 'diameter_basis': 'design_input', 'accepted': False,
                     'evidence': {'point_indices': ids[best].tolist(), 'support': len(best),
                                  'residual_p95_m': q95, 'axial_coverage': occupied,
                                  'centre_estimator': 'axial_bin_median' if scan_noise_m else 'mean',
                                  'noise_allowance_m': scan_noise_m, 'support_radius_m': radius,
                                  'max_axial_gap_m': float(np.diff(np.sort(points[best] @ direction)).max()),
                                  'confidence_heuristic': float(occupied * min(1, len(best)/(2*min_support)) * max(0, 1-q95/(2*radius)))}})
    duplicates = {'grouped_proposals': 0}
    if layer.get('enabled'):
        from .duplicates import group_layer_duplicates
        bars, duplicates = group_layer_duplicates(bars, direction, layer['normal'], diameter_m)
    bars.sort(key=lambda bar: tuple(np.asarray(bar['start'])-np.dot(bar['start'], direction)*direction))
    source_hash = None
    if dataset.filepath and Path(dataset.filepath).is_file():
        with open(dataset.filepath, 'rb') as stream:
            source_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    basis = dataset.apply_transform(np.vstack((np.zeros(3), np.eye(3))), viewport)
    affine = np.eye(4)
    affine[:3, :3] = (basis[1:]-basis[0]).T
    affine[:3, 3] = basis[0]
    return {'local_to_world_4x4': affine.tolist(), 'schema': 1, 'algorithm': 'parallel-layer-density-v5', 'seed': seed,
            'source': dataset.filepath, 'source_sha256': source_hash,
            'coordinate_frame': deepcopy(dataset.coordinate_frame),
            'world_roi_m': np.asarray([minimum, maximum]).tolist(),
            'direction': direction.tolist(), 'parameters': {'diameter_m': diameter_m,
            'min_support': min_support, 'min_length_m': min_length, 'scan_noise_m': scan_noise_m},
            'roi_points': roi_points, 'density_proposals': density, 'layer_filter': layer, 'duplicate_filter': duplicates,
            'background_filter': background, 'track_filter': track_filter, 'bars': bars, 'spacing': spacing(bars, direction),
            'limitations': 'One parallel family in one layer. Partial surfaces bias centres; diameter is design input. Confidence is heuristic. Review required.'}


def spacing(bars, direction):
    """Pairwise centreline spacing with overlapping axial intervals, in metres."""
    d = np.asarray(direction, dtype=float)
    if d.shape != (3,) or not np.isfinite(d).all() or np.linalg.norm(d) < 1e-12:
        raise ValueError('Invalid spacing direction')
    d /= np.linalg.norm(d)
    for bar in bars:
        ends = np.asarray([bar['start'], bar['end']], dtype=float)
        if ends.shape != (2, 3) or not np.isfinite(ends).all() or np.linalg.norm(ends[1]-ends[0]) < 1e-9:
            raise ValueError('Invalid bar endpoints')
    result = []
    for i, a in enumerate(bars):
        for j in range(i+1, len(bars)):
            b = bars[j]
            aa, bb = np.asarray([a['start'], a['end']]), np.asarray([b['start'], b['end']])
            for ends in (aa, bb):
                v = ends[1]-ends[0]
                if np.linalg.norm(v) < 1e-9 or abs(v @ d)/np.linalg.norm(v) < np.cos(np.radians(.1)):
                    raise ValueError('Reviewed bars must remain parallel to the detection direction')
            ar, br = sorted(aa @ d), sorted(bb @ d)
            if min(ar[1], br[1]) <= max(ar[0], br[0]):
                continue
            delta = bb.mean(axis=0)-aa.mean(axis=0)
            result.append({'bars': [i, j], 'centreline_m': float(np.linalg.norm(delta-(delta@d)*d)),
                           'axial_overlap_m': float(min(ar[1], br[1])-max(ar[0], br[0]))})
    return result


def commit_review(history, report):
    """Native cylinder groups + evidence in one atomic Undo/Redo transaction."""
    from core.history import Command, SetPluginDataCommand
    from core.group import Group
    from core.mesh import Mesh
    from PySide6.QtGui import QVector3D
    report = deepcopy(report)
    selected = [b for b in report['bars'] if b.get('accepted')]
    if not selected:
        raise ValueError('Accept at least one reviewed bar')
    report['spacing'] = spacing(selected, report['direction'])
    report['spacing_index_basis'] = 'accepted_bars_only'
    from datetime import datetime, timezone
    report['reviewed_at_utc'] = datetime.now(timezone.utc).isoformat()
    groups = []
    for index, bar in enumerate(selected):
        ends = np.asarray([bar['start'], bar['end']], dtype=float)
        if not np.isfinite(ends).all() or np.max(np.abs(ends)) > 10000:
            raise ValueError('Native geometry requires finite local coordinates within 10 km')
        axis = ends[1]-ends[0]
        axis /= np.linalg.norm(axis)
        u = np.cross(axis, np.eye(3)[np.argmin(np.abs(axis))]); u /= np.linalg.norm(u)
        v = np.cross(axis, u)
        radius = float(bar['diameter_m'])/2
        if not .0005 <= radius <= .05:
            raise ValueError('Invalid design diameter')
        rings = [[QVector3D(*map(float, end+radius*(u*np.cos(t)+v*np.sin(t))))
                  for t in np.linspace(0, 2*np.pi, 12, endpoint=False)] for end in ends]
        mesh = Mesh()
        mesh.add_face(list(reversed(rings[0])))
        mesh.add_face(rings[1])
        for k in range(12):
            mesh.add_face([rings[0][k], rings[0][(k+1)%12], rings[1][(k+1)%12], rings[1][k]])
        group = Group(mesh, name=f'Rebar {index+1} (design Ø{radius*2000:g} mm)')
        group.ifc = {'class': 'IfcReinforcingBar', 'name': group.name}
        group.ext = {'rebar_inspection': deepcopy(bar)}
        groups.append(group)
    report['native_group_uids'] = [group.uid for group in groups]
    class CreateInspection(Command):
        def __init__(self):
            self.data_command = None

        def do(self, scene):
            if self.data_command is None:
                data = deepcopy(scene.plugin_data.get('rebar_inspection', {'schema': 1, 'reports': []}))
                data['reports'].append(report)
                self.data_command = SetPluginDataCommand('rebar_inspection', data)
            # Construct/validate everything before changing the scene.
            self.data_command.do(scene)
            scene.groups.extend(groups)
            scene.version += 1

        def undo(self, scene):
            for group in groups:
                if group in scene.groups:
                    scene.groups.remove(group)
                scene.selection.discard(group)
            self.data_command.undo(scene)
            scene.version += 1

    history.execute(CreateInspection())
    return groups
