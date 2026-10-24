import numpy as np
import pytest
from pointcloud_splat.roi_audit import audit_traces, trace_records


def test_invalid_source_depth_and_each_crop_have_disjoint_counts():
    xyz = np.ones((20,3)); xyz[6] = 0; xyz[7] = np.nan
    valid = np.isfinite(xyz).all(1) & np.any(xyz != 0,1)
    raw = valid.copy(); raw[8] = False
    slab = raw.copy(); slab[9] = False
    rows = audit_traces(xyz,5,4,{'bar':[[0,1],[4,1]]},{'raw':raw,'slab':slab},radius=0)
    row = rows[0]
    assert row['in_image_records'] == 5 and row['invalid_source_depth_records'] == 2
    assert row['valid_source_depth_records'] == 3
    assert [s['removed_at_stage'] for s in row['stages']] == [1,1]
    assert row['retained_original_record_ids'] == [5]


def test_missing_depth_is_never_called_roi_removal():
    xyz = np.zeros((20,3)); empty = np.zeros(20,dtype=bool)
    row = audit_traces(xyz,5,4,{'bar':[[0,1],[4,1]]},{'roi':empty},radius=0)[0]
    assert row['invalid_source_depth_records'] == 5
    assert row['stages'][0]['removed_at_stage'] == 0
    assert not row['retained_original_record_ids']


def test_clipped_trace_preserves_original_record_coordinates():
    ids, outside = trace_records([[-2,1],[2,1]],5,4,0)
    assert outside == 2 and ids.tolist() == [5,6,7]


def test_non_nested_masks_rejected():
    with pytest.raises(ValueError,match='nested'):
        audit_traces(np.zeros((20,3)),5,4,{}, {'bad':np.ones(20,dtype=bool)})
    with pytest.raises(ValueError,match='boolean'):
        audit_traces(np.ones((20,3)),5,4,{}, {'bad':np.ones(20,dtype=int)})
    with pytest.raises(ValueError,match='organized'):
        audit_traces(np.ones((19,3)),5,4,{}, {})
