# SPDX-License-Identifier: GPL-3.0-or-later
"""LAS/LAZ import: float64 local metres, explicit source units, no global float32."""
from pathlib import Path
import numpy as np
from ..data_models import PointCloudDataset


def read_las(path, *, source_units=None, origin=None, roi=None):
    """ROI is inclusive in SOURCE coordinates, before localization.

    Units must be confirmed explicitly; LAS scale factors alone do not define units.
    LAZ requires laspy's lazrs backend. Never falls back to decoding compressed bytes.
    """
    if source_units not in ('m', 'mm', 'ft'):
        raise ValueError('Confirm source_units: m, mm, or ft before import')
    factor = {'m': 1., 'mm': .001, 'ft': .3048}[source_units]
    try:
        import laspy
    except ImportError as exc:
        raise ValueError('LAS/LAZ import requires laspy and lazrs') from exc
    path = Path(path)
    chunks, colors, intensities, indices = [], [], [], []
    if roi is not None:
        lo, hi = np.asarray(roi, dtype=np.float64)
        if lo.shape != (3,) or hi.shape != (3,) or not np.isfinite([lo, hi]).all() or np.any(lo > hi):
            raise ValueError('Invalid source ROI')
    with laspy.open(path) as reader:
        scales = np.asarray(reader.header.scales)
        if not np.isfinite(scales).all() or np.any(scales <= 0):
            raise ValueError('Invalid LAS scales')
        source_origin = np.asarray(reader.header.offsets if origin is None else origin, dtype=np.float64)
        if source_origin.shape != (3,) or not np.isfinite(source_origin).all():
            raise ValueError('Invalid local origin')
        total = 0
        for record in reader.chunk_iterator(250000):
            total += len(record)
            xyz = np.column_stack((record.x, record.y, record.z)).astype(np.float64)
            if not np.isfinite(xyz).all():
                raise ValueError('Non-finite LAS coordinates')
            mask = np.ones(len(xyz), dtype=bool) if roi is None else np.all((xyz >= lo) & (xyz <= hi), axis=1)
            chunks.append((xyz[mask] - source_origin) * factor)
            if roi is not None:
                indices.append(np.arange(total-len(record), total, dtype=np.int64)[mask])
            intensities.append(np.asarray(record.intensity)[mask].astype(np.float32))
            if 'red' in record.point_format.dimension_names:
                rgb = np.column_stack((record.red, record.green, record.blue))[mask]
                colors.append(rgb)
        if total != reader.header.point_count:
            raise ValueError('Truncated LAS point records')
        metadata = {'schema': 1, 'source_units': source_units, 'unit_to_m': factor,
                    'source_origin': source_origin.tolist(), 'las_scales': scales.tolist(),
                    'crs_wkt': None, 'source_roi': None if roi is None else np.asarray(roi).tolist()}
        crs = reader.header.parse_crs()
        if crs is not None:
            metadata['crs_wkt'] = crs.to_wkt()
    coords = np.concatenate(chunks) if chunks else np.empty((0, 3))
    if not len(coords):
        raise ValueError('No points in LAS/ROI')
    # Rebase again near retained points even if the LAS header offset is zero.
    shift = coords[0].copy() if origin is None else np.zeros(3)
    coords -= shift
    metadata['source_origin'] = (source_origin + shift / factor).tolist()
    rgba = np.full((len(coords), 4), 255, dtype=np.uint8)
    if colors:
        rgb = np.concatenate(colors)
        rgba[:, :3] = (rgb >> 8 if rgb.max() > 255 else rgb).astype(np.uint8)
    else:
        rgba[:, :3] = 200
    ds = PointCloudDataset(path.stem, str(path), coords, rgba)
    ds.coordinate_frame = metadata
    ds.intensities = np.concatenate(intensities)
    if indices:
        ds.source_point_indices = np.concatenate(indices)
    return ds
