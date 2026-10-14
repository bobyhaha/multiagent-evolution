import json
from pathlib import Path
from collections import Counter
from ant_colony.campaign_budget import Ledger
root=Path('runs/programbench-astra10-work-contracts-high-20261012-v18/v18-astra10-work-contracts-xsv')
events=[]
for line in (root/'events.jsonl').read_text().splitlines():
 try: events.append(json.loads(line))
 except json.JSONDecodeError: pass
counts=Counter(e['event'] for e in events)
account=Ledger('runs/programbench-mixed-high-20261010/campaign.sqlite',parallel=True).summary(root.name)
snap=next((e['state'] for e in reversed(events) if e['event']=='snapshot'),None)
selected=('call','invalid_reply','reply_recovered','action_rejected','review_rejected','work_contract_created','work_contract_receipt','work_contract_handoff','work_contract_reviewed','work_contract_invalidated','hire','stopped')
status={'round':max(e.get('round',0) for e in events),'counts':{k:counts[k] for k in selected},'accounting':account,'last_event':events[-1]['event'],'last_call':next(({k:e.get(k) for k in ('actor','kind','round')} for e in reversed(events) if e['event']=='call_reserved'),None),'snapshot_round':snap['round'] if snap else None,'teams':len(snap['teams']) if snap else None}
notable=[{k:e[k] for k in ('event','round','actor','agent','action','reason','decision','worker','contract_id','status','exit_code','passed') if k in e} for e in events if e['event'] in {'invalid_reply','action_rejected','work_contract_receipt','work_contract_handoff','work_contract_reviewed','stopped','runner_error'}][-6:]
status['recent_notable']=notable
status['phase']=events[-1].get('phase')
status['coding_tools']=dict(Counter(e.get('kind') for e in events if e['event']=='coding_tool'))
status['changed_paths']=sorted({p for e in events if e['event']=='coding_tool' for p in e.get('result',{}).get('changed',[])})
status['public_checkpoint']=next(({k:e.get(k) for k in ('version','status','passed','total')} for e in reversed(events) if e['event']=='checkpoint_test'),None)
status['experiment_settled_usd']=round(account['reported_usd']+3.849748,6)
status['experiment_accounted_usd']=round(account['accounted_usd']+3.849748,6)
if (root/'report.json').exists(): status['report']=json.loads((root/'report.json').read_text())
Path('reports/work-contracts-astra10-20261012/live-status.json').write_text(json.dumps(status,indent=2)+'\n')
display=dict(status)
if 'report' in display:
 display['report']={k:display['report'].get(k) for k in ('status','rounds','score','calls','api_usd','stop_reason','error')}
print(json.dumps(display,indent=2))
