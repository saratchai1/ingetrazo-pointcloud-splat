# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline source-anchored real wingwall benchmark. Never opens a CAD document."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from pointcloud_splat.data_models import PointCloudDataset
from pointcloud_splat.rebar import inspect
from pointcloud_splat.cell_validation import compare_cell_pairs


def detect(path, seed=123, noise=.02):
    # Geometric protocol fixed independently of tape spacings/counts. Uniform
    # source-record sampling preserves density; equal-voxel sampling does not.
    from scipy.io import loadmat
    source=loadmat(path)['smallrebar4M']
    if source.ndim!=2 or source.shape[1]!=3 or not np.isfinite(source).all():
        raise ValueError('Expected original finite XYZ matrix')
    roi=np.all((source>=[.18,.15,.18])&(source<=[1.72,2.8,.27]),axis=1)
    ids=np.flatnonzero(roi)
    sample=np.sort(np.random.default_rng(seed).choice(len(ids),min(180000,len(ids)),replace=False))
    ids=ids[sample];p=source[ids]
    # Unique stepped outline fixes orientation. No reference-error orientation
    # search and no resizing of the source to nominal or measured dimensions.
    offset=float(source[:,1].max())
    q=np.column_stack([offset-p[:,1],p[:,0],p[:,2]])
    matrix=np.array([[0,-1,0,offset],[1,0,0,0],[0,0,1,0],[0,0,0,1.]])
    ds=PointCloudDataset('UNM wingwall',str(path),q,np.full((len(q),4),255,dtype=np.uint8))
    ds.source_point_indices=ids
    ds.coordinate_frame={'source_units':'m','unit_to_m':1.,'source_origin':[0.,0.,0.],
                         'source_to_analysis_4x4':matrix.tolist(),
                         'unit_basis':'GeoSLAM companion E57 SI convention and author CSV-exported XYZ; no independent scale calibration'}
    runs=[]
    for family,direction in [('X',[0,1,0]),('Y',[1,0,0])]:
        start=time.perf_counter()
        report=inspect(ds,q.min(0)-.001,q.max(0)+.001,direction,diameter_m=.015875,
                       layer_normal=[0,0,1],scan_noise_m=noise)
        runs.append({'family':family,'elapsed_s':time.perf_counter()-start,'report':report})
    return runs,{'source_rows':len(source),'roi_rows':int(roi.sum()),'sample_rows':len(ids),
                 'sample_seed':seed,'sample_method':'uniform_without_replacement; sorted original record IDs',
                 'source_to_analysis_4x4':matrix.tolist()}


def assess(runs, reference):
    measured={};truth={};matches=[];assignments=[];counts=[]
    for run,axis,key,labels in [(runs[0],0,'x_tape_inches',reference['x_bar_ids']),
                                (runs[1],1,'y_tape_inches',reference['y_bar_ids'])]:
        family=run['family'];report=run['report']
        bars=sorted(enumerate(report['bars']),key=lambda item: np.mean([item[1]['start'],item[1]['end']],axis=0)[axis])
        count_ok=len(bars)==len(labels)
        windows=reference['scan_identity_windows_m'][family]
        identity_ok=count_ok and all(lo<=np.mean([bar['start'],bar['end']],axis=0)[axis]<=hi
                                     for (_,bar),(lo,hi) in zip(bars,windows))
        counts.append({'family':family,'detected':len(bars),'expected':len(labels),
                       'matched':count_ok,'source_identities_matched':identity_ok})
        for i,value in enumerate(reference[key]):
            identifier=f'{family}:{labels[i]}-{labels[i+1]}'
            truth[identifier]=value*.0254
        if not identity_ok:
            continue  # Never hide surplus/missing bars by selecting a subset.
        for label,(original_index,bar) in zip(labels,bars):
            assignments.append({'family':family,'source_label':label,'candidate_index':original_index,
                                'start':bar['start'],'end':bar['end'],
                                'anchor_basis':reference['anchor_evidence']})
        lookup={tuple(s['bars']):s['centreline_m'] for s in report['spacing']}
        for i,((ai,a),(bi,b)) in enumerate(zip(bars,bars[1:])):
            identifier=f'{family}:{labels[i]}-{labels[i+1]}'
            measured[identifier]=lookup.get(tuple(sorted([ai,bi])))
            matches.append({'reference_id':identifier,'measurement_id':identifier,'verified':True,
                            'anchor_evidence':'Manual asymmetric-outline registration to report Fig14, physical RB labels in source 1-5.png/A-C.png; hashes in reference manifest'})
    result=compare_cell_pairs(truth,measured,matches)
    for pair in result['pairs']:
        pair['reference_m']=truth[pair['reference_id']]
        pair['measured_m']=measured[pair['measurement_id']]
        pair['reference_display_increment_m']=.000254 if pair['reference_id']=='Y:G-H' else .00254
    return {'counts':counts,'line_assignments':assignments,'spacing_assessment':result,
            'crosswalk_basis':'Manually reviewed asymmetric shape and physically labeled photos; not a best-error permutation',
            'tolerance_verdict':'No field compliance decision. Published tape rounding and scanner error remain.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--sensitivity',action='store_true',help='Also run other fixed seeds/noise allowances; report every result')
    args=parser.parse_args()
    ref_path=Path(__file__).parents[1]/'docs/data/wingwall_reference.json'
    reference=json.loads(ref_path.read_text())
    # Anchors are source data, not arbitrary caller-provided verification text.
    for item in reference['files']:
        path=args.data_dir/item['name']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Missing or modified source/anchor file: '+item['name'])
    runs,protocol=detect(args.data_dir/'small_rebar_4M.mat')
    summary=assess(runs,reference)
    result={'reference':reference,'protocol':protocol,**summary,'runs':runs,'production_modified':False,
            'reference_sha256':hashlib.sha256(ref_path.read_bytes()).hexdigest()}
    result['sensitivity']=[]
    if args.sensitivity:
        for seed,noise in [(456,.02),(123,.015),(123,.025)]:
            other,meta=detect(args.data_dir/'small_rebar_4M.mat',seed,noise)
            result['sensitivity'].append({'seed':seed,'scan_noise_m':noise,**assess(other,reference)})
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'trial.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('Counts:',summary['counts'])
    print('Verified reference intervals:',summary['spacing_assessment']['scored_cells'])
    value=summary['spacing_assessment']['spacing_mae_m']
    print('MAE mm:',value*1000 if value is not None else None)
    value=summary['spacing_assessment']['spacing_max_abs_error_m']
    print('Max error mm:',value*1000 if value is not None else None)
    for row in result['sensitivity']:
        print('Sensitivity',row['seed'],row['scan_noise_m'],row['counts'],row['spacing_assessment']['scored_cells'])


if __name__=='__main__':
    main()
