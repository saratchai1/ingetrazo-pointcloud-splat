import numpy as np
import pytest
from pointcloud_splat.profile_spacing import paired_profile_spacing
from pointcloud_splat.rebar import spacing


def fixture():
    # Shared lateral drift, unequal visible spans: whole-track means are biased.
    samples=[];bars=[]
    for i,(lo,hi) in enumerate([(0,2),(.8,2)]):
        x=np.linspace(lo,hi,3000)
        p=np.column_stack([x,.04*x+i*.15,np.zeros(len(x))])
        samples.append(p)
        ids=np.arange(len(x))+i*len(x)
        centre=p.mean(0)
        bars.append({'start':[lo,centre[1],0], 'end':[hi,centre[1],0],
                     'evidence':{'point_indices':(ids*7+31).tolist()}})
    points=np.concatenate(samples);ids=np.arange(len(points))*7+31
    return points,ids,bars


@pytest.mark.parametrize('rotated',[False,True])
def test_paired_sections_recover_spacing_with_drift_and_unequal_visibility(rotated):
    points,ids,bars=fixture();d=np.array([1.,0,0]);n=np.array([0.,0,1])
    assert abs(spacing(bars,d)[0]['centreline_m']-.15)>.01
    if rotated:
        # Fixed orthonormal rotation; no benchmark-only SciPy dependency.
        r=np.array([[0.,-1,0],[.6,0,-.8],[.8,0,.6]])
        offset=np.array([8.,-3.,5.]);points=points@r.T+offset;d=r@d;n=r@n
        for bar in bars:
            for key in ['start','end']:bar[key]=(r@bar[key]+offset).tolist()
    result=paired_profile_spacing(points,ids,bars,d,n,.016)
    pair=result['pairs'][0]
    assert pair['status']=='measured' and pair['median_m']==pytest.approx(.15,abs=.0002)
    assert pair['paired_coverage']==1
    assert not result['variation_is_uncertainty']
    # Published transverse centres reproduce every section's distance.
    for section in pair['sections']:
        a,b=np.array(section['centres_transverse_m'])
        assert np.linalg.norm(a-b)==pytest.approx(section['spacing_m'])
        assert min(section['support_counts'])>=3


def test_profile_refuses_nonoverlap_instead_of_extrapolating():
    points,ids,bars=fixture();bars[1]['start'][0]=2.1;bars[1]['end'][0]=3
    pair=paired_profile_spacing(points,ids,bars,[1,0,0],[0,0,1],.016)['pairs'][0]
    assert pair['median_m'] is None and pair['sections']==[]


def test_profile_refuses_sparse_shared_support_and_keeps_unavailable_evidence():
    points,ids,bars=fixture();keep=(points[:3000,0]<1.1)|(points[:3000,0]>1.8)
    bars[0]['evidence']['point_indices']=ids[:3000][keep].tolist()
    pair=paired_profile_spacing(points,ids,bars,[1,0,0],[0,0,1],.016)['pairs'][0]
    assert pair['sections'] and pair['paired_coverage']<.75
    assert pair['status']=='unavailable_scan_support' and pair['median_m'] is None


def test_profile_point_id_lookup_is_independent_of_array_order():
    points,ids,bars=fixture()
    a=paired_profile_spacing(points,ids,bars,[1,0,0],[0,0,1],.016)
    order=np.random.default_rng(14).permutation(len(points))
    b=paired_profile_spacing(points[order],ids[order],bars,[1,0,0],[0,0,1],.016)
    assert a==b
