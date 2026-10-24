import numpy as np
import pytest
from pointcloud_splat.spatial_candidates import TransverseIndex


@pytest.mark.parametrize('direction', [[1.,0,0],[.4,.5,.8]])
def test_index_matches_exhaustive_neighbours_with_negative_coordinates(direction):
    direction=np.array(direction);direction/=np.linalg.norm(direction)
    rng=np.random.default_rng(182);p=rng.uniform(-2,2,(10000,3));t=p-np.outer(p@direction,direction)
    active=rng.random(len(p))>.3;index=TransverseIndex(t,direction,.0128)
    for centre in t[::137]:
        nearby=index.nearby(centre,.0256,active)
        found=nearby[np.linalg.norm(t[nearby]-centre,axis=1)<=.0256]
        expected=np.flatnonzero(active&(np.linalg.norm(t-centre,axis=1)<=.0256))
        assert np.array_equal(found,expected)


def test_exact_cell_boundaries_empty_and_consumed_points():
    t=np.array([[0.,0,0],[0,.016,0],[0,-.016,0],[0,0,.016],[0,0,-.016]])
    index=TransverseIndex(t,np.array([1.,0,0]),.008)
    for active in [np.ones(5,dtype=bool),np.zeros(5,dtype=bool)]:
        nearby=index.nearby(np.zeros(3),.016,active)
        found=nearby[np.linalg.norm(t[nearby],axis=1)<=.016]
        assert found.tolist()==np.flatnonzero(active).tolist()
    empty=TransverseIndex(np.empty((0,3)),np.array([1.,0,0]),.008)
    assert not len(empty.nearby(np.zeros(3),.016,np.zeros(0,dtype=bool)))
