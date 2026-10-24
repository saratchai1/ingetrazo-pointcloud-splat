# SPDX-License-Identifier: GPL-3.0-or-later
"""Benchmark summaries must not silently pair false/missing bars to references."""
import numpy as np


def compare_reference(detected_count, expected_count, measured_spacing_m,
                      reference_spacing_m, *, correspondence_verified=False):
    reference = np.asarray(reference_spacing_m, dtype=float)
    if expected_count < 1 or detected_count < 0 or reference.ndim != 1 or not np.isfinite(reference).all() or np.any(reference <= 0):
        raise ValueError('Invalid independent reference')
    result = {'expected_count': expected_count, 'detected_count': detected_count,
              'count_error': detected_count-expected_count, 'count_matches': detected_count==expected_count,
              'reference_spacing_count': len(reference), 'reference_spacing_m': reference.tolist(),
              'spacing_mae_m': None, 'spacing_max_abs_error_m': None, 'per_spacing_error_m': None}
    if detected_count != expected_count:
        result['spacing_status'] = 'unavailable_count_mismatch'
        return result
    if not correspondence_verified:
        result['spacing_status'] = 'unavailable_unverified_correspondence'
        return result
    measured = np.asarray(measured_spacing_m, dtype=float)
    if measured.shape != reference.shape or not np.isfinite(measured).all() or np.any(measured <= 0):
        raise ValueError('Verified measurements must cover every reference spacing in the same order')
    errors = measured-reference
    result.update(spacing_status='evaluated', per_spacing_error_m=errors.tolist(),
                  spacing_mae_m=float(np.mean(np.abs(errors))),
                  spacing_max_abs_error_m=float(np.max(np.abs(errors))))
    return result
