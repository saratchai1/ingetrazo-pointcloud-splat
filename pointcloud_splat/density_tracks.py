# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional guided density proposals for scans blurred beyond a bar diameter.

No expected bar count or spacing is accepted. Noise allowance is supplied in
metres and recorded, not estimated by fitting the reference measurements.
"""
import numpy as np


def density_proposals(points, direction, normal, diameter, noise_m, min_support):
    side = np.cross(normal, direction); side /= np.linalg.norm(side)
    radius = .8*diameter+2*noise_m
    sigma = np.hypot(noise_m, diameter/4)
    cell = diameter/4
    info = {'enabled': True, 'noise_allowance_m': noise_m, 'support_radius_m': radius,
            'bin_m': cell, 'smoothing_sigma_m': float(sigma), 'peaks': []}
    if not len(points):
        return [], info
    values = points @ side
    start = float(values.min())-cell
    count = int(np.ceil((values.max()-start)/cell))+1
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
