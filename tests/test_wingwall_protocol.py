import importlib.util
import json
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('wingwall_trial',Path(__file__).parents[1]/'tools/run_wingwall_trial.py')
trial=importlib.util.module_from_spec(spec);spec.loader.exec_module(trial)


def fixture():
    reference=json.loads((Path(__file__).parents[1]/'docs/data/wingwall_reference.json').read_text())
    runs=[]
    for family,axis in [('X',0),('Y',1)]:
        bars=[]
        for lo,hi in reference['scan_identity_windows_m'][family]:
            value=(lo+hi)/2
            bars.append({'start':[value,0,0] if axis==0 else [0,value,0],
                         'end':[value,3,0] if axis==0 else [3,value,0]})
        spacing=[{'bars':[i,i+1],'centreline_m':abs(bars[i+1]['start'][axis]-bars[i]['start'][axis])}
                 for i in range(len(bars)-1)]
        runs.append({'family':family,'report':{'bars':bars,'spacing':spacing}})
    return runs,reference


def test_complete_source_identities_assign_every_reference_once():
    runs,reference=fixture();result=trial.assess(runs,reference)
    assert result['spacing_assessment']['scored_cells']==18
    assert result['spacing_assessment']['status']=='complete_verified'
    assert len(result['line_assignments'])==20


def test_right_count_with_wrong_bar_location_cannot_score_family():
    runs,reference=fixture();runs[0]['report']['bars'][0]['start'][0]=-.2
    runs[0]['report']['bars'][0]['end'][0]=-.2
    result=trial.assess(runs,reference)
    assert result['counts'][0]['matched']
    assert not result['counts'][0]['source_identities_matched']
    assert result['spacing_assessment']['scored_cells']==7
    assert result['spacing_assessment']['status']=='partial_verified'


def test_surplus_bar_never_selects_best_fitting_subset():
    runs,reference=fixture();runs[0]['report']['bars'].append({'start':[.1,0,0],'end':[.1,3,0]})
    result=trial.assess(runs,reference)
    assert not result['counts'][0]['matched']
    assert result['spacing_assessment']['scored_cells']==7


def test_missing_axial_overlap_does_not_create_measurement():
    runs,reference=fixture();runs[0]['report']['spacing']=[]
    result=trial.assess(runs,reference)
    assert result['spacing_assessment']['verified_pairs']==18
    assert result['spacing_assessment']['scored_cells']==7
    assert all(p['error_m'] is None for p in result['spacing_assessment']['pairs'] if p['reference_id'].startswith('X:'))


def test_profile_metric_never_falls_back_to_straight_model_spacing():
    runs,reference=fixture()
    result=trial.assess(runs,reference,metric='paired_profile')
    assert result['spacing_assessment']['scored_cells']==0
    assert result['spacing_assessment']['spacing_mae_m'] is None


def test_profile_metric_uses_only_explicit_paired_scan_measurements():
    runs,reference=fixture()
    for run in runs:
        run['report']['profile_spacing']={'pairs':[
            {'bars':s['bars'],'median_m':s['centreline_m']+.001}
            for s in run['report']['spacing']]}
    scan=trial.assess(runs,reference,metric='paired_profile')
    model=trial.assess(runs,reference)
    assert scan['measurement_metric']=='paired_profile'
    assert scan['spacing_assessment']['scored_cells']==18
    assert all(a['measured_m']-b['measured_m']==pytest.approx(.001)
               for a,b in zip(scan['spacing_assessment']['pairs'],model['spacing_assessment']['pairs']))
