"""Explicit, ungraded artifact continuation; never restore or replay paid calls."""

import hashlib
import json
from pathlib import Path

from .programbench_probes import validate_probe


def continue_artifact(bench, episode):
    episode = Path(episode).resolve()
    report = json.loads((episode / "report.json").read_text())
    audit = json.loads((episode / "audit.json").read_text())
    provenance = json.loads((episode / "coding/provenance.json").read_text())
    if report.get("status") != "error" or report.get("score") is not None:
        raise ValueError("Only an interrupted, ungraded artifact may continue")
    if not audit.get("accounting_valid") or audit.get("complete_evaluation"):
        raise ValueError("Prior financial audit or ungraded condition failed")
    if (report.get("task_id") != bench.manifest["id"]
            or provenance.get("task") != bench.manifest["id"]
            or provenance.get("source_revision") != bench.manifest["source_revision"]):
        raise ValueError("Continuation task/provenance mismatch")
    # Do not read native outputs, or accept a checkpoint selected after grading.
    for line in (episode / "events.jsonl").open():
        if json.loads(line)["event"].startswith("native_evaluation"):
            raise ValueError("Native evaluation already began; no artifact reuse")
    if (episode / "coding/selected-artifact.json").exists():
        raise ValueError("A terminal evaluation artifact was already selected")
    export = json.loads((episode / "coding/checkpoint-export.json").read_text())
    source = episode / "coding/checkpoint-export"
    files = bench.code_files(source)
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    if not files or hashes != export["source_hashes"]:
        raise ValueError("Saved checkpoint hash mismatch")
    notes = source / "PROJECT_NOTES.md"
    if notes.is_symlink():
        raise ValueError("Unsafe checkpoint notes")
    note_data = notes.read_bytes() if notes.exists() else b""
    note_data.decode("utf-8")
    if len(note_data) > 16000:
        raise ValueError("Checkpoint notes exceed fixed bound")
    probe_path = episode / "coding/public-probes.json"
    probes = json.loads(probe_path.read_text()) if probe_path.exists() else []
    if not isinstance(probes, list) or len(probes) > 32:
        raise ValueError("Invalid saved public probes")
    ids = set()
    for row in probes:
        probe = validate_probe(row["input"])
        ident = hashlib.sha256(json.dumps(probe, sort_keys=True).encode()).hexdigest()[:16]
        if row["id"] != ident or ident in ids or not isinstance(row["expected"], dict):
            raise ValueError("Invalid saved probe identity")
        ids.add(ident)
    # Copy only verified source, bounded notes and existing public diagnostics.
    # No transcript, hidden result, old membership or wallet enters the new run.
    for name in bench.code_files(bench.public):
        (bench.public / name).unlink()
    for name, data in files.items():
        target = bench.public / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (bench.public / "PROJECT_NOTES.md").write_bytes(note_data)
    bench.public_version = export["version"]
    bench.probe_bank = probes
    if probes:
        bench._write("public-probes.json", probes)
    record = {"parent_episode": str(episode), "source_hashes": hashes,
              "notes_sha256": hashlib.sha256(note_data).hexdigest(),
              "public_probe_ids": sorted(ids), "prior_rounds": report["rounds"],
              "agent_state_restored": False, "hidden_evaluation_reused": False,
              "selection": "last integrated ungraded checkpoint, not score-selected"}
    bench._write("continuation.json", record)
    bench.emit("artifact_continued", **record)
    return record
