#!/usr/bin/env python3
"""Compare real schema validity, citations and latency with thinking on and off."""
import asyncio
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.model_gate import fixture
from app.ai.router import ModelRouter
from app.ai.validate import validate_ids

async def main():
    router=ModelRouter();await router.probe();results=[]
    if not router.status['hero']['healthy']:raise RuntimeError('Hero must be healthy')
    try:
        for role in ['identity','email','endpoint','data_access','lead','twist_check','card_polish','overdrive']:
            payload,schema,allowed=fixture(role if role in ('identity','email','endpoint','data_access','lead') else 'twist_check')
            for thinking in [False,True]:
                at=time.monotonic();usage=[]
                try:
                    result,meta=await router.clients['hero'].complete(role,payload,schema,lambda n,r:usage.append(r),reasoning=thinking)
                    value=validate_ids(result,allowed)
                    row={'role':role,'thinking':thinking,'valid':True,'latency_seconds':time.monotonic()-at,'usage':usage,'result':value}
                except Exception as exc:
                    row={'role':role,'thinking':thinking,'valid':False,'latency_seconds':time.monotonic()-at,'error':str(exc)}
                results.append(row);print(json.dumps(row),flush=True)
        Path('runtime/reasoning-benchmark.json').write_text(json.dumps(results,indent=2))
    finally:await router.close()
if __name__=='__main__':asyncio.run(main())
