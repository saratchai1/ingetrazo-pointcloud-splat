from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from pointcloud_splat.layers import select_layer
from pointcloud_splat.duplicates import group_layer_duplicates
from pointcloud_splat.rebar import inspect
from pointcloud_splat.parsers.las_parser import read_las
from test_bar_tracks import dataset, cylinder


@pytest.mark.parametrize('rotated', [False, True])
def test_two_layers_select_independently_with_spacing_and_source_ids(rotated):
    near = np.concatenate([cylinder(np.linspace(0, 1, 450), y) for y in [0., .15, .3]])
    far = np.concatenate([cylinder(np.linspace(0, 1, 150), y) for y in [0., .18]])
    far[:, 2] += .08
    ds = dataset(np.concatenate([near, far]))
    ds.source_point_indices = 100+np.arange(len(ds.coords))*7
    if rotated:
        ds.rotation_x_deg = 21; ds.rotation_y_deg = 32; ds.rotation_z_deg = 43
        ds.offset = np.array([.8, -.2, .3])
    basis = ds.apply_transform(np.vstack([np.zeros(3), np.eye(3)]))
    direction = basis[1]-basis[0]; normal = basis[3]-basis[0]
    first = inspect(ds, [-3]*3, [3]*3, direction, layer_normal=normal)
    second = inspect(ds, [-3]*3, [3]*3, direction, layer_normal=normal, layer_rank=1)
    assert len(first['bars']) == 3 and len(second['bars']) == 2
    assert sorted(s['centreline_m'] for s in first['spacing']) == pytest.approx([.15, .15, .30], abs=.001)
    assert second['spacing'][0]['centreline_m'] == pytest.approx(.18, abs=.001)
    for report, allowed in [(first, ds.source_point_indices[:len(near)]), (second, ds.source_point_indices[len(near):])]:
        used = {i for b in report['bars'] for i in b['evidence']['point_indices']}
        assert used <= set(allowed)
        removed = set(report['layer_filter']['excluded_point_indices'])
        assert not used & removed
        json.dumps(report, allow_nan=False)


def test_layer_histogram_large_translation_and_normal_scale():
    rng = np.random.default_rng(103)
    p = np.column_stack([rng.uniform(0, 1, 1000), rng.uniform(0, 1, 1000), rng.normal(0, .001, 1000)])
    p = np.concatenate([p, p[:200]+[0,0,.08]])
    ids = np.arange(len(p))
    a, ia, info = select_layer(p, ids, [0,0,1], .016)
    b, ib, other = select_layer(p+[2e6,3e6,4e6], ids, [0,0,5], .016)
    assert np.array_equal(ia, ib)
    assert b-[2e6,3e6,4e6] == pytest.approx(a, abs=1e-9)
    assert other['selected_depth_m']-4e6 == pytest.approx(info['selected_depth_m'], abs=1e-9)


@pytest.mark.parametrize('normal', [[0,0,0], [float('nan'),0,1], [0,1]])
def test_invalid_layer_normal_rejected(normal):
    with pytest.raises(ValueError, match='normal'):
        select_layer(np.zeros((30,3)), np.arange(30), normal, .016)


def test_parallel_normal_and_missing_rank_rejected():
    ds = dataset(cylinder(np.linspace(0,1,300)))
    with pytest.raises(ValueError, match='perpendicular'):
        inspect(ds, [-2]*3, [2]*3, [1,0,0], layer_normal=[1,0,0])
    with pytest.raises(ValueError, match='unavailable'):
        inspect(ds, [-2]*3, [2]*3, [1,0,0], layer_normal=[0,0,1], layer_rank=31)


@pytest.mark.parametrize('wall', [False, True])
def test_layer_selection_does_not_turn_floor_or_wall_into_bar(wall):
    ds = read_las(Path(__file__).parent/'fixtures/rohbau3d-floor.laz', source_units='m', origin=[0,0,0])
    if wall:
        ds.rotation_x_deg = 90
    normal = [0,1,0] if wall else [0,0,1]
    p = ds.apply_transform(ds.coords)
    report = inspect(ds, p.min(0)-.001, p.max(0)+.001, [1,0,0], layer_normal=normal)
    assert not report['bars']
    assert report['background_filter']['removed_points'] > .99*len(p)


def proposal(y, z, support, start=0., end=1.):
    return {'start': [start,y,z], 'end': [end,y,z], 'accepted': False,
            'evidence': {'support': support, 'point_indices': list(range(support))}}


def test_weak_duplicate_keeps_separate_evidence_and_strong_fit():
    strong, weak = proposal(0,0,400), proposal(.009,.009,50,.1,.9)
    original = deepcopy(weak)
    bars, info = group_layer_duplicates([weak, strong], [1,0,0], [0,0,1], .016)
    assert len(bars) == 1 and info['grouped_proposals'] == 1
    assert bars[0]['start'] == [0.,0,0] and bars[0]['evidence']['support'] == 400
    duplicate = bars[0]['grouped_duplicate_proposals'][0]
    assert duplicate['proposal'] == original
    assert duplicate['review_required'] and not duplicate['used_for_primary_fit']
    assert not bars[0]['accepted']
    json.dumps(bars, allow_nan=False)


@pytest.mark.parametrize('weak', [proposal(.04,0,50), proposal(0,.04,50),
                                  proposal(.009,.009,200), proposal(.009,.009,50,2.,3.)])
def test_distinct_bars_layers_or_fragments_not_grouped(weak):
    bars, info = group_layer_duplicates([proposal(0,0,400), deepcopy(weak)], [1,0,0], [0,0,1], .016)
    assert len(bars) == 2 and info['grouped_proposals'] == 0


def test_split_proposals_reconsolidate_after_outlying_islands_removed():
    # The raw proposals' centres differ due to distant disconnected islands.
    # Their continuous segments are two surfaces of the same single track.
    x = np.linspace(0, 1, 200)
    a = np.column_stack([x, np.full(200,-.006), np.zeros(200)])
    b = np.column_stack([x, np.full(200,.006), np.zeros(200)])
    islands = np.column_stack([np.full(100,2.),np.full(100,.12),np.zeros(100)])
    points = np.concatenate([a,b,islands])
    from pointcloud_splat.bar_tracks import continuous_tracks
    tracks, info = continuous_tracks(points, [np.arange(200), np.arange(200,500)],
                                     np.array([1.,0,0]), .016, 30, .25)
    assert len(tracks) == 1 and info['post_split_merges'] == 1
    assert set(tracks[0][0]) == set(range(400))
