"""Zero-API regressions for the v18 liquidity, evidence and finish failures."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from ant_colony.context import request_size
from ant_colony.structured import response_format
from test_mechanism import engine, funded, Policy
from test_work_contracts import colony, spec, check, handoff, accept
from test_programbench import fixture


def stranded(policy=None):
    c = engine(policy, initial_agents=1, runtime_control=True, max_output_tokens=2000,
               control_max_output_tokens=100, control_context_bytes=24000)
    root = funded(c, value=15000)
    child = c.new_agent('worker', 'implementation', root, 2500, 'Keep this scope')
    # Spend genuine credits until both shares are below the work reservation.
    c.charge(root, root.team, c.rights(root)-1200, "fixture spending")
    c.charge(child, child.team, c.rights(child)-1200, "fixture spending")
    c.round = 2
    return c, root, child


def test_stranded_funds_reclaimed_by_smaller_paid_call_preserve_scope():
    c, root, child = stranded(Policy(lambda obs: {'allocate': [{'agent': 'a0002', 'amount': -1000}]}))
    wealth = c.ledger.wealth
    c.recover_controls()
    assert c.calls == 1 and c.ledger.wealth == wealth-5
    assert c.rights(root) == 2195 and c.rights(child) == 200
    assert child.assignment == 'Keep this scope' and child.parent == root.name
    assert c.provider.observations[0]['phase'] == 'control'
    c.check()


def test_no_status_only_control_polling_until_relevant_state_changes():
    c, root, child = stranded()
    c.recover_controls()
    c.round += 1
    c.recover_controls()
    assert c.calls == 1
    c.teams[root.team].allowances[child.name] -= 1
    c.teams[root.team].allowances[root.name] += 1
    c.recover_controls()
    assert c.calls == 2


def test_control_allocation_batch_is_atomic_and_retains_reserve():
    c, root, child = stranded()
    original = c.teams[root.team].allowances.copy()
    with pytest.raises(ValueError):
        c.allocate(root, [{'agent': child.name, 'amount': -500}, {'agent': 'intruder', 'amount': 1}])
    assert c.teams[root.team].allowances == original
    with pytest.raises(ValueError, match='control reserve'):
        c.allocate(root, [{'agent': child.name, 'amount': 1150}])
    assert c.teams[root.team].allowances == original


def test_ancestor_routes_to_sleeping_executor_without_manager_call():
    c = engine(Policy(lambda obs: {'route': [{'to': 'a0003', 'text': 'Verify the assigned outcome'}]}),
               initial_agents=1, runtime_control=True)
    root = funded(c)
    parent = c.new_agent('worker', 'manager', root, 5000, 'Own subproject')
    worker = c.new_agent('worker', 'execute', parent, 2000, 'Verify component')
    c.charge(parent, parent.team, c.rights(parent), "fixture spending")
    worker.wake_round = 42
    c.round = 22
    c.recover_controls()
    assert worker.wake_round == 22 and worker.inbox[-1]['from'] == root.name
    assert c.calls == 1 and worker.assignment == 'Verify component'
    assert c.rights(parent) == 0
    with pytest.raises(ValueError):
        c.route_control(worker, [{'to': root.name, 'text': 'unauthorized'}])


def test_cancel_pending_proposal_during_cooldown_prevents_automatic_requeue():
    c, root, _ = stranded()
    c.config = replace(c.config, funding_recovery=True)
    c.record_proposal(root, {'amount': 3000, 'plan': 'obsolete need'}, 'bank')
    root.funding_retry_round = 99
    c.cancel_proposal(root, True)
    c.round = 100
    c.queue_funding_recovery([root])
    assert root.application is None
    c.record_proposal(root, {'amount': 3000, 'plan': 'new concrete work'}, 'bank')
    assert not root.recovery_paused and root.application['status'] == 'pending'
    assert c.minimum_grant(root) == 2800  # two work calls minus existing rights


def test_host_reports_preserve_contract_receipts_but_real_edits_invalidate(tmp_path):
    c, a = colony(tmp_path)
    c.declare_contract(a, spec())
    check(c, a)
    handoff(c, a)
    accept(c, a)
    fingerprint = c.artifact_state(a)[1]
    result = c.execute_contract_tool(a, {'kind': 'record', 'content': 'Report the known check without source writes.'})
    assert result['status'] == 'agent_note' and c.artifact_state(a)[1] == fingerprint
    assert not c.contract_reasons(c.work_contracts[a.name], evidence=True)
    (c.workbench.source(a.team) / 'pkg/a.py').write_text('def value(): return 43\n')
    assert c.contract_reasons(c.work_contracts[a.name], evidence=True)


def test_temporary_stdout_recovers_from_host_after_more_calls_without_reexecution(tmp_path):
    bench, a = fixture(tmp_path)
    calls = []
    def execute(agent, action):
        calls.append(action)
        return {'status': 'ok', 'exit_code': 1, 'output': '\n'.join(f'failure-{n}' for n in range(500)),
                'output_truncated': False, 'changed_count': 0}
    bench.execute_command = execute
    result = bench.execute(a, {'kind': 'exec', 'command': 'produce /tmp/report; cat /tmp/report'})
    identifier = result['artifact']
    before = bench.hashes(bench.source(a.team))
    bench.execute(a, {'kind': 'list'})
    bench.execute(a, {'kind': 'record', 'content': '500 diagnostic lines; strict failure remains.'})
    text, start = '', 1
    while start:
        page = bench.execute(a, {'kind': 'read_result', 'path': identifier, 'start': start, 'lines': 60})
        text += page['text']
        start = page['next_start']
    assert 'failure-499' in text and len(calls) == 1
    assert bench.evidence_summary(a)['exit_code'] == 1
    assert bench.hashes(bench.source(a.team)) == before
    with pytest.raises(ValueError):
        bench.read_evidence(SimpleNamespace(name='other', team='other'), {'path': identifier})
    with pytest.raises(ValueError):
        bench.read_evidence(a, {'path': '../submission/hidden.json'})


def test_incomplete_selection_does_not_claim_verified_finish(tmp_path):
    c, a = colony(tmp_path, bank_finalization=True, runtime_control=True)
    c.finalize_society('complete')
    assert c.final_answer is None
    c.select_incomplete_checkpoint('Cannot complete remaining strict checks with available execution rights')
    assert c.submission_mode == 'bank_selected_incomplete_checkpoint'
    assert c.final_author == '__public__' and not c.teams[a.team].ready
    assert c.events[-1]['verified_complete'] is False


def test_control_actual_output_and_context_caps_are_smaller_and_valid():
    c, root, _ = stranded()
    seen = []
    complete = c.provider.complete
    def capture(model, messages, max_tokens, call_id):
        seen.append((max_tokens, request_size(messages), response_format(messages)))
        return complete(model, messages, max_tokens, call_id)
    c.provider.complete = capture
    c.recover_controls()
    assert seen[0][0] == 100 and seen[0][1] <= 24000
    assert seen[0][2]['json_schema']['strict']


def test_underfunded_manager_does_not_burn_control_reserve_in_work_call():
    c, root, child = stranded()
    c.allocate(root, [{'agent': child.name, 'amount': -800}])
    assert c.rights(root) == c.call_budget(root.model)
    assert c.ask(root, 'work') == {} and c.calls == 0


def test_runtime_control_flag_reaches_frozen_experiment_config(monkeypatch):
    from test_colony40_plan import module
    from test_programbench import config
    cfg = module(monkeypatch).experiment_config(config().to_dict(), model_mix='all-astra',
                                                total_agents=10, max_total_agents=10,
                                                work_contracts=True, runtime_control=True)
    assert cfg['runtime_control'] and cfg['initial_agents'] == cfg['max_agents'] == 9


def test_incomplete_selection_freezes_checkpoint_before_evaluation(tmp_path, monkeypatch):
    c, _ = colony(tmp_path, bank_finalization=True, runtime_control=True, max_rounds=1)
    c.formation = lambda: []
    c.fund = lambda *args, **kwargs: c.select_incomplete_checkpoint('Remaining strict failures; select incomplete')
    def forbidden(*args, **kwargs):
        raise AssertionError('Selected checkpoint must not change')
    c.workbench.finish_round = forbidden
    monkeypatch.setattr("ant_colony.engine.evaluate", lambda *args: 0.0)
    c.run()
    assert c.submission_mode == 'bank_selected_incomplete_checkpoint'
