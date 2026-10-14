"""Offline decoding, provider contracts, cost bounds and phase integrations."""

from copy import deepcopy
import json

import pytest

from ant_colony.context import build_context, byte_size, request_size
from ant_colony.config import ColonyConfig
from ant_colony.programbench import ProgramBenchWorkbench
from ant_colony.protocol import SCHEMAS
from ant_colony.reservations import FRAMING_TOKENS, input_envelope
from ant_colony.structured import (
    FORMAT, actions, decode, flat_to_wire, reply_schema, response_format, validate,
)
from test_quality_first import colony


def envelope(catalog, flat):
    result = flat_to_wire(flat, catalog)
    validate(result, reply_schema(catalog))
    return result


@pytest.mark.parametrize("text", [
    '{} {}', '{"memory":"a"}{"memory":"b"}',
    '{"memory":"a"}{"sleep":1}', '{"tool":{}}{"spawn":{}}',
    '{"memory":"a","memory":"b"}', '{"tool":{"kind":"read","kind":"write"}}',
    '{"sleep":NaN}', '{"sleep":Infinity}', '{"sleep":1e999}',
    '```json\n{}\n```', '{} trailing explanation', '{"memory":"unterminated',
    '[]', '{"memory":"a"}{}{}{}{}',
])
def test_ambiguous_or_broken_replies_never_recovered(text):
    with pytest.raises(ValueError):
        decode(text, 10000)


@pytest.mark.parametrize("text", ['{"memory":"a"} {}', '{}\n{"memory":"a"}',
                                      '{} {"memory":"a"} {}'])
def test_empty_companion_recovery_is_unambiguous(text):
    assert decode(text, 10000) == ({"memory": "a"}, True)
    assert decode('{}', 10000) == ({}, False)


def test_strict_phase_schema_rejects_unknown_duplicate_and_mistyped_actions():
    catalog = SCHEMAS["application"]
    good = envelope(catalog, {"proposal": {"plan": "Test boundary", "amount": 1000}, "accept": True})
    assert actions(good, catalog)["proposal"]["amount"] == 1000
    bad_replies = [
        {"actions": [{"action": "tool", "value": {"kind": "exec"}}]},
        {"actions": [good["actions"][0], good["actions"][0]]},
        {"actions": [{"action": "accept", "value": "true"}]},
        {"actions": [{"action": "proposal", "value": {"plan": "x", "amount": True}}]},
        {"actions": [{"action": "proposal", "value": {"plan": "x", "amount": "1000"}}]},
        {"actions": [], "tool": {"kind": "exec"}},
        {"actions": [{"action": "accept", "value": None}]},
    ]
    for reply in bad_replies:
        with pytest.raises(ValueError):
            actions(reply, catalog)


def test_new_configs_default_to_strict_and_explicit_legacy_configs_roundtrip():
    assert ColonyConfig().strict_outputs
    assert ColonyConfig.from_dict({}).strict_outputs
    legacy = ColonyConfig.from_dict({"strict_outputs": False})
    assert not ColonyConfig.from_dict(json.loads(json.dumps(legacy.to_dict()))).strict_outputs


@pytest.mark.parametrize("quality", [False, True])
@pytest.mark.parametrize("phase", ["application", "formation", "work", "review"])
def test_phase_prompts_have_one_consistent_encoding_contract(quality, phase):
    from dataclasses import replace
    c = colony()
    c.config = replace(c.config, quality_first=quality)
    a = next(iter(c.agents.values()))
    messages, _ = c.observation(a, phase)
    system = messages[0]["content"]
    obs = json.loads(messages[-1]["content"])
    assert obs["reply_format"] == FORMAT
    assert system.count("OUTPUT ENCODING (") == 1
    assert "OUTPUT ENCODING (actions-v1)" in system
    assert "top-level action\nkeys" not in system
    assert 'top-level\n"tool" key' not in system
    assert "only the current schema's optional action keys" not in system
    assert "must be present with null" in system
    assert response_format(messages)["json_schema"]["schema"] == reply_schema(obs["schema"])


@pytest.mark.parametrize("reply,expected", [
    ({"actions": [{"action": "proposal", "value": {"plan": "Check", "amount": "1000"}}]},
     "reply.actions[0].value.amount must be integer"),
    ({"actions": [{"action": "proposal", "value": {"amount": 1000}}]},
     "reply.actions[0].value.plan is required"),
    ({"actions": [{"action": "accept", "value": True, "extra": 1}]},
     "reply.actions[0].extra is not allowed"),
    ({"actions": [{"action": "tool", "value": {}}]},
     "reply.actions[0].action must name an action in this phase's catalog"),
])
def test_validation_errors_identify_the_actual_field(reply, expected):
    with pytest.raises(ValueError) as error:
        actions(reply, SCHEMAS["application"])
    assert str(error.value) == expected


def test_nullable_tool_field_preserves_specific_error():
    reply = envelope({"tool": ProgramBenchWorkbench.schema}, {"tool": {"kind": "read", "path": "SPEC.md"}})
    reply["actions"][0]["value"]["path"] = 42
    with pytest.raises(ValueError, match=r"reply.actions\[0\].value.path must be string"):
        actions(reply, {"tool": ProgramBenchWorkbench.schema})


@pytest.mark.parametrize("raw", [
    '{"memory":"old flat format"}',
    '{"actions":[{"action":"memory","value":"one"}]}'
    '{"actions":[{"action":"memory","value":"simulated next turn"}]}',
    '{"actions":[{"action":"memory","value":"one","value":"duplicate"}]}',
    '{"actions":[{"action":"memory","value":"truncated',
])
def test_default_contract_rejects_malformed_paid_replies_without_executing_or_retrying(raw):
    c = colony(lambda obs: raw)
    a = next(iter(c.agents.values()))
    c.grant(a, 15_000_000)
    original_memory = a.memory
    c.remember_and_sleep(a, c.ask(a, "work"))
    assert a.memory == original_memory
    assert c.calls == len(c.payloads) == 1
    error = c.events[-1]
    assert error["event"] == "invalid_reply"
    assert error["phase"] == "work" and error["reply_format"] == FORMAT
    assert c.provider.reserved == 0 and c.provider.spent > 0
    assert '{"actions":[]}' in c.format_errors[a.name]


def test_field_error_reaches_next_normal_turn_and_clears_after_valid_reply():
    seen = []
    def policy(obs):
        seen.append(obs)
        if len(seen) == 1:
            return {"actions": [{"action": "messages", "value": [{"to": "bank", "text": 42}]}]}
        assert "reply.actions[0].value[0].text must be string" in obs["last_protocol_error"]
        return {"actions": [{"action": "memory", "value": "corrected"}]}
    c = colony(policy)
    a = next(iter(c.agents.values()))
    c.grant(a, 15_000_000)
    c.remember_and_sleep(a, c.ask(a, "work"))
    assert c.calls == 1 and a.memory != "corrected"
    assert len(c.format_errors[a.name].encode()) < 512
    c.remember_and_sleep(a, c.ask(a, "work"))
    assert c.calls == 2 and a.memory == "corrected" and a.name not in c.format_errors


def test_default_bank_contract_accepts_minimal_tasks_and_rejects_forged_ownership():
    from ant_colony.board import TaskBoard
    task = {"id": "verify", "title": "Verify", "scope": "Independent checks", "acceptance": "Reproduce result"}
    c = colony(lambda obs: flat_to_wire({"tasks": [task]}, obs["schema"]))
    c.board = TaskBoard(4, c.config.text_bytes)
    c.fund([], planning=True)
    assert c.board.items["verify"]["status"] == "open"
    assert c.board.items["verify"]["owner"] is None
    before = c.board.view()
    task["owner"] = "forged"
    c.fund([], planning=True)
    assert c.board.view() == before
    assert c.events[-1]["reason"] == "reply.actions[0].value[0].owner is not allowed"


def test_clear_actions_preserve_null_and_no_actions_do_not_close_jobs():
    catalog = {**SCHEMAS["formation"], "liaison": "worker ID or null"}
    assert actions({"actions": []}, catalog) == {}
    clears = {"opening": None, "recruitment_request": None, "liaison": None}
    assert actions(envelope(catalog, clears), catalog) == clears
    opening = {"opening": {"assignment": "subproblem", "allowance": 1000}}
    assert actions(envelope(catalog, opening), catalog) == opening


def test_tool_optional_fields_and_file_encoding_are_lossless_and_unique():
    catalog = {"tool": ProgramBenchWorkbench.schema}
    original = {"tool": {"kind": "probe", "args": ["input.csv"],
                         "files": {"input.csv": 'a,b\n"quoted",\\\n'}, "capture": ["output.csv"]}}
    wire = envelope(catalog, original)
    assert actions(wire, catalog) == original
    wire["actions"][0]["value"]["files"].append({"path": "input.csv", "content": "conflict"})
    with pytest.raises(ValueError, match="Duplicate tool file"):
        actions(wire, catalog)
    tool = envelope(catalog, {"tool": {"kind": "read", "path": "SPEC.md"}})
    tool["actions"][0]["value"]["kind"] = "delete_everything"
    with pytest.raises(ValueError):
        actions(tool, catalog)


def test_schema_is_in_input_bound_and_cannot_displace_required_context():
    required = {"phase": "work", "schema": {"tool": ProgramBenchWorkbench.schema}, "_strict_outputs": True}
    messages, _ = build_context("rules", required, [], 20000)
    format_ = response_format(messages)
    assert format_["json_schema"]["strict"] is True
    assert request_size(messages) == byte_size(messages) + byte_size(format_)
    settings = {"id": "openai/example", "input_token_ceiling": 100000}
    assert input_envelope(settings, enabled=True, messages=messages) == request_size(messages) + FRAMING_TOKENS
    with pytest.raises(ValueError, match="Required context exceeds"):
        build_context("rules", required, [], request_size(messages) - 1)
    _, dropped = build_context("rules", required, [{"memory": "x" * 1000}], request_size(messages))
    assert dropped == 1


def test_live_path_uses_strict_schema_single_settlement_and_matching_reserve():
    def policy(obs):
        assert obs["reply_format"] == FORMAT
        return envelope(obs["schema"], {"memory": "bounded evidence", "messages": []})
    c = colony(policy, strict_outputs=True)
    a = next(iter(c.agents.values()))
    c.grant(a, 15_000_000)
    result = c.ask(a, "formation")
    assert result == {"memory": "bounded evidence", "messages": []}
    payload = c.payloads[-1]
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["provider"]["require_parameters"] is True
    assert payload["provider"]["allow_fallbacks"] is False
    assert c.calls == 1 and c.provider.reserved == 0
    assert c.provider.spent > 0
    reservation = next(e for e in c.events if e["event"] == "call_reserved")
    _, dollars = c.provider.reservation(a.model, payload["messages"], payload["max_tokens"])
    assert reservation["credits"] == c.dollar_credits(dollars)
    assert reservation["input_bytes"] == request_size(payload["messages"]) <= c.config.context_bytes


def test_entire_reply_validated_before_any_action_is_returned():
    c = colony(lambda obs: {"actions": [
        {"action": "memory", "value": "do not apply"},
        {"action": "spawn", "value": {"model": "astra", "allowance": "bad"}},
    ]}, strict_outputs=True)
    a = next(iter(c.agents.values()))
    c.grant(a, 15_000_000)
    assert c.ask(a, "work") == {}
    assert c.calls == 1 and c.events[-1]["event"] == "invalid_reply"


def test_recovery_logs_and_validates_exact_host_phase_without_paid_retry():
    c = colony(strict_outputs=True)
    a = next(iter(c.agents.values()))
    c.reply_contracts = {a.name: {"phase": "formation", "reply_format": FORMAT,
                                 "schema": SCHEMAS["formation"]}}
    reply = envelope(SCHEMAS["formation"], {"memory": "evidence"})
    assert c.parse(json.dumps(reply) + '{}', set(SCHEMAS["formation"]), a.name) == {"memory": "evidence"}
    assert c.events[-1]["event"] == "reply_recovered" and c.calls == 0
    assert c.parse('{"actions":[{"action":"tool","value":{}}]}{}', set(SCHEMAS["formation"]), a.name) == {}
    assert c.events[-1]["event"] == "invalid_reply"


def test_legacy_recovery_requires_nested_validation_and_retains_valid_messages():
    c = colony(strict_outputs=False)
    a = next(iter(c.agents.values()))
    catalog = deepcopy(SCHEMAS["work"])
    c.reply_contracts = {a.name: {"phase": "work", "schema": catalog}}
    assert c.parse('{"messages":[{"to":"a2","text":"test evidence"}]}{}', set(catalog), a.name) == {
        "messages": [{"to": "a2", "text": "test evidence"}]}
    assert c.parse('{"messages":[{"to":"a2"}]}{}', set(catalog), a.name) == {}
    assert c.parse('{"messages":[]} {"spawn":{}}', set(catalog), a.name) == {}


def test_discovery_and_bank_use_phase_specific_strict_contracts():
    c = colony(lambda obs: {"actions": []}, strict_outputs=True)
    c.workbench = type("Workbench", (), {"inspect_public": lambda self, value: {}})()
    c.discover()
    assert c.calls > 0
    assert all(p["response_format"]["json_schema"]["name"] == "colony_discovery" for p in c.payloads)
    assert not any(e["event"] == "invalid_reply" for e in c.events)
    c.workbench = None
    from ant_colony.board import TaskBoard
    c.board = TaskBoard(4, c.config.text_bytes)
    c.fund([], planning=True)
    assert c.payloads[-1]["response_format"]["json_schema"]["name"] == "colony_bank"
    assert not any(e["event"] == "invalid_reply" for e in c.events)


def test_complete_mock_run_passes_financial_audit_with_schema_overhead(tmp_path):
    from ant_colony.config import ColonyConfig
    from ant_colony.engine import ColonyMAS
    from ant_colony.environment import Task
    from ant_colony.providers import OpenRouterProvider
    from ant_colony.storage import RunStore, audit
    from test_providers_and_evaluation import MODELS, response

    def transport(payload):
        obs = json.loads(payload["messages"][-1]["content"])
        result = {}
        if obs["phase"] == "application":
            result = {"proposal": {"plan": "Compute sum", "amount": 6000}, "accept": True}
        elif obs["phase"] == "bank":
            result = {"decisions": [{"agent": p["agent"], "amount": p["amount"],
                                      "decision": "approve", "feedback": "Proceed"}
                                     for p in obs["proposals"]]}
        elif obs["phase"] == "work":
            result = {"submit": "2"}
        return response(json.dumps(envelope(obs["schema"], result)))

    store = RunStore(tmp_path / "strict")
    provider = OpenRouterProvider(MODELS, 1, store.emit, transport=transport)
    c = ColonyMAS(ColonyConfig(initial_agents=2, strict_outputs=True),
                  Task("test", "1+1?", "2"), provider, store.emit)
    report = c.run()
    store.close()
    assert report["status"] == "completed" and report["rewarded"] == c.config.reward
    assert audit(store.path)["accounting_valid"]


def test_strict_rejection_does_not_fallback_or_retry_missing_billing_receipt():
    from ant_colony.providers import OpenRouterProvider, UncertainCall
    from test_providers_and_evaluation import MODELS
    sent = []
    def transport(payload):
        sent.append(payload)
        return {"error": {"code": 400}}
    provider = OpenRouterProvider(MODELS, 1, lambda *a, **kw: None, transport=transport)
    messages, _ = build_context("rules", {"phase": "work", "schema": SCHEMAS["work"],
                                          "_strict_outputs": True}, [], 20000)
    with pytest.raises(UncertainCall):
        provider.complete("worker", messages, 100, "c1")
    assert len(sent) == 1 and provider.blocked and provider.reserved > 0
    assert sent[0]["response_format"]["type"] == "json_schema"
