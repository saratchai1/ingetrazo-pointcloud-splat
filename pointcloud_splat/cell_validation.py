# SPDX-License-Identifier: GPL-3.0-or-later
"""Score only explicit, independently anchored cell correspondences.

Partial verified cells may be reported as partial coverage, never a whole-grid
pass. An ordering guess or a best-fitting spacing permutation is insufficient.
"""
import numpy as np


def bound_matches(document, expected):
    if any(document.get(k) != expected[k] for k in ('source_sha256', 'reference_sha256', 'measurement_sha256')):
        raise ValueError('Crosswalk must match the exact source, reference and measured grid hashes')
    if not isinstance(document.get('matches'), list):
        raise ValueError('Crosswalk matches must be a list')
    return document['matches']


def compare_cell_pairs(reference, measured, matches):
    rows = []
    used_reference, used_measurement = set(), set()
    for match in matches:
        ref_id, scan_id = match['reference_id'], match['measurement_id']
        if ref_id not in reference or scan_id not in measured:
            raise ValueError('Unknown reference or measurement ID')
        if ref_id in used_reference or scan_id in used_measurement:
            raise ValueError('Correspondences must be one-to-one')
        used_reference.add(ref_id); used_measurement.add(scan_id)
        verified = match.get('verified') is True and bool(match.get('anchor_evidence'))
        value, truth = measured[scan_id], reference[ref_id]
        available = value is not None
        if not np.isfinite(truth) or truth <= 0 or (available and (not np.isfinite(value) or value <= 0)):
            raise ValueError('Spacing values must be finite positive metres')
        error = float(value-truth) if verified and available else None
        rows.append({'reference_id': ref_id, 'measurement_id': scan_id, 'verified': verified,
                     'anchor_evidence': match.get('anchor_evidence'),
                     'status': ('scored' if available else 'unavailable_scan_support') if verified else 'unverified_correspondence',
                     'error_m': error})
    errors = [r['error_m'] for r in rows if r['error_m'] is not None]
    scored = len(errors)
    verified = sum(r['verified'] for r in rows)
    status = ('complete_verified' if scored == len(reference) else 'partial_verified') if scored else (
        'unavailable_scan_support' if verified else 'unavailable_unverified_correspondence')
    return {'reference_cells': len(reference), 'scored_cells': scored,
            'verified_pairs': verified, 'pairs': rows, 'status': status,
            'spacing_mae_m': float(np.mean(np.abs(errors))) if scored else None,
            'spacing_max_abs_error_m': float(np.max(np.abs(errors))) if scored else None}
