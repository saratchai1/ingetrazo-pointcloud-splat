import numpy as np
import pytest
from pointcloud_splat.grid_measurement import measure_grid


def bar(a,b):
    return {'start':a,'end':b}


def rectangle():
    return ({'V0':bar([0,-.01,0],[0,.21,0]),'V1':bar([.15,-.01,0],[.15,.21,0])},
            {'H0':bar([-.01,0,0],[.16,0,0]),'H1':bar([-.01,.20,0],[.16,.20,0])})


def test_known_rectangle_midbay_spacing():
    c,r = rectangle(); grid = measure_grid(c,r,[0,0,1]);cell=grid['cells'][0]
    assert cell['scan_cell_id'] == 'H0:H1/V0:V1' and cell['status']=='measured'
    assert cell['horizontal_m'] == pytest.approx(.15)
    assert cell['vertical_m'] == pytest.approx(.20)
    assert all(p['within_both_tracks'] for p in grid['corners'])
    assert not grid['reference_correspondence_verified']


def test_midbay_averages_opposite_edges_for_nonparallel_bars():
    c,r = rectangle();c['V1']=bar([.098,-.01,0],[.142,.21,0])
    cell=measure_grid(c,r,[0,0,1])['cells'][0]
    assert cell['horizontal_m'] == pytest.approx(.12)
    assert cell['vertical_m'] == pytest.approx((.20+np.hypot(.04,.20))/2)


def test_missing_corner_never_extrapolates_to_reference_grid():
    c,r=rectangle();c['V1']['end']=[.15,.1,0]
    cell=measure_grid(c,r,[0,0,1])['cells'][0]
    assert cell['status']=='unavailable_outside_track_support'
    assert cell['horizontal_m'] is None and cell['vertical_m'] is None


def test_rotated_translated_grid_retains_metric_lengths():
    c,r=rectangle()
    # Orthogonal cyclic axis permutation, with million-scale translation.
    rotation=np.array([[0,0,1],[1,0,0],[0,1,0]])
    for b in list(c.values())+list(r.values()):
        for key in ['start','end']: b[key]=(rotation@b[key]+[1e6,2e6,3e6]).tolist()
    cell=measure_grid(c,r,rotation@np.array([0,0,1]))['cells'][0]
    assert cell['horizontal_m']==pytest.approx(.15,abs=1e-9)
    assert cell['vertical_m']==pytest.approx(.2,abs=1e-9)


def test_parallel_or_degenerate_grid_rejected():
    c,r=rectangle();r['H0']=bar([0,-.01,0],[0,.21,0])
    with pytest.raises(ValueError,match='intersect'): measure_grid(c,r,[0,0,1])
    with pytest.raises(ValueError,match='collapses'):
        measure_grid({'V':bar([0,0,0],[0,0,1])},{},[0,0,1])
