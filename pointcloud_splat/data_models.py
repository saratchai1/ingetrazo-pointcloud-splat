# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""Data models for Point Cloud and 3D Gaussian Splatting datasets."""
from __future__ import annotations

import dataclasses
import math
from typing import Any, Optional, Tuple
import numpy as np


@dataclasses.dataclass
class PointCloudDataset:
    """Represents a point cloud dataset in IngeTrazo."""
    name: str
    filepath: Optional[str]
    coords: np.ndarray          # shape (N, 3), local metres; LAS analysis retains float64
    colors: np.ndarray          # shape (N, 4), uint8 RGBA
    normals: Optional[np.ndarray] = None      # shape (N, 3), float32 or None
    intensities: Optional[np.ndarray] = None  # shape (N,), float32 or None
    
    coordinate_frame: Optional[dict] = None  # source origin/units, JSON-safe

    source_point_indices: Optional[np.ndarray] = None  # populated for import ROI

    # Display settings
    visible: bool = True
    point_size: int = 2                       # 1 to 12 px
    color_mode: str = "rgb"                   # "rgb", "elevation", "intensity", "normals", "solid"
    solid_color: Tuple[int, int, int] = (0, 200, 255)
    colormap: str = "turbo"                   # "turbo", "viridis", "jet", "terrain"
    elevation_range: Optional[Tuple[float, float]] = None  # (min_z, max_z)
    opacity: float = 1.0                      # 0.0 to 1.0
    
    # Transform in world space
    offset: np.ndarray = dataclasses.field(default_factory=lambda: np.zeros(3, dtype=np.float32))
    rotation_x_deg: float = 0.0
    rotation_y_deg: float = 0.0
    rotation_z_deg: float = 0.0
    scale: float = 1.0
    pivot: Optional[np.ndarray] = None
    proxy_group: Optional[Any] = None

    # Bounds cache: (min_x, min_y, min_z), (max_x, max_y, max_z)
    _raw_bounds: Optional[Tuple[np.ndarray, np.ndarray]] = None

    def __post_init__(self):
        if self.coords is not None and len(self.coords) > 0:
            min_pt = np.min(self.coords, axis=0)
            max_pt = np.max(self.coords, axis=0)
            self._raw_bounds = (min_pt, max_pt)
            if self.pivot is None:
                self.pivot = ((min_pt + max_pt) * 0.5).astype(np.float32)
            if self.elevation_range is None:
                self.elevation_range = (float(min_pt[2]), float(max_pt[2]))
        else:
            if self.pivot is None:
                self.pivot = np.zeros(3, dtype=np.float32)

    @property
    def point_count(self) -> int:
        return len(self.coords) if self.coords is not None else 0

    @property
    def count(self) -> int:
        return len(self.coords) if self.coords is not None else 0

    @property
    def is_gaussian_splat(self) -> bool:
        return False

    @property
    def bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Transformed world bounds (min_xyz, max_xyz)."""
        if self._raw_bounds is None:
            return np.zeros(3, dtype=np.float32), np.zeros(3, dtype=np.float32)
        min_p, max_p = self._raw_bounds
        # Simple transform of 8 corner points
        corners = np.array([
            [min_p[0], min_p[1], min_p[2]],
            [max_p[0], min_p[1], min_p[2]],
            [min_p[0], max_p[1], min_p[2]],
            [max_p[0], max_p[1], min_p[2]],
            [min_p[0], min_p[1], max_p[2]],
            [max_p[0], min_p[1], max_p[2]],
            [min_p[0], max_p[1], max_p[2]],
            [max_p[0], max_p[1], max_p[2]],
        ], dtype=np.float32)
        transformed = self.apply_transform(corners)
        return np.min(transformed, axis=0), np.max(transformed, axis=0)

    def apply_transform(self, points: np.ndarray, viewport=None) -> np.ndarray:
        """Applies scale, 3D Euler rotations (Z, Y, X) around pivot, and offset to points."""
        pts = np.asarray(points, dtype=np.float64)
        if self.proxy_group is not None:
            from .scene_proxy import proxy_affine
            matrix, translation = proxy_affine(self, viewport)
            return pts @ matrix.T + translation
        return self.manual_transform(pts)

    def manual_transform(self, points):
        pts = np.asarray(points, dtype=np.float64)
        piv = np.asarray(self.pivot, dtype=np.float64)
        if not np.isfinite(self.scale) or self.scale <= 0:
            raise ValueError("Scale must be finite and positive")
        rx, ry, rz = np.radians([self.rotation_x_deg, self.rotation_y_deg, self.rotation_z_deg])
        cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
        matrix = np.array([[cz*cy, cz*sy*sx-sz*cx, cz*sy*cx+sz*sx],
                           [sz*cy, sz*sy*sx+cz*cx, sz*sy*cx-cz*sx],
                           [-sy, cy*sx, cy*cx]])
        return (pts-piv) @ matrix.T * self.scale + piv + self.offset

    def source_coordinates(self):
        if self.coordinate_frame is None:
            raise ValueError("Dataset has no verified coordinate frame")
        f = self.coordinate_frame
        return self.coords / f['unit_to_m'] + np.asarray(f['source_origin'])

    def world_roi(self, minimum, maximum, viewport=None):
        lo, hi = np.asarray([minimum, maximum], dtype=np.float64)
        if lo.shape != (3,) or not np.isfinite([lo, hi]).all() or np.any(lo > hi):
            raise ValueError("Invalid world ROI")
        points = self.apply_transform(self.coords, viewport)
        indices = np.flatnonzero(np.all((points >= lo) & (points <= hi), axis=1))
        return points[indices], indices


@dataclasses.dataclass
class GaussianSplatDataset:
    """Represents a 3D Gaussian Splatting dataset."""
    name: str
    filepath: Optional[str]
    coords: np.ndarray          # shape (N, 3), float32 (centres in metres)
    scales: np.ndarray          # shape (N, 3), float32 (semi-axes radii)
    rotations: np.ndarray       # shape (N, 4), float32 (quaternions [w, x, y, z] or [x, y, z, w])
    opacities: np.ndarray       # shape (N,), float32 (0.0 to 1.0)
    colors: np.ndarray          # shape (N, 4), uint8 RGBA

    # Display settings
    visible: bool = True
    splat_scale: float = 1.0    # multiplier for splat footprint
    opacity: float = 1.0        # overall opacity multiplier
    opacity_threshold: float = 0.02
    max_splats: int = 3000000    # budget for real-time display (up to 3M splats)
    point_size: int = 3
    
    # Transform in world space
    offset: np.ndarray = dataclasses.field(default_factory=lambda: np.zeros(3, dtype=np.float32))
    rotation_x_deg: float = 0.0
    rotation_y_deg: float = 0.0
    rotation_z_deg: float = 0.0
    scale: float = 1.0
    pivot: Optional[np.ndarray] = None
    proxy_group: Optional[Any] = None

    _raw_bounds: Optional[Tuple[np.ndarray, np.ndarray]] = None

    def __post_init__(self):
        if self.coords is not None and len(self.coords) > 0:
            min_pt = np.min(self.coords, axis=0)
            max_pt = np.max(self.coords, axis=0)
            self._raw_bounds = (min_pt, max_pt)
            if self.pivot is None:
                self.pivot = ((min_pt + max_pt) * 0.5).astype(np.float32)
        else:
            if self.pivot is None:
                self.pivot = np.zeros(3, dtype=np.float32)

    @property
    def splat_count(self) -> int:
        return len(self.coords) if self.coords is not None else 0

    @property
    def point_count(self) -> int:
        return len(self.coords) if self.coords is not None else 0

    @property
    def count(self) -> int:
        return len(self.coords) if self.coords is not None else 0

    @property
    def is_gaussian_splat(self) -> bool:
        return True

    @property
    def bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Transformed world bounds (min_xyz, max_xyz)."""
        if self._raw_bounds is None:
            return np.zeros(3, dtype=np.float32), np.zeros(3, dtype=np.float32)
        min_p, max_p = self._raw_bounds
        corners = np.array([
            [min_p[0], min_p[1], min_p[2]],
            [max_p[0], min_p[1], min_p[2]],
            [min_p[0], max_p[1], min_p[2]],
            [max_p[0], max_p[1], min_p[2]],
            [min_p[0], min_p[1], max_p[2]],
            [max_p[0], min_p[1], max_p[2]],
            [min_p[0], max_p[1], max_p[2]],
            [max_p[0], max_p[1], max_p[2]],
        ], dtype=np.float32)
        transformed = self.apply_transform(corners)
        return np.min(transformed, axis=0), np.max(transformed, axis=0)

    def apply_transform(self, points: np.ndarray, viewport=None) -> np.ndarray:
        """Applies scale, 3D Euler rotations (Z, Y, X) around pivot, and offset to points."""
        pts = points
        piv = self.pivot if self.pivot is not None else np.zeros(3, dtype=np.float32)
        if np.any(piv != 0):
            pts = pts - piv
        if self.scale != 1.0:
            pts = pts * self.scale

        if self.proxy_group is not None:
            try:
                from .scene_proxy import compute_dataset_transform
                R, T = compute_dataset_transform(self, viewport)
                self.offset = T
                self.rotation_z_deg = float(math.degrees(math.atan2(R[1, 0], R[0, 0])))
                self.rotation_x_deg = float(math.degrees(math.atan2(R[2, 1], R[2, 2])))
                self.rotation_y_deg = float(math.degrees(math.atan2(-R[2, 0], math.hypot(R[2, 1], R[2, 2]))))
                pts = pts @ R.T
                if np.any(piv != 0):
                    pts = pts + piv
                if np.any(T != 0):
                    pts = pts + T
                return pts
            except Exception:
                pass

        rx = math.radians(self.rotation_x_deg)
        ry = math.radians(self.rotation_y_deg)
        rz = math.radians(self.rotation_z_deg)
        if abs(rx) > 1e-4 or abs(ry) > 1e-4 or abs(rz) > 1e-4:
            cx, sx = math.cos(rx), math.sin(rx)
            cy, sy = math.cos(ry), math.sin(ry)
            cz, sz = math.cos(rz), math.sin(rz)
            R = np.array([
                [cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
                [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
                [-sy, cy * sx, cy * cx]
            ], dtype=np.float32)
            pts = pts @ R.T
        if np.any(piv != 0):
            pts = pts + piv
        if np.any(self.offset != 0):
            pts = pts + self.offset
        return pts
