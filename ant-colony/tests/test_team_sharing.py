"""Offline authorization, information flow and scalability regressions."""

import json
from types import SimpleNamespace

import pytest

from ant_colony.context import byte_size
from ant_colony.quality import rules
from test_quality_first import colony


def teams(**changes):
    c = colony(team_sharing=True, **changes)
    a, b, child, other, free = c.agents.values()
    c.grant(a, 15_000_000)
    c.grant(b, 15_000_000)
    c.phase = "formation"
    c.hire(a, child, 2_000_000, "Own one boundary")
    c.hire(b, other, 2_000_000, "Own another boundary")
    return c, a, b, child, other, free


def post(topic="interface", status="finding", text="Evidence"):
    return dict(topic=topic, status=status, text=text, evidence="CHECKS.md")


def send(c, a, target):
    return c.outbound(a, {"messages": [{"to": target.name, "text": "Evidence"}]}, set(), "work")


def test_direct_messages_local_and_liaison_only_without_fixed_specialist_roles():
    c, a, b, child, other, free = teams()
    assert send(c, a, child) and send(c, child, a)
    assert send(c, a, b)  # Roots are default liaisons.
    assert not send(c, child, other) and not send(c, child, b)
    assert not send(c, free, a)
    c.phase = "formation"
    c.sharing_actions(a, {"liaison": child.name})
    c.sharing_actions(b, {"liaison": other.name})
    assert send(c, child, other)
    assert len(c.team_liaisons(a.team)) == 2
    c.round += c.config.liaison_rounds
    assert not send(c, child, other)
    assert c.team_liaisons(a.team) == [a.name]


def test_nonroot_cannot_appoint_and_retired_liaison_is_not_addressable():
    c, a, b, child, other, free = teams()
    c.phase = "formation"
    c.sharing_actions(child, {"liaison": child.name})
    assert c.team_liaisons(a.team) == [a.name]
    c.sharing_actions(a, {"liaison": child.name})
    child.retired = True
    assert c.team_liaisons(a.team) == [a.name]
    assert not send(c, a, child)


def test_bank_address_no_longer_drops_valid_teammate_delivery():
    c, a, b, child, other, free = teams()
    deliveries = c.outbound(a, {"messages": [
        {"to": "bank", "text": "Integration evidence"},
        {"to": "missing", "text": "Bad address"},
        {"to": child.name, "text": "Read shared interface"},
        {"to": child.name, "text": "Duplicate"},
    ]}, set(), "work")
    c.deliver(deliveries)
    assert len(deliveries) == 1 and child.inbox[-1]["text"] == "Read shared interface"
    assert c.shared_entries[-1]["topic"] == "bank-update"
    assert any(e["event"] == "action_rejected" and "Unknown" in e["reason"] for e in c.events)
    assert any(e["event"] == "action_rejected" and "Duplicate" in e["reason"] for e in c.events)
    assert c.calls == 0  # Routing never secretly purchases inference.


def test_message_volume_cap_still_enforced():
    c, a, *_ = teams()
    with pytest.raises(ValueError, match="Too many"):
        c.outbound(a, {"messages": [{}] * 5}, set(), "work")


def test_shared_append_only_corrections_retrieval_and_no_progress_credit():
    c, a, b, *_ = teams()
    c.append_shared(a, post("parser", "blocker", "Broken quoting"))
    first = dict(c.shared_entries[0])
    c.append_shared(a, post("parser", "resolved", "Quote regression verified"))
    for n in range(50):
        c.append_shared(b, post("topic-" + str(n), text="x" * 4000))
    view = c.shared_view(b.name, "parser quoting")
    assert c.shared_entries[0] == first
    assert view[0]["status"] == "resolved"
    assert len(view) == c.config.scratch_reads
    assert all(len(e["text"].encode()) <= c.config.shared_entry_bytes for e in view)
    assert a.productive_steps == 0 and c.calls == 0


def test_blockers_visible_and_entries_attributed_across_teams():
    c, a, b, *_ = teams()
    c.append_shared(a, post("build", "blocker", "Cannot build; see compiler receipt"))
    c.append_shared(b, post("parser", text="Parser checks pass"))
    view = c.shared_view(b.name, "parser")
    assert view[0]["status"] == "blocker" and view[0]["author"] == a.name
    c.lookup_collaborators(b, "boundary")
    assert all(card["id"] in c.team_liaisons(a.team) or c.agents[card["id"]].team == b.team
               for card in b.directory)


def test_new_actions_survive_full_paid_parse_path_and_context_remains_bounded():
    c = colony(lambda o: {"shared_post": post(), "shared_search": "interface"}, team_sharing=True)
    a = next(iter(c.agents.values()))
    c.grant(a, 15_000_000)
    for n in range(100):
        c.append_shared(a, post(str(n), text="x" * 4000))
    reply = c.ask(a, "work")
    c.remember_and_sleep(a, reply)
    assert a.shared_query == "interface"
    assert len(c.shared_entries) == 101
    for phase in ("formation", "work", "application", "review"):
        messages, _ = c.observation(a, phase)
        obs = json.loads(messages[-1]["content"])
        assert len(obs["shared_scratchpad"]) <= c.config.scratch_reads
        assert byte_size(messages) <= c.context_limit(phase)
        assert "global context" in messages[0]["content"]
    assert not any(e["event"] == "invalid_reply" for e in c.events)


def test_discovery_can_publish_without_money_or_direct_chat():
    c = colony(lambda o: {"shared_post": post(), "offer": {
        "target": "bank", "plan": "Check documented boundaries", "amount": 5_000_000}}, team_sharing=True)
    c.workbench = SimpleNamespace(inspect_public=lambda x: {})
    c.discover()
    assert len(c.shared_entries) == 2 and c.calls == 2
    assert all(a.team is None for a in c.agents.values())
    assert not any(e["event"] == "invalid_reply" for e in c.events)


def test_queue_exceeds_review_batch_without_unbounded_agent_context():
    c = colony(team_sharing=True)
    owner = c.agents['a0001']
    c.grant(owner, 15_000_000)
    for applicant in list(c.agents.values())[1:]:
        c.discovery_offer(applicant, {"target": owner.name, "plan": "Distinct check", "amount": 2_000_000})
    c.check()
    assert len(owner.introductions) == 4
    assert len(c.introduction_views(owner)) == c.config.manager_contacts
    assert len(c.offers_for(owner)) == c.config.manager_contacts
    assert any(e['event'] == 'introduction_queued' for e in c.events)
    assert not any(e['event'] == 'action_rejected' for e in c.events)


def test_stagnation_grace_finishes_and_new_progress_resets_it():
    c = colony(team_sharing=True, progress_control=True)
    c.workbench = SimpleNamespace()
    c.round = c.config.stagnation_rounds
    c.assess_progress()
    assert c.force_bank_review and c.final_answer is None
    c.round += c.config.bank_review_interval - 1
    c.assess_progress()
    assert c.final_answer is None
    c.round += 1
    c.assess_progress()
    assert c.submission_mode == 'automatic_stagnation_checkpoint'

    d = colony(team_sharing=True, progress_control=True)
    progress = {"writes": 0, "tests": 0}
    d.workbench = SimpleNamespace(summary=lambda t: dict(progress),
                                 execute=lambda a, action: progress.update(writes=1))
    d.round = d.config.stagnation_rounds
    d.assess_progress()
    d.execute_with_progress(next(iter(d.agents.values())), {})
    assert d.stall_review_round is None and d.last_productive_round == d.round


def test_ambiguous_multiobject_json_remains_fail_closed():
    c = colony(team_sharing=True)
    assert c.parse('{"tool":{"kind":"exec","command":"pwd"}}\n{"tool":{}}', {'tool'}, 'a0001') == {}
    assert c.events[-1]['event'] == 'invalid_reply'
    assert 'simulate' in rules(c.config, 'work')


def test_treatment_flag_is_explicit_and_budget_accounting_unchanged(monkeypatch):
    from test_colony40_plan import module
    from test_programbench import config
    m = module(monkeypatch)
    base = m.experiment_config(config().to_dict(), model_mix='all-astra', quality_first=True)
    treatment = m.experiment_config(config().to_dict(), model_mix='all-astra', quality_first=True, team_sharing=True)
    assert {k for k in base if base[k] != treatment[k]} == {'team_sharing'}
    assert treatment['max_rounds'] == 60


@pytest.mark.parametrize('adaptive', [False, True])
def test_complete_40_agent_scripted_episode_with_actual_dollar_audit(tmp_path, adaptive):
    from ant_colony.engine import ColonyMAS
    from ant_colony.environment import Task
    from ant_colony.providers import OpenRouterProvider
    from ant_colony.storage import RunStore, audit
    from test_programbench import config, MODELS
    from test_providers_and_evaluation import response

    def transport(payload):
        o = json.loads(payload['messages'][-1]['content'])
        if o['phase'] == 'application':
            reply = {'proposal': {'plan': 'Verify arithmetic', 'amount': 5_000_000}}
        elif o['phase'] == 'bank':
            reply = {'decisions': [{'agent': p['agent'], 'decision': 'approve', 'amount': p['amount'],
                                     'feedback': 'Provide evidence'} for p in o['proposals']]}
        elif o['phase'] == 'work':
            reply = {'shared_post': post(), 'messages': [{'to': 'bank', 'text': 'Verified arithmetic'}], 'submit': '2'}
        else:
            reply = {}
        from test_mechanism import encode_reply
        return response(encode_reply(o, reply), tokens=40, cost=0.001)

    cfg = config(initial_agents=39, initial_models=('astra',) * 39, max_agents=63,
                 worker_models=('astra',), quality_first=True, team_sharing=True,
                 adaptive_communication=adaptive,
                 request_pricing=True, bank_contacts=4, manager_contacts=3,
                 max_children=3, bank_board_size=0, max_rounds=2)
    store = RunStore(tmp_path / 'mock40')
    engine = ColonyMAS(cfg, Task('fixture', 'Compute 1+1', '2'),
                       OpenRouterProvider(MODELS, 100, store.emit, transport=transport), store.emit)
    report = engine.run()
    store.close()
    assert report['status'] == 'completed'
    assert audit(store.path)['accounting_valid']
    assert engine.shared_entries and report['burned'] == report['calls'] * 1000
    assert report['max_context_bytes'] <= cfg.context_bytes


@pytest.mark.parametrize('round_number,is_open', [(0, False), (1, True), (2, True), (3, False)])
def test_bootstrap_window_allows_nonliaisons_and_unfunded_contacts_then_closes(round_number, is_open):
    c, a, b, child, other, free = teams(open_contact_rounds=2)
    c.round = round_number
    before = c.ledger.wealth
    assert bool(send(c, child, other)) is is_open
    assert bool(send(c, free, child)) is is_open
    assert bool(send(c, child, free)) is is_open
    assert c.ledger.wealth == before and c.calls == 0
    assert c.rights(free) == 0 and free.team is None
    c.check()


def test_bootstrap_lookup_and_observation_match_current_communication_permissions():
    c, a, b, child, other, free = teams(open_contact_rounds=2)
    free.assignment = 'Special boundary diagnosis'
    other.assignment = 'Special boundary diagnosis'
    c.lookup_collaborators(child, 'Special boundary diagnosis')
    found = {card['id'] for card in child.directory}
    assert {free.name, other.name} <= found
    msg, _ = c.observation(child, 'work', peers=[other.name, free.name])
    obs = json.loads(msg[-1]['content'])
    assert obs['communication']['open_contact_window']
    assert len(obs['work_peers']) == 2
    assert 'OPEN CONTACT WINDOW' in msg[0]['content']
    c.round = 3
    c.lookup_collaborators(child, 'Special boundary diagnosis')
    assert not ({free.name, other.name} & {card['id'] for card in child.directory})
    msg, _ = c.observation(child, 'work', peers=[other.name, free.name])
    obs = json.loads(msg[-1]['content'])
    assert not obs['communication']['open_contact_window'] and not obs['work_peers']
    assert 'OPEN CONTACT WINDOW' not in msg[0]['content']


def test_bootstrap_does_not_bypass_message_volume_or_invalid_recipient_checks():
    c, a, b, child, other, free = teams(open_contact_rounds=2)
    with pytest.raises(ValueError, match='Too many'):
        c.outbound(free, {'messages': [{'to': child.name, 'text': 'Hello'}] * 5}, set(), 'discovery')
    other.retired = True
    result = c.outbound(child, {'messages': [
        {'to': other.name, 'text': 'retired'}, {'to': child.name, 'text': 'self'},
        {'to': 'missing', 'text': 'missing'}, {'to': free.name, 'text': 'valid'}]}, set(), 'work')
    assert len(result) == 1 and result[0][1] == free.name


def test_only_bootstrap_flag_differs_from_v11_plan(monkeypatch):
    from test_colony40_plan import module
    from test_programbench import config
    m = module(monkeypatch)
    options = dict(model_mix='all-astra', quality_first=True, team_sharing=True,
                   bank_contacts=4, manager_contacts=3, max_children=3)
    old = m.experiment_config(config().to_dict(), **options)
    new = m.experiment_config(config().to_dict(), **options, open_contact_rounds=2)
    assert {k for k in old if old[k] != new[k]} == {'open_contact_rounds'}
    assert new['discovery_contacts'] == 8 and new['message_contacts'] == 4
    with pytest.raises(ValueError, match='requires team_sharing'):
        m.experiment_config(config().to_dict(), quality_first=True, open_contact_rounds=2)
