# SPDX-License-Identifier: GPL-3.0-or-later
"""Fetch selected CC BY 4.0 source/anchor members; execute no archive contents.

Files are checked by ZIP CRC/size and committed SHA-256. Only selected byte
ranges are transferred; no executable or unrelated nested archive is fetched.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

URL='https://zenodo.org/api/records/4273237/files/Data-20201114T023951Z-001.zip/content'
MEMBERS={
 'small_rebar_4M.mat':(216187323,50909736,50911265,394429367),
 '1-5.png':(17071453,4486923,4486238,3080943787),
 'A-C.png':(30202024,4305637,4304977,654368755),
 'drawing.PNG':(34507898,38624,38614,1417280735),
}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    reference=json.loads((Path(__file__).parents[1]/'docs/data/wingwall_reference.json').read_text())
    for item in reference['files']:
        name=item['name'];path=args.output_dir/name
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']:
            print('Verified cached',name,flush=True);continue
        if name=='report.pdf':
            subprocess.run(['curl','-fsSL','--max-time','60',reference['report_url'],'-o',str(path)],check=True)
        else:
            offset,compressed,size,crc=MEMBERS[name];total=compressed+4095;chunk=2*1024*1024
            parts=args.output_dir/(name+'.parts');parts.mkdir(exist_ok=True)
            def fetch(start):
                take=min(chunk,total-start);part=parts/str(start)
                if part.exists() and part.stat().st_size==take:return part
                for _ in range(3):
                    result=subprocess.run(['curl','-fsSL','--max-time','40','-r',
                        f'{offset+start}-{offset+start+take-1}',URL,'-o',str(part),'-w','%{http_code}'],capture_output=True,text=True)
                    if result.returncode==0 and result.stdout=='206' and part.stat().st_size==take:return part
                raise RuntimeError('Range transfer failed; rerun to resume: '+name)
            with ThreadPoolExecutor(max_workers=3) as pool:
                files=list(pool.map(fetch,range(0,total,chunk)))
            data=b''.join(p.read_bytes() for p in files)
            h=struct.unpack_from('<4s5H3I2H',data)
            if h[0]!=b'PK\x03\x04':raise ValueError('Expected ZIP member header')
            start=30+h[-2]+h[-1];payload=data[start:start+compressed]
            raw=zlib.decompress(payload,-15) if h[3]==8 else payload
            if len(raw)!=size or zlib.crc32(raw)!=crc:raise ValueError('ZIP CRC/size mismatch')
            path.write_bytes(raw)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Source hash mismatch; do not use as reference: '+name)
        print('Verified',name,flush=True)
    (args.output_dir/'source-manifest.json').write_text(json.dumps(reference['files'],indent=2)+'\n')


if __name__=='__main__':
    main()
