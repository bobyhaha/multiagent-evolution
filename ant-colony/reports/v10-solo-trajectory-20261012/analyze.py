import json, collections, hashlib
from decimal import Decimal
from pathlib import Path
from programbench.eval.eval import EvaluationResult
from programbench.utils.load_data import load_all_instances, get_active_branches, get_ignored_tests
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
PATHS={'V10':ROOT/'runs/programbench-astra40-quality-first-high-20261011-v10/v10-all-astra40-quality-first-xsv', 'solo':ROOT/'runs/programbench-mixed-high-20261010/solo-xsv'}
inst=next(x for x in load_all_instances(include_tests=True) if x['instance_id']=='burntsushi__xsv.f430466')
allstats={}; maps={}
for name,p in PATHS.items():
 rows=[json.loads(l) for l in (p/'events.jsonl').open()]; calls=[x for x in rows if x['event']=='call']; tools=[x for x in rows if x['event']=='coding_tool']; rounds={}; invalid_cost=Decimal(0); lastcall={}; invalid=[]
 for x in rows:
  if x['event']=='call': lastcall[x['actor']]=x
  if x['event']=='invalid_reply':
   c=lastcall.get(x['actor']); invalid.append({**x,'call_id':c['call_id'] if c else None,'cost_usd':c['cost_usd'] if c else None}); invalid_cost+=Decimal(c['cost_usd']) if c else 0
 for rd in range(1,max(x.get('round',0) for x in rows)+1):
  cs=[x for x in calls if x.get('round')==rd]; ts=[x for x in tools if x.get('round')==rd]; integrations=[x for x in rows if x.get('round')==rd and x['event']=='checkpoint_integrated']; checks=[{k:v for k,v in x.items() if k in ('passed','total','build','version','status')} for x in rows if x.get('round')==rd and x['event']=='checkpoint_test']; rounds[rd]={'calls':len(cs),'cost':float(sum(Decimal(x['cost_usd']) for x in cs)),'work_calls':sum(x['kind']=='work' for x in cs),'tools':len(ts),'nonzero_exec':sum(x['kind']=='exec' and x['result'].get('exit_code',0)!=0 for x in ts),'truncated_tools':sum(x['result'].get('output_truncated',False) for x in ts),'writes':[(x['agent'],x['path']) for x in rows if x['event']=='source_written' and x.get('round')==rd],'integrated_paths':[f for x in integrations for f in x['paths']],'public_checks':checks}
 phase={k:{'calls':sum(x['kind']==k for x in calls),'cost':float(sum(Decimal(x['cost_usd']) for x in calls if x['kind']==k))} for k in sorted({x['kind'] for x in calls})}
 stats={'phase':phase,'calls':len(calls),'input_tokens':sum(x.get('input_tokens',0) for x in calls),'output_tokens':sum(x.get('output_tokens',0) for x in calls),'invalid_replies':invalid,'invalid_reply_cost':str(invalid_cost),'tool_kinds':dict(collections.Counter(x['kind'] for x in tools)),'rounds':rounds,'failed_tools':[{'seq':x['seq'],'round':x['round'],'agent':x['agent'],'kind':x['kind'],'exit_code':x['result'].get('exit_code'),'status':x['result'].get('status'),'command':x['result'].get('command','')[:240],'output_tail':x['result'].get('output','')[-700:]} for x in tools if x['kind']=='exec' and x['result'].get('exit_code',0)!=0]}
 allstats[name]=stats
 result=EvaluationResult.model_validate_json((p/'coding/submission/burntsushi__xsv.f430466/burntsushi__xsv.f430466.eval.json').read_text()).for_branches(get_active_branches(inst)).without_ignored(get_ignored_tests(inst)); maps[name]={(t.branch,t.name):t for t in result.test_results}; assert len(maps[name])==len(result.test_results)
common=maps['V10'].keys()&maps['solo'].keys(); groups=collections.defaultdict(lambda:collections.Counter()); paired=[]
for k in sorted(common):
 a,b=maps['V10'][k],maps['solo'][k]; modules=[v for v in a.name.split('[',1)[0].split('.')[:-1] if v.startswith('test_')]; group=modules[-1] if modules else a.name.split('.')[0]; c=groups[group];c['total']+=1;c['V10']+=a.is_resolved;c['solo']+=b.is_resolved;c['both_fail']+=not a.is_resolved and not b.is_resolved
 if a.is_resolved!=b.is_resolved: paired.append({'branch':k[0],'name':k[1],'group':group,'V10':a.status,'solo':b.status})
summary={'trajectories':allstats,'common_test_count':len(common),'test_groups':dict(groups),'paired_disagreements':paired,'method':'Read-only historical analysis. Hidden terminal results never fed to live agents. Each test keyed by branch and name after upstream active/ignore filters. No inference or evaluation reruns.'}
(OUT/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
for name,s in allstats.items():
 print(name,{k:s[k] for k in ('phase','calls','input_tokens','output_tokens','invalid_reply_cost','tool_kinds')});print('failed_tools',len(s['failed_tools']))
 print('timeline',[(k,v['calls'],round(v['cost'],2),v['nonzero_exec'],v['integrated_paths'],v['public_checks']) for k,v in s['rounds'].items() if v['calls'] or v['integrated_paths']])
print('test_groups',json.dumps(dict(groups),indent=2));print('DISAGREEMENTS',paired[:6])
