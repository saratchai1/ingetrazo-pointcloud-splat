# SPDX-License-Identifier: GPL-3.0-or-later
"""Conservative geometric broad-surface removal before guided bar detection.

A plane alone is insufficient: coplanar bars also fit planes. Require broad
support in TWO directions and dense occupancy at the design-diameter scale.
No semantic labels, world Z assumption, or class-specific scan metadata is used.
"""
import numpy as np


def separate_surfaces(points, point_ids, diameter_m, *, seed=0, min_support=30):
    points = np.asarray(points, dtype=np.float64)
    point_ids = np.asarray(point_ids)
    remaining = np.arange(len(points))
    rng = np.random.default_rng(seed)
    fit_tolerance = min(.003, diameter_m * .15)
    removal_tolerance = fit_tolerance * 3
    cell_size = diameter_m
    minimum_extent = max(.08, 6 * diameter_m)
    minimum_points = max(90, 3 * min_support)
    planes = []
    for _ in range(4):
        if len(remaining) < minimum_points:
            break
        sample_ids = rng.choice(remaining, min(6000, len(remaining)), replace=False)
        sample = points[sample_ids]
        hypotheses = []
        for _ in range(160):
            triangle = sample[rng.choice(len(sample), 3, replace=False)]
            normal = np.cross(triangle[1]-triangle[0], triangle[2]-triangle[0])
            norm = np.linalg.norm(normal)
            if norm < 1e-10:
                continue
            normal /= norm
            offset = -normal @ triangle[0]
            inliers = np.abs(sample @ normal + offset) <= fit_tolerance
            support = int(inliers.sum())
            if support >= minimum_points:
                hypotheses.append((support, normal, offset))
        accepted = None
        for _, normal, offset in sorted(hypotheses, key=lambda h: -h[0])[:24]:
            inliers = np.abs(sample @ normal + offset) <= fit_tolerance
            surface = sample[inliers]
            centre = surface.mean(axis=0)
            _, _, axes = np.linalg.svd(surface-centre, full_matrices=False)
            normal = axes[-1]
            offset = -normal @ centre
            inliers = np.abs(sample @ normal + offset) <= fit_tolerance
            surface = sample[inliers]
            projected = (surface-centre) @ axes[:2].T
            low, high = np.quantile(projected, [.01, .99], axis=0)
            extent = high-low
            if np.any(extent < minimum_extent):
                continue
            inside = np.all((projected >= low) & (projected <= high), axis=1)
            cells = np.floor((projected[inside]-low)/cell_size).astype(np.int64)
            grid_shape = np.maximum(1, np.ceil(extent/cell_size).astype(np.int64))
            cells = np.minimum(cells, grid_shape-1)
            occupancy = len(np.unique(cells, axis=0)) / float(np.prod(grid_shape))
            if occupancy < .55:
                continue
            removed = remaining[np.abs(points[remaining] @ normal + offset) <= removal_tolerance]
            if len(removed) < minimum_points:
                continue
            accepted = removed
            kind = 'horizontal_surface' if abs(normal[2]) > .9 else ('vertical_surface' if abs(normal[2]) < .25 else 'sloped_surface')
            planes.append({'kind': kind, 'normal_world': normal.tolist(), 'offset_m': float(offset),
                           'fit_support': int(inliers.sum()), 'coverage': float(occupancy),
                           'extent_m': extent.tolist(), 'removed_point_indices': point_ids[removed].tolist()})
            break
        if accepted is None:
            break
        remaining = np.setdiff1d(remaining, accepted)
    details = {'algorithm': 'broad-plane-occupancy-v1', 'planes': planes,
               'removed_points': len(points)-len(remaining), 'remaining_points': len(remaining),
               'parameters': {'fit_tolerance_m': fit_tolerance, 'removal_tolerance_m': removal_tolerance,
                              'cell_size_m': cell_size, 'minimum_extent_m': minimum_extent,
                              'minimum_coverage': .55, 'max_planes': 4, 'sample_limit': 6000, 'trials': 160},
               'limitations': 'Geometric surfaces only; sparse/curved backgrounds can remain. Points within the removal tolerance of a supporting plane may be lost.'}
    return points[remaining], point_ids[remaining], details
