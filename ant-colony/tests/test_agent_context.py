from copy import deepcopy
import json

import pytest

from ant_colony.context import build_agent_context, build_context, request_size


def test_agent_previews_fit_without_changing_contracts_or_evidence_status():
    offer = {'agent': 'a1', 'amount': 12.5, 'target': 't2', 'expires': 4,
             'plan': '測試' * 500, 'reason': 'r' * 1000}
    required = {
        'assignment': 'Keep this complete', 'proposals': [{'plan': 'Full proposal', 'amount': 23}],
        'allowance': 40, 'parent': 'a0', 'work_authorized': True,
        'recruitment': {'introductions': [offer]}, 'collaboration_offers': [deepcopy(offer)],
        'verified_progress': {'last_test': {'passed': 1, 'total': 2, 'failures': [
            {'probe': 'p1', 'status': 'failed', 'exit_code': 1, 'expected': 'x' * 4000}]},
            'recent_executions': [{'command': 'cmd' * 1000, 'output': 'error' * 1000,
                                   'exit_code': 2, 'revision': 7}]},
        'shared_scratchpad': [{'id': 'e1', 'status': 'unverified', 'text': 'x' * 2000}],
    }
    before = deepcopy(required)
    with pytest.raises(ValueError):
        build_context('Work', required, [], 3500)
    messages, dropped = build_agent_context('Work', required, [], 3500)
    obs = json.loads(messages[-1]['content'])
    assert request_size(messages) <= 3500 and dropped > 0
    for key in ('assignment', 'proposals', 'allowance', 'parent', 'work_authorized'):
        assert obs[key] == required[key]
    for key in ('amount', 'target', 'expires', 'agent'):
        assert obs['collaboration_offers'][0][key] == offer[key]
    progress = obs['verified_progress']
    assert progress['last_test']['passed'] == 1
    assert progress['last_test']['failures'] == [
        {'probe': 'p1', 'status': 'failed', 'exit_code': 1, 'details_optional': True}]
    assert progress['recent_executions'][0]['exit_code'] == 2
    assert progress['recent_executions'][0]['revision'] == 7
    assert obs['shared_scratchpad'][0]['status'] == 'unverified'
    assert required == before


def test_fitting_agent_context_is_unchanged():
    required = {'collaboration_offers': [{'plan': 'x' * 500}]}
    assert build_agent_context('s', required, [], 5000) == build_context('s', required, [], 5000)


def test_essential_contract_overflow_still_fails():
    with pytest.raises(ValueError, match='Required context'):
        build_agent_context('s', {'assignment': 'x' * 5000, 'proposals': [{'amount': 12}]}, [], 1000)


def test_action_rejection_survives_crowded_context_is_private_and_clears_on_success():
    from test_quality_first import colony

    c = colony()
    agent, peer = list(c.agents.values())[:2]
    c.grant(agent, 15_000_000)
    c.phase = 'work'

    def rejected():
        raise ValueError('Probe capture allows at most 12 paths; received 18')

    assert not c.attempt(agent, 'tool', rejected)
    # Reproduce the case where the normal runtime inbox message was crowded out.
    agent.inbox = [{'from': peer.name, 'text': 'status ' * 2000}] * 20
    agent.memory = 'large old context ' * 5000
    messages, dropped = c.observation(agent, 'work')
    obs = json.loads(messages[-1]['content'])
    assert dropped > 0
    assert obs['last_action_errors'] == [{'action': 'tool',
        'reason': 'Probe capture allows at most 12 paths; received 18', 'round': 1, 'phase': 'work'}]
    peer_messages, _ = c.observation(peer, 'formation')
    assert 'last_action_errors' not in json.loads(peer_messages[-1]['content'])
    assert c.attempt(agent, 'messages', lambda: None)
    assert agent.name in c.action_errors
    assert c.attempt(agent, 'tool', lambda: None)
    messages, _ = c.observation(agent, 'work')
    assert 'last_action_errors' not in json.loads(messages[-1]['content'])


def test_action_rejection_context_is_bounded_and_deduplicated():
    from test_quality_first import colony

    c = colony()
    agent = next(iter(c.agents.values()))

    def rejected():
        raise ValueError('x' * 10000)

    for action in ['tool', 'handoff', 'allocate', 'ready', 'tool']:
        c.attempt(agent, action, rejected)
    rows = c.action_errors[agent.name]
    assert [e['action'] for e in rows] == ['allocate', 'ready', 'tool']
    assert all(len(e['reason'].encode()) <= 300 for e in rows)
