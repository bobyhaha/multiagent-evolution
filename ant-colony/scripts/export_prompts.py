"""Export actual recorded prompts, or build a no-inference ProgramBench preview."""

import argparse
from dataclasses import replace
import json
from pathlib import Path
import tempfile

from ant_colony.config import ColonyConfig
from ant_colony.context import request_size
from ant_colony.engine import ColonyMAS
from ant_colony.programbench import ProgramBenchWorkbench
from ant_colony.providers import OpenRouterProvider
from ant_colony.structured import response_format
from ant_colony.work_contracts import RULES as CONTRACT_RULES, REVIEW_RULES
from run_programbench_campaign import build_task


def save_prompt(out, name, messages):
    (out / (name + '.txt')).write_text('\n\n'.join(
        message['role'].upper() + '\n' + message['content'] for message in messages) + '\n')
    (out / (name + '.json')).write_text(json.dumps(
        {'messages': messages, 'response_format': response_format(messages)}, indent=2) + '\n')
    return {'name': name, 'request_bytes_including_schema': request_size(messages)}


def preview(args, out):
    cfg = ColonyConfig.from_dict(json.loads(args.config.read_text()))
    cfg = replace(cfg, initial_bank=int(args.max_usd * cfg.credits_per_usd))
    models = json.loads(args.models.read_text())
    # This callback records request construction; it never invokes the provider.
    captured = []
    with tempfile.TemporaryDirectory(prefix='colony-prompt-preview-') as temp:
        bench = ProgramBenchWorkbench(args.task, Path(temp) / 'coding', args.evaluator_python,
                                      output_bytes=cfg.coding_output_bytes)
        provider = OpenRouterProvider(models, args.max_usd, lambda *a, **kw: None)
        c = ColonyMAS(cfg, build_task(bench, cfg), provider, workbench=bench)
        c.round = 1
        def capture(model, messages, **kwargs):
            captured.append(messages)
            return None
        c.call = capture
        c.fund([], planning=True)
        c.discover()
        root = next(iter(c.agents.values()))
        c.board.replace([{'id': 'implementation', 'title': 'Implementation',
                          'scope': 'Implement the documented behavior in the shared source.',
                          'acceptance': 'Build and verify behavior against public documentation and evidence.'}])
        c.grant(root, min(cfg.max_grant, cfg.initial_bank // 2), task_id='implementation')
        for phase in ('application', 'formation', 'review', 'work'):
            captured.append(c.observation(root, phase)[0])
        source = bench.hashes(bench.source(root.team))
        output = next(iter(source), 'compile.sh')
        if cfg.work_contracts:
            c.declare_contract(root, {'replaces': '', 'objective': 'Implement documented command behavior',
                'inputs': [], 'outputs': [output], 'checks': ['sh compile.sh && ./executable --help'],
                'acceptance': 'Build and help command match the documented interface; broader behavior remains to verify.',
                'stop_when': 'Report verified coverage or a concrete blocker; do not claim untested behavior.'})
            captured.append(c.observation(root, 'work')[0])
        if cfg.runtime_control:
            child = next(a for a in c.agents.values() if a.name != root.name)
            c.phase = 'formation'
            c.hire(root, child, c.working_minimum(child.model), 'Independent public behavior verification')
            child.wake_round = 10
            c.round = 2
            c.recover_controls()
    seen, manifest = {}, []
    for messages in captured:
        phase = json.loads(messages[-1]['content'])['phase']
        index = seen.get(phase, 0) + 1
        seen[phase] = index
        manifest.append(save_prompt(out, f'preview-{phase}-{index}', messages))
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--events', type=Path)
    p.add_argument('--config', type=Path)
    p.add_argument('--models', type=Path)
    p.add_argument('--task', type=Path)
    p.add_argument('--evaluator-python', type=Path)
    p.add_argument('--max-usd', type=float, default=100)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'work-contract-rules.txt').write_text(CONTRACT_RULES.strip() + '\n')
    (args.out / 'handoff-review-rules.txt').write_text(REVIEW_RULES.strip() + '\n')
    if args.events:
        # Export every distinct system prompt and the first full request using
        # it, with its exact response schema. No secrets are read from the host.
        seen, manifest = set(), []
        for line in args.events.open():
            event = json.loads(line)
            if event['event'] != 'call_reserved':
                continue
            messages = event['messages']
            key = (event['kind'], messages[0]['content'])
            if key in seen:
                continue
            seen.add(key)
            name = f"recorded-{event['kind']}-{event['call_id']}"
            manifest.append(save_prompt(args.out, name, messages) | {'call_id': event['call_id']})
        origin = 'actual recorded requests'
    else:
        if not all((args.config, args.models, args.task, args.evaluator_python)):
            p.error('Preview requires --config, --models, --task and --evaluator-python')
        manifest = preview(args, args.out)
        origin = 'offline preview using production prompt builders; illustrative state, no inference'
    (args.out / 'manifest.json').write_text(json.dumps({'origin': origin, 'prompts': manifest}, indent=2) + '\n')
    print(json.dumps({'origin': origin, 'prompts': len(manifest), 'directory': str(args.out.resolve())}))


if __name__ == '__main__':
    main()
