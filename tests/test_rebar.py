import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import numpy as np
import pytest
import laspy
from pointcloud_splat.parsers.las_parser import read_las
from pointcloud_splat.data_models import PointCloudDataset
from pointcloud_splat.rebar import inspect, commit_review


def cloud(tmp_path, suffix='.las', units='m', count=300):
    h = laspy.LasHeader(point_format=3, version='1.2')
    h.offsets = [600000., 1500000., 100.]
    h.scales = [.0001]*3
    las = laspy.LasData(h)
    t = np.linspace(0, 2, count)
    phi = np.arange(count)*2.399963
    points = np.concatenate([np.column_stack([t, y+.008*np.cos(phi), .008*np.sin(phi)]) for y in [0., .15, .30]])
    xyz = points + h.offsets
    las.x, las.y, las.z = xyz.T
    las.red = np.full(len(xyz), 65535, dtype=np.uint16)
    path = tmp_path/('scan'+suffix); las.write(path)
    return read_las(path, source_units=units), xyz


@pytest.mark.parametrize('suffix', ['.las', '.laz'])
def test_precision_and_laz(tmp_path, suffix):
    ds, truth = cloud(tmp_path, suffix)
    assert ds.coords.dtype == np.float64
    assert np.max(abs(ds.coords)) < 3
    assert np.max(abs(ds.source_coordinates()-truth)) < .000051
    assert ds.colors[0].tolist() == [255,0,0,255]


def test_units_and_source_roi(tmp_path):
    ds, _ = cloud(tmp_path)
    small = read_las(ds.filepath, source_units='mm', roi=([600000, 1500000, 99], [600001, 1500001, 101]))
    assert np.ptp(small.coords[:,0]) <= .001001
    with pytest.raises(ValueError, match='source_units'):
        read_las(ds.filepath)
    with pytest.raises(ValueError, match='ROI'):
        read_las(ds.filepath, source_units='m', roi=([1,2,3],[0,1,2]))


def test_truncated_rejected(tmp_path):
    ds, _ = cloud(tmp_path)
    path = Path(ds.filepath); data = path.read_bytes(); path.write_bytes(data[:-30])
    with pytest.raises((ValueError, laspy.errors.LaspyException)):
        read_las(path, source_units='m')


def test_synthetic_spacing_noise_and_evidence(tmp_path):
    ds, _ = cloud(tmp_path)
    rng = np.random.default_rng(27)
    ds.coords += rng.normal(0, .0003, ds.coords.shape)
    report = inspect(ds, [-3,-3,-3], [3,3,3], [1,0,0])
    assert len(report['bars']) == 3
    assert sorted(s['centreline_m'] for s in report['spacing']) == pytest.approx([.15,.15,.30], abs=.001)
    assert all(not b['accepted'] for b in report['bars'])
    assert all(b['evidence']['support'] > 200 for b in report['bars'])
    assert len(report['source_sha256']) == 64


def test_transform_roi_and_renderer_agree(tmp_path):
    from pointcloud_splat.scene_proxy import create_pointcloud_proxy, sync_proxy_from_dataset
    from pointcloud_splat.renderer import CloudRenderer
    from core.scene import Scene
    ds, _ = cloud(tmp_path)
    ds.rotation_z_deg=35; ds.scale=1.7; ds.offset=np.array([2.,3.,4.])
    manual = ds.manual_transform(ds.coords)
    create_pointcloud_proxy(ds, Scene())
    assert np.allclose(ds.apply_transform(ds.coords), manual, atol=2e-6)
    matrix=CloudRenderer._get_obj_matrix(None, ds).reshape(3,4)
    assert np.allclose(ds.coords @ matrix[:,:3].T+matrix[:,3], manual, atol=2e-6)
    ds.scale=2.; sync_proxy_from_dataset(ds)
    assert np.allclose(ds.apply_transform(ds.coords), ds.manual_transform(ds.coords), atol=2e-6)
    pts, ids=ds.world_roi([-10,-10,-10],[10,10,10])
    assert np.allclose(pts, ds.apply_transform(ds.coords)[ids])


@pytest.mark.parametrize('use_layer', [False, True])
def test_native_undo_redo_and_persistence(tmp_path, use_layer):
    from core.scene import Scene
    from core.history import History
    from formats import igz
    ds, _=cloud(tmp_path)
    report=inspect(ds, [-3]*3, [3]*3, [1,0,0], layer_normal=[0,0,1] if use_layer else None)
    for b in report['bars']: b['accepted']=True
    scene=Scene(); hist=History(scene)
    original=scene.version
    groups=commit_review(hist, report)
    assert len(groups)==3 and len(scene.groups)==3
    assert scene.version > original
    assert all(g.ifc['class']=='IfcReinforcingBar' and len(g.mesh.faces)==14 for g in groups)
    hist.undo(); assert not scene.groups and not scene.plugin_data
    hist.redo(); assert len(scene.groups)==3
    path=tmp_path/'test.igz'; igz.save_scene(scene, path)
    back=Scene(); igz.load_into(back,path)
    assert back.plugin_data==scene.plugin_data
    assert [g.ext for g in back.groups]==[g.ext for g in scene.groups]
    hist.undo(); hist.redo(); assert len(scene.groups)==3


def test_empty_roi_and_unverified_units(tmp_path):
    ds, _=cloud(tmp_path)
    assert not inspect(ds,[10]*3,[11]*3,[1,0,0])['bars']
    ds.coordinate_frame=None
    with pytest.raises(ValueError,match='confirmed units'):
        inspect(ds,[-3]*3,[3]*3,[1,0,0])


def test_shared_origin_and_import_roi_indices(tmp_path):
    ds, _ = cloud(tmp_path)
    origin = ds.coordinate_frame['source_origin']
    path = tmp_path/'second.las'
    las = laspy.read(ds.filepath); las.x = np.asarray(las.x)+3; las.write(path)
    other = read_las(path, source_units='m', origin=origin)
    assert other.coordinate_frame['source_origin'] == origin
    assert other.coords[0,0] == pytest.approx(3.)
    cropped = read_las(ds.filepath, source_units='m', roi=([600001,1499999,99],[600002,1500001,101]))
    report = inspect(cropped, [-5]*3,[5]*3,[1,0,0])
    assert all(min(b['evidence']['point_indices']) >= 150 for b in report['bars'])
    assert np.array(report['local_to_world_4x4']).shape == (4,4)


def test_transformed_spacing_ground_truth(tmp_path):
    ds, _=cloud(tmp_path)
    ds.rotation_x_deg=23; ds.rotation_y_deg=15; ds.rotation_z_deg=37
    ds.scale=1.5; ds.offset=np.array([2.,-1.,3.])
    axis = ds.manual_transform(np.array([[1.,0.,0.],[0.,0.,0.]]))
    report=inspect(ds,[-10]*3,[10]*3,axis[0]-axis[1], diameter_m=.024)
    assert len(report['bars'])==3
    assert sorted(s['centreline_m'] for s in report['spacing']) == pytest.approx([.225,.225,.45],abs=.001)


def test_sparse_noise_and_disjoint_intervals(tmp_path):
    from pointcloud_splat.rebar import spacing
    ds,_=cloud(tmp_path)
    rng=np.random.default_rng(73)
    ds.coords=rng.uniform(-1,1,(1000,3))
    assert not inspect(ds,[-2]*3,[2]*3,[1,0,0])['bars']
    bars=[{'start':[0,0,0],'end':[1,0,0]}, {'start':[2,.15,0],'end':[3,.15,0]}]
    assert spacing(bars,[1,0,0])==[]
    bars[1]['end']=[3,.17,0]
    with pytest.raises(ValueError,match='parallel'):
        spacing(bars,[1,0,0])


def test_invalid_review_is_atomic(tmp_path):
    from core.scene import Scene
    from core.history import History
    ds,_=cloud(tmp_path)
    report=inspect(ds,[-3]*3,[3]*3,[1,0,0])
    scene=Scene(); hist=History(scene)
    with pytest.raises(ValueError,match='Accept'):
        commit_review(hist,report)
    for bar in report['bars']: bar['accepted']=True
    report['bars'][-1]['start']=[float('nan'),0,0]
    with pytest.raises(ValueError):
        commit_review(hist,report)
    assert not scene.groups and not scene.plugin_data


def test_review_dialog_end_to_end_offscreen(tmp_path):
    from types import SimpleNamespace
    from PySide6.QtWidgets import QApplication, QWidget, QCheckBox, QDoubleSpinBox
    from PySide6.QtCore import Qt
    from core.scene import Scene
    from core.history import History
    from pointcloud_splat.ui.rebar_dialog import RebarDialog
    app=QApplication.instance() or QApplication([])
    ds,_=cloud(tmp_path)
    manager=QWidget(); manager.datasets=[ds]; manager._active_idx=0
    scene=Scene(); history=History(scene)
    manager.app=SimpleNamespace(viewport=SimpleNamespace(history=history,scene=scene,notify_scene_changed=lambda:None))
    manager.chk_clipping=QCheckBox(); manager.chk_clipping.setChecked(True)
    for axis in 'xyz':
        for end, value in [('min',-3),('max',3)]:
            spin=QDoubleSpinBox();spin.setRange(-10,10);spin.setValue(value)
            setattr(manager,f'spin_{axis}_{end}',spin)
    dialog=RebarDialog(manager)
    dialog.analyze()
    assert dialog.table.rowCount()==3
    dialog.layer_normal.setCurrentText('Z')
    dialog.analyze()
    assert dialog.report['layer_filter']['enabled']
    assert dialog.table.rowCount()==3
    for row in range(3): dialog.table.item(row,0).setCheckState(Qt.Checked)
    dialog.table.item(0,1).setText('0.05')
    reviewed=dialog.reviewed()
    assert reviewed['bars'][0]['review_adjusted']
    dialog.create()
    assert len(scene.groups)==3
    history.undo(); assert not scene.groups
    history.redo(); assert len(scene.groups)==3
    dialog.close();manager.close()


def test_native_transform_undo_roi_subset(tmp_path):
    from core.scene import Scene
    from core.history import History, MoveGroupCommand
    from PySide6.QtGui import QVector3D
    from pointcloud_splat.scene_proxy import create_pointcloud_proxy
    ds,_=cloud(tmp_path)
    scene=Scene(); history=History(scene)
    group=create_pointcloud_proxy(ds,scene)
    before=ds.apply_transform(ds.coords)
    history.execute(MoveGroupCommand(group, QVector3D(1.,2.,3.)))
    assert np.allclose(ds.apply_transform(ds.coords),before+[1,2,3],atol=1e-6)
    points, ids=ds.world_roi([1.5,1.9,2.9],[2.5,2.2,3.1])
    assert 0<len(ids)<len(ds.coords)
    assert np.all((points >= [1.5,1.9,2.9]) & (points <= [2.5,2.2,3.1]))
    history.undo();assert np.allclose(ds.apply_transform(ds.coords),before,atol=1e-6)
    history.redo();assert np.allclose(ds.apply_transform(ds.coords),before+[1,2,3],atol=1e-6)


@pytest.mark.parametrize('version,fmt', [('1.2',0),('1.4',7),('1.4',10)])
def test_las_versions_formats_and_feet(tmp_path,version,fmt):
    header=laspy.LasHeader(point_format=fmt,version=version)
    header.offsets=[2000000.,5000000.,30.];header.scales=[.001]*3
    las=laspy.LasData(header)
    las.x=np.array([2000000.,2000000.001]);las.y=np.array([5000000.,5000000.001]);las.z=np.array([30.,30.001])
    path=tmp_path/'formats.laz';las.write(path)
    ds=read_las(path,source_units='ft')
    assert ds.coords[1] == pytest.approx([.0003048]*3,abs=1e-9)


def test_saved_report_reconstructs_source_alignment(tmp_path):
    import json
    ds,_=cloud(tmp_path)
    ds.scale=1.3;ds.rotation_z_deg=19;ds.offset=np.array([1.,2.,3.])
    report=inspect(ds,[-10]*3,[10]*3,[np.cos(np.radians(19)),np.sin(np.radians(19)),0],diameter_m=.0208)
    report=json.loads(json.dumps(report,allow_nan=False))
    frame=report['coordinate_frame']
    reloaded=read_las(report['source'],source_units=frame['source_units'],origin=frame['source_origin'])
    matrix=np.array(report['local_to_world_4x4'])
    assert np.allclose(reloaded.coords @ matrix[:3,:3].T+matrix[:3,3],ds.apply_transform(ds.coords))


def test_native_instance_transform_and_flat_scan(tmp_path):
    from core.scene import Scene
    from PySide6.QtGui import QMatrix4x4
    from pointcloud_splat.scene_proxy import create_pointcloud_proxy
    ds,_=cloud(tmp_path)
    ds.coords[:,2]=0.; ds._raw_bounds=(ds.coords.min(axis=0),ds.coords.max(axis=0))
    ds.pivot=(ds._raw_bounds[0]+ds._raw_bounds[1])/2
    group=create_pointcloud_proxy(ds,Scene())
    transform=QMatrix4x4();transform.translate(1.,2.,3.);transform.scale(1.2)
    group.xform=transform
    assert np.allclose(ds.apply_transform(ds.coords),ds.coords*1.2+[1,2,3],atol=1e-6)


@pytest.mark.parametrize('vertical', [False, True])
def test_real_rohbau_floor_and_rotated_wall_are_not_bars(vertical):
    ds=read_las(Path(__file__).parent/'fixtures/rohbau3d-floor.laz',source_units='m',origin=[0,0,0])
    if vertical:
        ds.rotation_x_deg=90
    points=ds.apply_transform(ds.coords)
    report=inspect(ds,points.min(0)-.001,points.max(0)+.001,[1,0,0])
    assert report['bars']==[]
    assert report['background_filter']['removed_points'] > .99*len(points)
    assert report['background_filter']['planes'][0]['kind']==('vertical_surface' if vertical else 'horizontal_surface')
    removed=report['background_filter']['planes'][0]['removed_point_indices']
    assert len(set(removed))==len(removed) and max(removed)<ds.point_count


@pytest.mark.parametrize('rotated', [False, True])
def test_bars_survive_floor_and_wall_separation(tmp_path, rotated):
    ds,_=cloud(tmp_path)
    bars=ds.coords.copy();bars[:,2]+=.06
    rng=np.random.default_rng(81)
    x,y=np.meshgrid(np.linspace(0,2,160),np.linspace(-.1,.4,50))
    floor=np.column_stack([x.ravel(),y.ravel(),np.zeros(x.size)])
    x,z=np.meshgrid(np.linspace(0,2,160),np.linspace(0,.3,40))
    wall=np.column_stack([x.ravel(),np.full(x.size,-.1),z.ravel()])
    background=np.concatenate([floor,wall])+rng.normal(0,.0004,(len(floor)+len(wall),3))
    ds.coords=np.concatenate([bars,background])
    if rotated:
        ds.rotation_x_deg=23;ds.rotation_y_deg=15;ds.rotation_z_deg=37
        ds.offset=np.array([2.,1.,3.])
    world=ds.apply_transform(ds.coords)
    basis=ds.apply_transform(np.array([[1.,0.,0.],[0.,0.,0.]]))
    report=inspect(ds,world.min(0)-.001,world.max(0)+.001,basis[0]-basis[1])
    assert len(report['bars'])==3
    assert sorted(s['centreline_m'] for s in report['spacing'])==pytest.approx([.15,.15,.30],abs=.001)
    assert len(report['background_filter']['planes'])==2
    # Evidence must still refer to original ROI records after filtering.
    assert all(max(b['evidence']['point_indices'])<len(bars) for b in report['bars'])
    assert report['background_filter']['removed_points'] >= .99*len(background)


def test_coplanar_bars_are_not_mistaken_for_a_solid_plane(tmp_path):
    ds,_=cloud(tmp_path)
    ds.coords[:,2]=0.
    report=inspect(ds,[-3]*3,[3]*3,[1,0,0])
    assert len(report['bars'])==3
    assert report['background_filter']['removed_points']==0
    assert sorted(s['centreline_m'] for s in report['spacing'])==pytest.approx([.15,.15,.30],abs=.001)
