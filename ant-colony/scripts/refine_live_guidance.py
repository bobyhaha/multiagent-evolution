"""Apply explicit operator guidance through existing bounded project-note prompts.

This changes work-prompt context only, not loaded system prompts or agent state.
Keep immutable version files and a separate operator audit alongside run reports.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


START = "[OPERATOR_GUIDANCE "
END = "[/OPERATOR_GUIDANCE]"


def live_boundary(episode):
    lines = (episode / "events.jsonl").read_text(encoding="utf-8").splitlines()
    events = []
    for index, line in enumerate(lines):
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            if index != len(lines) - 1:
                raise
    if (episode / "report.json").exists() or any(
            e["event"].startswith("native_evaluation") or e["event"] == "finished" for e in events):
        raise ValueError("Episode is no longer in live inference")
    reserved = next((e for e in reversed(events) if e["event"] == "call_reserved"), None)
    if reserved is None or any(
            e["event"] == "call" and e["call_id"] == reserved["call_id"] for e in events):
        raise ValueError("No model request pending; retry at the next call boundary")
    return events[-1]["seq"], reserved["call_id"]


def amended_notes(previous, version, guidance):
    if not re.fullmatch(r"v[0-9]{3}", version):
        raise ValueError("Use a version such as v001")
    if not isinstance(guidance, str) or START in guidance or END in guidance:
        raise ValueError("Invalid guidance text")
    block = f"{START}{version}]\n{guidance.strip()}\n{END}\n\n"
    if len(block.encode()) > 1500:
        raise ValueError("Guidance must fit the existing 1600-byte note preview")
    body = previous
    if body.startswith(START):
        if END not in body:
            raise ValueError("Incomplete previous guidance; preserve notes for inspection")
        body = body.split(END, 1)[1].removeprefix("\n\n")
    updated = block + body
    if len(updated.encode()) > 16000:
        raise ValueError("Guidance would exceed the existing notes limit")
    return updated


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--episode", type=Path, required=True)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--audit-dir", type=Path, required=True)
    args = p.parse_args()
    episode = args.episode.resolve()
    policy_bytes = args.policy.read_bytes()
    policy = json.loads(policy_bytes)
    if set(policy) != {"version", "rationale", "common", "teams"}:
        raise ValueError("Unexpected policy fields")
    if (not isinstance(policy["rationale"], str) or not isinstance(policy["common"], str)
            or not isinstance(policy["teams"], dict)
            or any(not isinstance(k, str) or not isinstance(v, str)
                   for k, v in policy["teams"].items())):
        raise ValueError("Invalid policy metadata")
    # Apply while a model is considering its request, not during a source tool's
    # transaction. Next work observations will read the atomically updated notes.
    trace_seq, pending_call = live_boundary(episode)
    targets = [("public", episode / "coding/public/PROJECT_NOTES.md")]
    targets += [(d.name, d / "source/PROJECT_NOTES.md")
                for d in sorted((episode / "coding/teams").iterdir()) if d.is_dir()]
    prepared = []
    for team, path in targets:
        if path.is_symlink() or path.resolve() != path:
            raise ValueError("Unsafe notes path")
        previous = path.read_text(encoding="utf-8") if path.exists() else ""
        guidance = policy["common"] + "\n" + policy["teams"].get(team, "")
        updated = amended_notes(previous, policy["version"], guidance)
        prepared.append((team, path, previous, updated))
    args.audit_dir.mkdir(parents=True, exist_ok=True)
    saved_policy = args.audit_dir / f"{policy['version']}.json"
    if saved_policy.exists() and saved_policy.read_bytes() != policy_bytes:
        raise ValueError("Policy versions are immutable; use a new version")
    if not saved_policy.exists():
        saved_policy.write_bytes(policy_bytes)
    stamp = datetime.now(timezone.utc).isoformat()
    record = {"at": stamp, "version": policy["version"], "policy": str(saved_policy.resolve()),
              "policy_sha256": hashlib.sha256(policy_bytes).hexdigest(),
              "trace_seq": trace_seq, "pending_call": pending_call,
              "rationale": policy["rationale"],
              "channel": "existing work observation project_notes; system prompt unchanged"}

    def audit(fields):
        with (args.audit_dir / "guidance-events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record | fields) + "\n")
            f.flush()
            os.fsync(f.fileno())

    changes = []
    for team, path, previous, updated in prepared:
        if updated == previous:
            continue
        before = hashlib.sha256(previous.encode()).hexdigest()
        backup = args.audit_dir / f"{policy['version']}-{team}-{before}.txt"
        if not backup.exists():
            backup.write_text(previous, encoding="utf-8")
        change = {"team": team, "path": str(path), "before_sha256": before,
                  "after_sha256": hashlib.sha256(updated.encode()).hexdigest(),
                  "bytes": len(updated.encode()), "backup": str(backup.resolve())}
        live_boundary(episode)
        audit({"event": "planned", "change": change})
        # Temp files stay outside candidate source, avoiding tracked-file churn.
        fd, temp = tempfile.mkstemp(prefix="operator-notes-", dir=path.parent.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(updated)
            os.chmod(temp, path.stat().st_mode & 0o777 if path.exists() else 0o644)
            if (path.read_text(encoding="utf-8") if path.exists() else "") != previous:
                raise ValueError("Notes changed concurrently; retry with fresh contents")
            os.replace(temp, path)
        finally:
            if Path(temp).exists():
                Path(temp).unlink()
        changes.append(change)
        audit({"event": "applied", "change": change})
    if changes:
        audit({"event": "batch_complete", "changes": changes})
    print(json.dumps(record | {"changes": changes}))


if __name__ == "__main__":
    main()
