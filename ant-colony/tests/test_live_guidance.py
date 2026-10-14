import importlib.util
import json
from pathlib import Path
import sys

import pytest


spec = importlib.util.spec_from_file_location(
    "live_guidance", Path(__file__).parents[1] / "scripts/refine_live_guidance.py")
guidance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guidance)


def test_guidance_replacement_preserves_agent_notes_and_is_idempotent():
    original = "\n\nKnown interface: x\n\nNext: test Unicode π.\n"
    first = guidance.amended_notes(original, "v001", "Run focused checks.")
    updated = guidance.amended_notes(first, "v002", "Check, then hand off.")
    assert updated.endswith(original)
    assert updated.count(guidance.START) == 1
    assert "v001" not in updated
    assert guidance.amended_notes(updated, "v002", "Check, then hand off.") == updated


@pytest.mark.parametrize("previous,version,text", [
    ("[OPERATOR_GUIDANCE v001]\nbroken", "v002", "x"),
    ("notes", "../x", "x"),
    ("notes", "v001", "π" * 800),
    ("n" * 16000, "v001", "x"),
    ("notes", "v001", "[/OPERATOR_GUIDANCE]"),
])
def test_unsafe_or_oversized_guidance_fails_without_writes(previous, version, text):
    with pytest.raises(ValueError):
        guidance.amended_notes(previous, version, text)


def test_live_injection_audited_without_touching_source(tmp_path, monkeypatch):
    episode = tmp_path / "episode"
    source = episode / "coding/teams/t0001/source"
    source.mkdir(parents=True)
    public = episode / "coding/public"
    public.mkdir(parents=True)
    (source / "main.py").write_text("original source\n")
    (source / "PROJECT_NOTES.md").write_text("agent findings\n")
    events = episode / "events.jsonl"
    events.write_text(json.dumps({"event": "call_reserved", "call_id": "c1", "seq": 1}) + "\n")
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"version": "v001", "rationale": "trace finding",
                                  "common": "Focused checks.", "teams": {}}))
    audit = tmp_path / "audit"
    monkeypatch.setattr(sys, "argv", ["refine", "--episode", str(episode),
                                     "--policy", str(policy), "--audit-dir", str(audit)])
    guidance.main()
    assert (source / "PROJECT_NOTES.md").read_text().endswith("agent findings\n")
    assert (source / "main.py").read_text() == "original source\n"
    log = (audit / "guidance-events.jsonl").read_text()
    assert len([r for r in map(json.loads, log.splitlines()) if r["event"] == "applied"]) == 2
    guidance.main()
    assert (audit / "guidance-events.jsonl").read_text() == log
    with events.open("a") as f:
        f.write(json.dumps({"event": "call", "call_id": "c1", "seq": 2}) + "\n")
    with pytest.raises(ValueError, match="No model request"):
        guidance.main()
    events.write_text(json.dumps({"event": "native_evaluation_waiting", "seq": 3}) + "\n")
    with pytest.raises(ValueError, match="no longer"):
        guidance.main()
