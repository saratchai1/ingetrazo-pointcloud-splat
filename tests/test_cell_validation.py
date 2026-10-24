import pytest
from pointcloud_splat.cell_validation import compare_cell_pairs


def match(ref='A',scan='s',verified=True,anchor='reviewed fiducial crosswalk'):
    return {'reference_id':ref,'measurement_id':scan,'verified':verified,'anchor_evidence':anchor}


def test_order_guess_and_unanchored_flag_cannot_score_spacing():
    for m in [match(verified=False),match(anchor='')]:
        result=compare_cell_pairs({'A':.15},{'s':.151},[m])
        assert result['scored_cells']==0 and result['spacing_mae_m'] is None
        assert result['pairs'][0]['error_m'] is None


def test_partial_verified_cells_keep_explicit_reference_coverage():
    result=compare_cell_pairs({'A':.15,'B':.20},{'s':.152},[match()])
    assert result['status']=='partial_verified' and result['reference_cells']==2
    assert result['scored_cells']==1 and result['spacing_mae_m']==pytest.approx(.002)


def test_verified_mapping_without_scan_support_cannot_score():
    result=compare_cell_pairs({'A':.15},{'s':None},[match()])
    assert result['verified_pairs']==1 and result['scored_cells']==0
    assert result['status']=='unavailable_scan_support' and result['spacing_mae_m'] is None


def test_complete_verified_cells_have_signed_errors_and_mae():
    result=compare_cell_pairs({'A':.15,'B':.20},{'s':.152,'t':.197},[match(),match('B','t')])
    assert result['status']=='complete_verified'
    assert [p['error_m'] for p in result['pairs']]==pytest.approx([.002,-.003])
    assert result['spacing_mae_m']==pytest.approx(.0025)


def test_duplicate_or_unknown_correspondence_rejected():
    with pytest.raises(ValueError,match='one-to-one'):
        compare_cell_pairs({'A':.15},{'s':.15},[match(),match()])
    with pytest.raises(ValueError,match='Unknown'):
        compare_cell_pairs({'A':.15},{'s':.15},[match(scan='missing')])


def test_no_pairs_never_reports_zero_error():
    result=compare_cell_pairs({'A':.15},{},[])
    assert result['spacing_mae_m'] is None and result['spacing_max_abs_error_m'] is None


@pytest.mark.parametrize('changed', ['source_sha256','reference_sha256','measurement_sha256'])
def test_stale_crosswalk_hash_cannot_be_used(changed):
    from pointcloud_splat.cell_validation import bound_matches
    expected={'source_sha256':'source','reference_sha256':'reference','measurement_sha256':'grid'}
    document={**expected,'matches':[match()]};document[changed]='stale'
    with pytest.raises(ValueError,match='exact source'):
        bound_matches(document,expected)


def test_hash_bound_crosswalk_preserves_explicit_matches():
    from pointcloud_splat.cell_validation import bound_matches
    expected={'source_sha256':'source','reference_sha256':'reference','measurement_sha256':'grid'}
    pairs=[match()]
    assert bound_matches({**expected,'matches':pairs},expected)==pairs
