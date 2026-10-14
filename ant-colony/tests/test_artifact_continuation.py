import hashlib
import json

import pytest

from ant_colony.continuation import continue_artifact
from test_programbench import fixture


def saved_episode(tmp_path, bench):
    old = tmp_path / "old"
    code = old / "coding/checkpoint-export"
    code.mkdir(parents=True)
    (code / "main.py").write_text("print('existing work')\n")
    (code / "PROJECT_NOTES.md").write_text("Check parser boundaries.\n")
    def write(path, value):
        (old / path).write_text(json.dumps(value))
    write("report.json", {"status": "error", "score": None, "task_id": bench.manifest["id"], "rounds": 3})
    write("audit.json", {"accounting_valid": True, "complete_evaluation": False})
    write("coding/provenance.json", {"task": bench.manifest["id"], "source_revision": bench.manifest["source_revision"]})
    write("coding/checkpoint-export.json", {"source_hashes": bench.hashes(code), "version": 5})
    probe = {"args": ["--help"], "stdin": "", "files": {}, "capture": []}
    ident = hashlib.sha256(json.dumps(probe, sort_keys=True).encode()).hexdigest()[:16]
    write("coding/public-probes.json", [{"id": ident, "input": probe, "expected": {"exit_code": 0}}])
    (old / "events.jsonl").write_text('{"event":"finished"}\n')
    return old


def test_continuation_preserves_ungraded_code_notes_and_probe_allowance(tmp_path):
    bench, _ = fixture(tmp_path)
    old = saved_episode(tmp_path, bench)
    record = continue_artifact(bench, old)
    assert (bench.public / "main.py").read_text() == "print('existing work')\n"
    assert (bench.public / "PROJECT_NOTES.md").read_text() == "Check parser boundaries.\n"
    assert len(bench.probe_bank) == 1 and bench.public_version == 5
    assert record["agent_state_restored"] is False
    assert record["hidden_evaluation_reused"] is False
    assert json.loads((bench.directory / "public-probes.json").read_text()) == bench.probe_bank


@pytest.mark.parametrize("violation", ["graded", "started", "selected", "hash", "task", "probe", "symlink"])
def test_unsafe_or_graded_continuation_is_rejected_before_import(tmp_path, violation):
    bench, _ = fixture(tmp_path)
    old = saved_episode(tmp_path, bench)
    if violation in {"graded", "task"}:
        report = json.loads((old / "report.json").read_text())
        report["score" if violation == "graded" else "task_id"] = 0.5 if violation == "graded" else "other"
        (old / "report.json").write_text(json.dumps(report))
    elif violation == "started":
        (old / "events.jsonl").write_text('{"event":"native_evaluation_started"}\n')
    elif violation == "selected":
        (old / "coding/selected-artifact.json").write_text('{}')
    elif violation == "hash":
        (old / "coding/checkpoint-export/main.py").write_text("changed")
    elif violation == "probe":
        probes = json.loads((old / "coding/public-probes.json").read_text())
        probes[0]["input"]["args"] = ["changed"]
        (old / "coding/public-probes.json").write_text(json.dumps(probes))
    elif violation == "symlink":
        p = old / "coding/checkpoint-export/main.py"
        p.unlink()
        p.symlink_to(old / "report.json")
    with pytest.raises(ValueError):
        continue_artifact(bench, old)
    assert not (bench.public / "main.py").exists()
