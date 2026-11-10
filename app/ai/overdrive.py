"""Real additional independent model reviews, bounded to one per team per model."""
import asyncio
from .twist_check import review

async def run(router,teams,session,on_result):
    models=router.lineup(session['label']=='REHEARSAL')
    async def one(team,key):
        try:
            result=await review(router,team,session,key)
            await on_result(team,result)
        except Exception as exc:
            await on_result(team,{'error':str(exc)[:160],'requested_model':key})
    await asyncio.gather(*(one(t,k) for t in teams if t.get('decision') for k in models))
