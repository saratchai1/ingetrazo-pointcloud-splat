import json
import numpy as np
import pytest
from pointcloud_splat.profile_spacing import paired_profile_spacing, theil_sen
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


def fanning(tilt=.03, rotation=None):
    # Bar 0 stays on the guided axis; bar 1 drifts away: spacing .15 -> .15+2*tilt.
    samples=[];bars=[]
    for i,slope in enumerate([0,tilt]):
        x=np.linspace(0,2,4000)
        samples.append(np.column_stack([x,slope*x+i*.15,np.zeros(len(x))]))
        bars.append({'start':[0,i*.15,0],'end':[2,i*.15,0],
                     'evidence':{'point_indices':(np.arange(len(x))+i*len(x)).tolist()}})
    points=np.concatenate(samples);d=np.array([1.,0,0]);n=np.array([0.,0,1])
    if rotation is not None:
        offset=np.array([8.,-3.,5.]);points=points@rotation.T+offset;d=rotation@d;n=rotation@n
        for bar in bars:
            for key in ['start','end']:bar[key]=(rotation@bar[key]+offset).tolist()
    return points,np.arange(len(points)),bars,d,n


@pytest.mark.parametrize('rotated',[False,True])
def test_axial_trend_reports_nonparallel_support_without_changing_median(rotated):
    r=np.array([[0.,-1,0],[.6,0,-.8],[.8,0,.6]]) if rotated else None
    points,ids,bars,d,n=fanning(rotation=r)
    pair=paired_profile_spacing(points,ids,bars,d,n,.016)['pairs'][0]
    values=[s['spacing_m'] for s in pair['sections']]
    assert pair['median_m']==np.median(values)
    trend=pair['axial_trend']
    # Section medians sample discrete points: allow 0.1 mm/m.
    assert trend['slope_m_per_m']==pytest.approx(.03,abs=1e-4)
    lo,hi=trend['section_axial_range_m']
    assert trend['fitted_change_m']==pytest.approx(.03*(hi-lo),abs=2e-4)
    assert trend['section_spacing_range_m']==[min(values),max(values)]
    # Drift is per bar in the pair's own (native index) order.
    assert trend['lateral_drift_deg'][0]==pytest.approx(0,abs=1e-9)
    assert trend['lateral_drift_deg'][1]==pytest.approx(np.degrees(np.arctan(.03)),abs=1e-2)
    assert not trend['station_registered'] and not trend['is_uncertainty']


def test_shared_drift_is_not_reported_as_spacing_trend():
    points,ids,bars=fixture()
    trend=paired_profile_spacing(points,ids,bars,[1,0,0],[0,0,1],.016)['pairs'][0]['axial_trend']
    assert trend['slope_m_per_m']==pytest.approx(0,abs=1e-9)
    assert trend['lateral_drift_deg']==pytest.approx([np.degrees(np.arctan(.04))]*2,abs=1e-2)


def test_trend_ignores_a_single_cluttered_section():
    x=np.arange(20.);y=.15+.01*x;y[7]+=1.
    slope,intercept=theil_sen(x,y)
    assert slope==pytest.approx(.01) and intercept==pytest.approx(.15)


def test_single_section_measurement_has_no_trend_or_nan():
    x=np.linspace(0,.03,200);points=np.concatenate([np.column_stack([x,np.full(200,y),np.zeros(200)]) for y in (0,.15)])
    bars=[{'start':[0,y,0],'end':[.04,y,0],'evidence':{'point_indices':list(range(i*200,(i+1)*200))}}
          for i,y in enumerate((0,.15))]
    pair=paired_profile_spacing(points,np.arange(400),bars,[1,0,0],[0,0,1],.016,min_length=.01)['pairs'][0]
    assert pair['status']=='measured' and len(pair['sections'])==1
    assert 'axial_trend' not in pair
    json.dumps(pair,allow_nan=False)


def test_trend_refuses_degenerate_input_instead_of_nan():
    for x,y in [([1.,1.],[.1,.2]),([0.,np.nan],[.1,.2])]:
        with pytest.raises(ValueError):
            theil_sen(x,y)
