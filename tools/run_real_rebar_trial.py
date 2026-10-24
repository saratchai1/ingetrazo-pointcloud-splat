# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline, explicitly guided trial; never opens or edits a running CAD document.

Download the two public PLY ZIP members described in docs/REAL_REBAR_TRIAL.md.
Run with --data-dir pointing to them and --output-dir to a disposable folder.
This benchmark uses provisional specimen counts, not registered per-bay truth.
"""
import argparse
from pathlib import Path
import json
import numpy as np
from scipy.spatial.transform import Rotation
from pointcloud_splat.data_models import PointCloudDataset
from pointcloud_splat.rebar import inspect
from pointcloud_splat.reference_validation import compare_reference


def read_ascii_ply(path):
    with path.open() as stream:
        header=[]
        while True:
            line=stream.readline()
            if not line:
                raise ValueError('Truncated PLY header')
            header.append(line.strip())
            if line.strip()=='end_header':
                break
        if 'format ascii 1.0' not in header:
            raise ValueError('Trial reader supports ASCII PLY only')
        count=int(next(s.split()[-1] for s in header if s.startswith('element vertex ')))
        values=np.loadtxt(stream,max_rows=count)
    if values.shape != (count,6):
        raise ValueError('Expected original XYZ RGB PLY records')
    valid=np.isfinite(values[:,:3]).all(axis=1)&np.any(values[:,:3]!=0,axis=1)
    return values[valid,:3]/1000.,values[valid,3:].astype(np.uint8),np.flatnonzero(valid)


def geometry_directions(points):
    rng=np.random.default_rng(123)
    sample=points[rng.choice(len(points),min(3000,len(points)),replace=False)]
    directions=[]
    for family in range(2):
        bestmask=None;support=0
        for _ in range(1000):
            a,b=sample[rng.choice(len(sample),2,replace=False)]
            v=b-a;length=np.linalg.norm(v)
            if length<.25:
                continue
            v/=length
            if abs(v[2])>.25 or (family and abs(v@directions[0])>.2):
                continue
            inside=np.linalg.norm(np.cross(sample-a,v),axis=1)<.008
            if inside.sum()>support:
                bestmask=inside;support=int(inside.sum())
        if bestmask is None:
            continue
        chosen=sample[bestmask]
        _,_,axes=np.linalg.svd(chosen-chosen.mean(0),full_matrices=False)
        directions.append(axes[0])
    return directions


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--layer-mode', choices=['roi', 'dominant'], default='roi',
                        help='Optional dominant depth-band selection inside the existing guided ROI')
    args=parser.parse_args()
    reference=json.loads((Path(__file__).parents[1]/'docs/data/real_rebar_reference.json').read_text())
    results=[];args.output_dir.mkdir(parents=True,exist_ok=True)
    for name,low,high,angle in [('drone-t1',[-.07,-.3,1.85],[.57,.4,2.2],-7),
                                ('drone-t8',[-.03,-.6,.80],[.68,.14,1.12],-9)]:
        path=args.data_dir/(name+'.ply')
        points,rgb,ids=read_ascii_ply(path)
        mask=np.all((points>=low)&(points<=high),axis=1)
        points,rgb,ids=points[mask],rgb[mask],ids[mask]
        _,_,axes=np.linalg.svd(points-points.mean(0),full_matrices=False)
        normal=axes[-1]*np.sign(axes[-1,2]);centre=points.mean(0)
        base=np.array([np.cos(np.radians(angle)),np.sin(np.radians(angle))])
        u=np.r_[base,-normal[:2]@base/normal[2]];u/=np.linalg.norm(u)
        u-=np.dot(u,normal)*normal;u/=np.linalg.norm(u)
        rotation=np.array([u,np.cross(normal,u),normal])
        local=(points-centre)@rotation.T
        roi_low=local.min(0);roi_high=local.max(0)
        roi_low[2]=-.14;roi_high[2]=-.075
        layer_mask=np.all((local>=roi_low)&(local<=roi_high),axis=1)
        directions=geometry_directions(local[layer_mask])
        # Keep original source geometry/record indices; express the inspection in
        # the rigid scan-local frame using the same transform as the application.
        ds=PointCloudDataset(name,str(path),points,np.column_stack([rgb,np.full(len(rgb),255,dtype=np.uint8)]))
        ds.coordinate_frame={'source_units':'mm','unit_to_m':.001,'source_origin':[0.,0.,0.]}
        ds.source_point_indices=ids
        ds.pivot=np.zeros(3)
        ds.rotation_x_deg,ds.rotation_y_deg,ds.rotation_z_deg=Rotation.from_matrix(rotation).as_euler('xyz',degrees=True)
        ds.offset=-centre@rotation.T
        for family,direction in enumerate(directions):
            report=inspect(ds,roi_low,roi_high,direction,diameter_m=.015875,
                           layer_normal=[0,0,1] if args.layer_mode=='dominant' else None)
            ref_key='horizontal_midbay_spacing_mm' if family==0 else 'vertical_midbay_spacing_mm'
            assessment=compare_reference(len(report['bars']),5,[],np.asarray(reference[ref_key]).ravel()/1000,
                                         correspondence_verified=False)
            record={'scan':name,'family':family+1,'layer_points':int(layer_mask.sum()),
                    'rotation':rotation.tolist(),'centre_m':centre.tolist(),'assessment':assessment,'report':report}
            results.append(record)
            print(name,'family',family+1,'detected',len(report['bars']),'expected 5',flush=True)
    (args.output_dir/'trial.json').write_text(json.dumps({'reference':reference,'runs':results},indent=2))


if __name__=='__main__':
    main()
