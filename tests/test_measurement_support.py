from copy import deepcopy
import numpy as np
import pytest
from pointcloud_splat.measurement_support import fixed_support_spacing, match_tracks
from pointcloud_splat.rebar import inspect
from test_bar_tracks import dataset, cylinder


def cloud(shift=0.):
    rng=np.random.default_rng(152)
    steel=np.concatenate([cylinder(np.linspace(0,1.5,2000),y) for y in [0,.15,.3+shift]])
    steel+=rng.normal(0,.003,steel.shape)
    # Clutter enters a wide detection envelope, outside the metrology layer.
    clutter=np.column_stack([np.linspace(0,1.5,1500),np.full(1500,.336),np.full(1500,.040)])
    clutter+=rng.normal(0,.001,clutter.shape)
    return dataset(np.concatenate([steel,clutter])),len(steel)


def analyze(ds,noise):
    basis=ds.apply_transform(np.vstack([np.zeros(3),np.eye(3)]))
    p=ds.apply_transform(ds.coords)
    return inspect(ds,p.min(0)-.001,p.max(0)+.001,basis[1]-basis[0],
                   layer_normal=basis[3]-basis[0],scan_noise_m=noise)


@pytest.mark.parametrize('rotated',[False,True])
def test_scan_measurement_stays_fixed_while_detection_admits_more_clutter(rotated):
    ds,steel=cloud()
    if rotated:
        ds.rotation_x_deg=23;ds.rotation_y_deg=13;ds.rotation_z_deg=42
        ds.offset=np.array([2.,1.,3.])
    reports=[analyze(ds,n) for n in [.015,.0175,.02,.0225,.025]]
    assert all(len(r['bars'])==3 for r in reports)
    fits=[r['profile_spacing'] for r in reports]
    assert all(all(p['status']=='measured' for p in f['pairs']) for f in fits)
    values=np.array([[p['median_m'] for p in f['pairs']] for f in fits])
    assert np.max(np.ptp(values,axis=0))<1e-12
    assert values[0]==pytest.approx([.15,.15],abs=.002)
    assert reports[-1]['layer_filter']['retained_points']>reports[0]['layer_filter']['retained_points']
    for f in fits:
        info=f['measurement_support']
        assert info['layer_half_width_m']==.032 and info['support_radius_m']==.048
        assert all(k<steel for t in info['measurement_tracks'] for k in t['evidence']['point_indices'])
        assert all(m['measurement_track'] is not None for m in info['matches'])


def test_fixed_measurement_responds_to_actual_changed_scan_geometry():
    a=analyze(cloud()[0],.02)['profile_spacing']
    b=analyze(cloud(.01)[0],.02)['profile_spacing']
    assert a['pairs'][1]['median_m']==pytest.approx(.15,abs=.002)
    assert b['pairs'][1]['median_m']==pytest.approx(.16,abs=.002)
    assert b['pairs'][1]['median_m']-a['pairs'][1]['median_m']>.008


def bar(y,lo=0,hi=1):
    return {'start':[lo,y,0],'end':[hi,y,0]}


@pytest.mark.parametrize('candidates,tracks',[
    ([bar(0),bar(.01)],[bar(0)]),
    ([bar(0)],[bar(-.01),bar(.01)]),
    ([bar(0)],[bar(0,2,3)]),
    ([bar(0)],[bar(.1)]),
])
def test_ambiguous_wrong_or_nonoverlapping_tracks_are_not_forced(candidates,tracks):
    matches=match_tracks(candidates,tracks,[1,0,0],.016,.25)
    assert all(m['measurement_track'] is None for m in matches)


def test_measurement_pair_references_native_bar_order_not_track_fit_order():
    ds,_=cloud();r=analyze(ds,.02);bars=deepcopy(r['bars'])[::-1]
    # Same scan, deliberately reversed native indexing.
    profile=fixed_support_spacing(ds.coords,np.arange(len(ds.coords)),bars,[1,0,0],[0,0,1],.016,
                                  r['layer_filter']['selected_depth_m'])
    for pair in profile['pairs']:
        assert pair['status']=='measured'
        for native,fit in zip(pair['bars'],pair['measurement_tracks']):
            assert profile['measurement_support']['matches'][native]['measurement_track']==fit
        for section in pair['sections']:
            centres=np.array(section['centres_transverse_m'])
            assert centres[0,1]>centres[1,1]
            assert np.linalg.norm(centres[1]-centres[0])==pytest.approx(section['spacing_m'])


def test_missing_measurement_support_never_falls_back_to_native_spacing():
    candidates=[bar(0),bar(.15)]
    result=fixed_support_spacing(np.empty((0,3)),np.array([],dtype=int),candidates,
                                [1,0,0],[0,0,1],.016,None)
    assert len(result['pairs'])==1
    assert result['pairs'][0]['median_m'] is None
    assert result['pairs'][0]['status']=='unavailable_scan_support'


def test_native_reordering_keeps_per_bar_drift_with_its_bar():
    rng=np.random.default_rng(91);x=np.linspace(0,1.5,2500)
    # Middle bar tilts 1 degree; the outer bars stay on the guided axis.
    steel=np.concatenate([cylinder(x,y)+np.outer(x*s,[0,1,0]) for y,s in [(0,0),(.15,np.tan(np.radians(1))),(.3,0)]])
    ds=dataset(steel+rng.normal(0,.003,steel.shape));r=analyze(ds,.02)
    bars=deepcopy(r['bars'])[::-1]
    profile=fixed_support_spacing(ds.coords,np.arange(len(ds.coords)),bars,[1,0,0],[0,0,1],.016,
                                  r['layer_filter']['selected_depth_m'])
    middle=int(np.argmin([abs(np.mean([b['start'][1],b['end'][1]])-.15-.75*np.tan(np.radians(1))) for b in bars]))
    for pair in profile['pairs']:
        assert pair['status']=='measured'
        for native,drift in zip(pair['bars'],pair['axial_trend']['lateral_drift_deg']):
            assert drift==pytest.approx(1. if native==middle else 0.,abs=.3)
