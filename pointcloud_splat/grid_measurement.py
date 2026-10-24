# SPDX-License-Identifier: GPL-3.0-or-later
"""Candidate mid-bay measurements from named straight tracks, without extension.

Projection and global straight-track fitting can bias curved/partial steel.
Scan-local cell IDs do not establish correspondence with a reference diagram.
"""
import numpy as np


def measure_grid(columns, rows, normal):
    normal = np.asarray(normal, dtype=float)
    if normal.shape != (3,) or not np.isfinite(normal).all() or np.linalg.norm(normal) < 1e-12:
        raise ValueError('Invalid grid normal')
    normal = normal/np.linalg.norm(normal)
    u = np.cross(normal, np.eye(3)[np.argmin(abs(normal))]); u /= np.linalg.norm(u)
    basis = np.array([u, np.cross(normal, u)])
    def project(mapping):
        result = {}
        for key, bar in mapping.items():
            ends = np.asarray([bar['start'], bar['end']], dtype=float)
            if ends.shape != (2, 3) or not np.isfinite(ends).all():
                raise ValueError('Invalid grid endpoints')
            result[key] = ends @ basis.T
            if np.linalg.norm(result[key][1]-result[key][0]) < 1e-9:
                raise ValueError('Grid track collapses under projection')
        return result
    cc, rr = project(columns), project(rows)
    corners = {}
    for ci, c in cc.items():
        for ri, r in rr.items():
            a, b = c[1]-c[0], r[1]-r[0]
            matrix = np.column_stack([a, -b])
            if abs(np.linalg.det(matrix)) < 1e-8*np.linalg.norm(a)*np.linalg.norm(b):
                raise ValueError('Grid families must intersect')
            t, s = np.linalg.solve(matrix, r[0]-c[0])
            # A geometric crossing outside measured endpoint support is not an
            # observed corner; never extend tracks to complete a reference grid.
            inside = bool(0 <= t <= 1 and 0 <= s <= 1)
            corners[(ci, ri)] = {'xy': c[0]+t*a, 'inside': inside}
    cells = []
    col_ids, row_ids = list(cc), list(rr)
    for r0, r1 in zip(row_ids, row_ids[1:]):
        for c0, c1 in zip(col_ids, col_ids[1:]):
            keys = [(c0, r0), (c1, r0), (c0, r1), (c1, r1)]
            valid = all(corners[k]['inside'] for k in keys)
            p00, p10, p01, p11 = [corners[k]['xy'] for k in keys]
            cells.append({'scan_cell_id': f'{r0}:{r1}/{c0}:{c1}', 'columns': [c0, c1], 'rows': [r0, r1],
                          'status': 'measured' if valid else 'unavailable_outside_track_support',
                          'horizontal_m': float((np.linalg.norm(p10-p00)+np.linalg.norm(p11-p01))/2) if valid else None,
                          'vertical_m': float((np.linalg.norm(p01-p00)+np.linalg.norm(p11-p10))/2) if valid else None})
    return {'basis': 'projected_straight_tracks; averaged opposite edges; no extrapolation',
            'plane_basis_2x3': basis.tolist(),
            'corners': [{'column': ci, 'row': ri, 'projected_xy_m': c['xy'].tolist(),
                         'within_both_tracks': c['inside']} for (ci, ri), c in corners.items()],
            'columns': col_ids, 'rows': row_ids, 'cells': cells,
            'reference_correspondence_verified': False}
