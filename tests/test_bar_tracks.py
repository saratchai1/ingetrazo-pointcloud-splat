import numpy as np
import pytest

from pointcloud_splat.bar_tracks import continuous_tracks
from pointcloud_splat.data_models import PointCloudDataset
from pointcloud_splat.rebar import inspect


def dataset(points):
    ds = PointCloudDataset('synthetic continuity', '', points, np.full((len(points), 4), 255, dtype=np.uint8))
    ds.coordinate_frame = {'source_units': 'm', 'unit_to_m': 1., 'source_origin': [0., 0., 0.]}
    return ds


def cylinder(x, y=0.):
    phi = np.arange(len(x)) * 2.399963
    return np.column_stack([x, y + .008*np.cos(phi), .008*np.sin(phi)])


def test_perpendicular_bars_cannot_support_phantom_lines():
    # Each crossing supplies many points, and their union has a long PCA axis.
    # Between crossings there is no steel in the requested X direction.
    along = np.linspace(0, .6, 500)
    phi = np.arange(len(along))*2.399963
    points = np.concatenate([np.column_stack([x+.008*np.cos(phi), along, .008*np.sin(phi)])
                             for x in np.arange(5)*.15])
    ds = dataset(points)
    report = inspect(ds, [-1]*3, [1]*3, [1, 0, 0])
    assert report['bars'] == []
    assert report['track_filter']['rejected_short_or_sparse'] > 0
    actual = inspect(ds, [-1]*3, [1]*3, [0, 1, 0])
    assert len(actual['bars']) == 5
    assert all(b['evidence']['axial_coverage'] > .9 for b in actual['bars'])


@pytest.mark.parametrize('gap, expected', [(.02, 1), (.12, 2)])
def test_small_scan_gap_survives_large_gap_splits(gap, expected):
    x = np.r_[np.linspace(0, .4, 180), np.linspace(.4+gap, .8+gap, 180)]
    report = inspect(dataset(cylinder(x)), [-1]*3, [2]*3, [1, 0, 0])
    assert len(report['bars']) == expected
    if expected == 2:
        assert all(np.linalg.norm(np.subtract(b['end'], b['start'])) < .41 for b in report['bars'])
        # Disconnected portions do not produce a spacing interval.
        assert report['spacing'] == []


def test_duplicate_surface_proposals_merge_with_all_evidence():
    x = np.linspace(0, 1, 100)
    points = np.concatenate([np.column_stack([x, np.full(100, y), np.zeros(100)]) for y in [-.006, .006]])
    tracks, stats = continuous_tracks(points, [np.arange(100), np.arange(100, 200)],
                                     np.array([1., 0., 0.]), .016, 30, .25)
    assert len(tracks) == 1 and stats['merged_proposals'] == 1
    assert set(tracks[0][0]) == set(range(200))
    assert tracks[0][1][1] == pytest.approx(0., abs=1e-12)


def test_distinct_parallel_bars_stay_separate():
    x = np.linspace(0, 1, 300)
    ds = dataset(np.concatenate([cylinder(x, y) for y in [0., .064, .128]]))
    report = inspect(ds, [-1]*3, [2]*3, [1, 0, 0])
    assert len(report['bars']) == 3
    assert sorted(s['centreline_m'] for s in report['spacing']) == pytest.approx([.064, .064, .128], abs=.001)


def test_wide_support_is_not_one_physical_bar():
    x = np.linspace(0, 1, 100)
    points = np.concatenate([np.column_stack([x, np.full(100, y), np.zeros(100)]) for y in [-.02, .02]])
    tracks, stats = continuous_tracks(points, [np.arange(len(points))],
                                     np.array([1., 0., 0.]), .016, 30, .25)
    assert not tracks and stats['rejected_width'] == 1


def test_many_points_in_islands_do_not_prove_continuity():
    # Dense narrow islands separated by gaps below the hard splitting limit.
    # Fine coverage must reject this even though the old 10-bin test passes.
    centres = np.arange(26)*.046
    x = np.repeat(centres, 40)
    points = np.column_stack([x, np.zeros(len(x)), np.zeros(len(x))])
    tracks, stats = continuous_tracks(points, [np.arange(len(points))],
                                     np.array([1., 0., 0.]), .016, 30, .25)
    assert not tracks
    assert stats['rejected_coverage'] == 1


def test_rotated_continuity_filter_preserves_record_ids():
    x = np.r_[np.linspace(0, .4, 180), np.linspace(.6, 1., 180)]
    ds = dataset(cylinder(x))
    ds.source_point_indices = np.arange(len(x))*3+100
    ds.rotation_x_deg = 21; ds.rotation_y_deg = 31; ds.rotation_z_deg = 47
    basis = ds.apply_transform(np.array([[0., 0., 0.], [1., 0., 0.]]))
    direction = basis[1]-basis[0]
    report = inspect(ds, [-2]*3, [2]*3, direction)
    assert len(report['bars']) == 2
    used = [i for b in report['bars'] for i in b['evidence']['point_indices']]
    assert len(used) == len(set(used)) == len(x)
    assert set(used) == set(ds.source_point_indices)
