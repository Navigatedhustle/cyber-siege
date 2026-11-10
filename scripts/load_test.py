#!/usr/bin/env python3
"""Record every attempt, even failures. This script never manufactures metrics."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.rehearse import run

async def main(args):
    result=await run(args.teams,True)
    summary={k:v for k,v in result.items() if k not in ('investigations','health_samples','metrics')}
    summary['investigations']=[{k:v for k,v in r.items() if k in ('team','status','duration_seconds','cached','error','model')} for r in result['investigations']]
    summary['peak_5s']=result['metrics']['peak_5s'] if result['metrics'] else None
    summary['peak_at']=result['metrics']['peak_at'] if result['metrics'] else None
    with Path('docs/LOAD_TEST.md').open('a') as stream:
        stream.write('\n## Combined live workload · '+result['started_at']+'\n\n```json\n'+json.dumps(summary,indent=2)+'\n```\n')
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--teams',type=int,default=15);asyncio.run(main(p.parse_args()))
