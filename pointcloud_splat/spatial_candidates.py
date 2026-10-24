# SPDX-License-Identifier: GPL-3.0-or-later
"""Conservative transverse grid lookup; final membership uses original distances.

This changes search cost, not the detector's geometric thresholds or seed order.
"""
from itertools import product
import numpy as np


class TransverseIndex:
    def __init__(self, transverse, direction, cell_size):
        u = np.cross(direction, np.eye(3)[np.argmin(np.abs(direction))])
        u /= np.linalg.norm(u)
        self.basis = np.column_stack([u, np.cross(direction, u)])
        self.cell_size = cell_size
        keys = np.floor(transverse @ self.basis / cell_size).astype(np.int64)
        cells = {}
        for i, key in enumerate(keys):
            cells.setdefault(tuple(key), []).append(i)
        self.cells = {key: np.asarray(ids, dtype=np.int64) for key, ids in cells.items()}

    def nearby(self, centre, radius, active):
        key = np.floor(centre @ self.basis / self.cell_size).astype(np.int64)
        # Extra shell ensures numerical bin-boundary rounding cannot discard a
        # true radius neighbour. The caller performs the exact 3D distance test.
        reach = int(np.ceil(radius/self.cell_size))+1
        groups = [self.cells[(key[0]+dx, key[1]+dy)]
                  for dx, dy in product(range(-reach, reach+1), repeat=2)
                  if (key[0]+dx, key[1]+dy) in self.cells]
        if not groups:
            return np.empty(0, dtype=np.int64)
        ids = np.sort(np.concatenate(groups))
        return ids[active[ids]]
