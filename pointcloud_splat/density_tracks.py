# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional guided density proposals for scans blurred beyond a bar diameter.

No expected bar count or spacing is accepted. Noise allowance is supplied in
metres and recorded, not estimated by fitting the reference measurements.
"""
import numpy as np


def _single_scale_proposals(points, direction, normal, diameter, noise_m, min_support):
    side = np.cross(normal, direction); side /= np.linalg.norm(side)
    radius = .8*diameter+2*noise_m
    sigma = np.hypot(noise_m, diameter/4)
    cell = diameter/4
    info = {'enabled': True, 'noise_allowance_m': noise_m, 'support_radius_m': radius,
            'bin_m': cell, 'smoothing_sigma_m': float(sigma), 'peaks': []}
    if not len(points):
        return [], info
    values = points @ side
    # Include the Gaussian tails: an edge bar must not lose prominence
    # merely because the histogram stops at the first/last observed point.
    start = float(values.min())-3*sigma-cell
    count = int(np.ceil((values.max()+3*sigma-start)/cell))+1
    if count > 100000:
        raise ValueError('Narrow ROI before density analysis')
    hist, edges = np.histogram(values, bins=count, range=(start,start+count*cell))
    extent = int(np.ceil(3*sigma/cell))
    kernel = np.exp(-.5*(np.arange(-extent,extent+1)*cell/sigma)**2); kernel /= kernel.sum()
    smooth = np.convolve(np.pad(hist,(extent,extent)),kernel,mode='valid')
    threshold = max(min_support/10, 5*np.sqrt(np.median(smooth)))
    info['minimum_prominence'] = float(threshold)
    candidates = np.flatnonzero((smooth>np.r_[0,smooth[:-1]]) & (smooth>=np.r_[smooth[1:],0]))
    ranked = []
    for i in candidates:
        left = right = smooth[i]
        for j in range(i-1,-1,-1):
            if smooth[j]>smooth[i]: break
            left = min(left,smooth[j])
        for j in range(i+1,len(smooth)):
            if smooth[j]>smooth[i]: break
            right = min(right,smooth[j])
        prominence = float(smooth[i]-max(left,right))
        if prominence >= threshold:
            ranked.append((prominence,int(i)))
    centres = (edges[:-1]+edges[1:])/2
    chosen = []
    for prominence,i in sorted(ranked,reverse=True):
        if all(abs(centres[i]-centres[j])>=2*radius for _,j in chosen):
            chosen.append((prominence,i))
    clusters = []
    for prominence,i in sorted(chosen,key=lambda item: centres[item[1]]):
        ids = np.flatnonzero(abs(values-centres[i])<=radius)
        if len(ids)>=min_support:
            clusters.append(ids)
            info['peaks'].append({'transverse_m':float(centres[i]),'prominence':prominence,'support':len(ids)})
    return clusters, info


def density_proposals(points, direction, normal, diameter, noise_m, min_support):
    """Require a peak in three of four diameter-based smoothing scales.

    Proposal identity is independent of the requested support allowance. This
    avoids accepting one-scale clutter or losing an edge bar solely because
    the user widened its support envelope. No count/spacing prior is used.
    """
    scales = [.75, 1., 1.25, 1.5]
    inventories = []
    for scale in scales:
        _, info = _single_scale_proposals(points, direction, normal, diameter,
                                          scale*diameter, min_support)
        inventories.append(info)
    locations = [np.array([p['transverse_m'] for p in info['peaks']]) for info in inventories]
    chosen = []
    for values in locations:
        for value in values:
            matches = [a[np.argmin(abs(a-value))] for a in locations
                       if len(a) and min(abs(a-value)) < 2*diameter]
            if len(matches) < 3:
                continue
            centre = float(np.median(matches))
            if all(abs(centre-p['transverse_m']) > 2*diameter for p in chosen):
                chosen.append({'transverse_m': centre, 'scale_votes': len(matches)})
    side = np.cross(normal, direction); side /= np.linalg.norm(side)
    values = points @ side
    radius = .8*diameter+2*noise_m
    clusters, peaks = [], []
    for peak in sorted(chosen, key=lambda p: p['transverse_m']):
        ids = np.flatnonzero(abs(values-peak['transverse_m']) <= radius)
        if len(ids) >= min_support:
            clusters.append(ids)
            peaks.append({**peak, 'support': len(ids)})
    return clusters, {'enabled': True, 'method': 'diameter_scale_consensus',
                      'noise_allowance_m': noise_m, 'support_radius_m': radius,
                      'minimum_scale_votes': 3, 'matching_distance_m': 2*diameter,
                      'scales_diameter': scales, 'scale_inventories': inventories, 'peaks': peaks}
