import numpy as np
import pytest
from pointcloud_splat.rebar import inspect
from pointcloud_splat.bar_tracks import axial_cell_centre
from test_bar_tracks import dataset, cylinder


@pytest.mark.parametrize('rotated', [False,True])
@pytest.mark.parametrize('noise', [.015,.02,.025])
def test_blurred_parallel_bars_have_known_spacing(rotated, noise):
    rng=np.random.default_rng(63)
    points=np.concatenate([cylinder(np.linspace(0,1.5,1800),y) for y in [0,.15,.3]])
    points+=rng.normal(0,.008,points.shape)
    ds=dataset(points)
    if rotated:
        ds.rotation_x_deg=23;ds.rotation_y_deg=13;ds.rotation_z_deg=42
        ds.offset=np.array([2.,1.,3.])
    basis=ds.apply_transform(np.vstack([np.zeros(3),np.eye(3)]))
    p=ds.apply_transform(ds.coords)
    report=inspect(ds,p.min(0)-.01,p.max(0)+.01,basis[1]-basis[0],
                   layer_normal=basis[3]-basis[0],scan_noise_m=noise)
    assert len(report['bars'])==3
    assert sorted(s['centreline_m'] for s in report['spacing'])==pytest.approx([.15,.15,.3],abs=.002)
    assert report['density_proposals']['enabled']
    pairs=report['profile_spacing']['pairs']
    assert len(pairs)==2 and all(p['status']=='measured' for p in pairs)
    assert [p['median_m'] for p in pairs]==pytest.approx([.15,.15],abs=.002)
    assert all(p['scale_votes']>=3 for p in report['density_proposals']['peaks'])
    assert all(b['evidence']['centre_estimator']=='axial_bin_median' for b in report['bars'])
    assert all(not b['accepted'] for b in report['bars'])


@pytest.mark.parametrize('noise', [.015,.02,.025])
def test_perpendicular_crossings_do_not_become_blurred_parallel_bars(noise):
    x=np.linspace(0,.6,500)
    points=np.concatenate([np.column_stack([np.full(500,v),x,np.zeros(500)]) for v in np.arange(5)*.15])
    report=inspect(dataset(points),[-1]*3,[1]*3,[1,0,0],layer_normal=[0,0,1],scan_noise_m=noise)
    assert not report['bars']


@pytest.mark.parametrize('noise', [float('nan'),-.01,.051])
def test_invalid_noise_allowance_rejected(noise):
    ds=dataset(cylinder(np.linspace(0,1,300)))
    with pytest.raises(ValueError,match='noise allowance'):
        inspect(ds,[-1]*3,[2]*3,[1,0,0],scan_noise_m=noise)


def test_blur_mode_requires_explicit_layer_normal():
    with pytest.raises(ValueError,match='layer normal'):
        inspect(dataset(cylinder(np.linspace(0,1,300))),[-1]*3,[2]*3,[1,0,0],scan_noise_m=.02)


def test_equal_axial_cell_influence_resists_local_dense_anchor():
    bar=np.column_stack([np.linspace(0,1,1000),np.zeros(1000),np.zeros(1000)])
    anchor=np.tile([.5,.03,0],(4000,1));points=np.concatenate([bar,anchor])
    assert points.mean(0)[1]>.02
    centre=axial_cell_centre(points,np.array([1.,0,0]),.016,.0528)
    assert abs(centre[1])<1e-9


@pytest.mark.parametrize('noise', [.003,.015,.025])
def test_sparse_edge_bars_keep_gaussian_tails_and_all_three_peaks(noise):
    from pointcloud_splat.density_tracks import density_proposals
    points=np.concatenate([cylinder(np.linspace(0,2,300),y) for y in (0.,.15,.3)])
    clusters,info=density_proposals(points,np.array([1.,0,0]),np.array([0.,0,1]),.016,noise,30)
    assert len(clusters)==3
    assert all(p['scale_votes']>=3 for p in info['peaks'])
