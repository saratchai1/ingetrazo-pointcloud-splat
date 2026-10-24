import pytest
from pointcloud_splat.reference_validation import compare_reference


def test_real_trial_overcount_cannot_generate_a_spacing_accuracy():
    result=compare_reference(65,5,[.127]*16,[.13335]*16,correspondence_verified=True)
    assert result['count_error']==60
    assert result['spacing_mae_m'] is None
    assert result['spacing_status']=='unavailable_count_mismatch'


def test_correct_count_does_not_prove_spacing_correspondence():
    result=compare_reference(5,5,[.127]*4,[.13]*4)
    assert result['spacing_mae_m'] is None
    assert result['spacing_status']=='unavailable_unverified_correspondence'


def test_independently_matched_measurements_have_signed_errors_and_mae():
    result=compare_reference(3,3,[.152,.297],[.15,.30],correspondence_verified=True)
    assert result['per_spacing_error_m']==pytest.approx([.002,-.003])
    assert result['spacing_mae_m']==pytest.approx(.0025)
    assert result['spacing_max_abs_error_m']==pytest.approx(.003)


def test_verified_partial_pairs_are_not_silently_scored():
    with pytest.raises(ValueError,match='every reference'):
        compare_reference(3,3,[.152],[.15,.30],correspondence_verified=True)
