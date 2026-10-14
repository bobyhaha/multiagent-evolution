"""A hard serialized-input bound; history is never automatically concatenated."""

from copy import deepcopy
import json


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def clip(text, limit):
    if not isinstance(text, str):
        raise ValueError("Expected text")
    return text.encode("utf-8")[:limit].decode("utf-8", errors="ignore")


def byte_size(value):
    return len(dumps(value).encode("utf-8"))


def messages(system, observation):
    if observation.get("_strict_outputs"):
        from .structured import FORMAT, WIRE_RULES
        observation = {k: v for k, v in observation.items() if k != "_strict_outputs"}
        observation["reply_format"] = FORMAT
        system += WIRE_RULES
    elif "schema" in observation:
        from .structured import LEGACY_WIRE_RULES
        system += LEGACY_WIRE_RULES
    return [{"role": "system", "content": system}, {"role": "user", "content": dumps(observation)}]


def request_size(request_messages):
    """Serialized messages plus the separately transmitted response schema."""
    from .structured import response_format
    output_format = response_format(request_messages)
    return byte_size(request_messages) + (byte_size(output_format) if output_format else 0)


def build_context(system, required, optional, limit):
    """Add bounded optional items until full. Never truncate the task or schema.

    The unit is UTF-8 bytes of the entire serialized messages array plus the
    separately transmitted response schema, not a tokenizer estimate. Provider
    framing is separate, fixed overhead.
    """
    observation = dict(required)
    observation["context"] = []
    if request_size(messages(system, observation)) > limit:
        raise ValueError(
            "Required context exceeds context_bytes; raise the configured constant or shorten task"
        )
    dropped = 0
    for item in optional:
        observation["context"].append(item)
        if request_size(messages(system, observation)) > limit:
            observation["context"].pop()
            dropped += 1
    return messages(system, observation), dropped


def build_agent_context(system, required, optional, limit):
    """Fit informational previews without shortening actionable contracts.

    Full proposals, grants, assignments, authorization, evidence status and the
    output schema remain required. Verbose receipts and collaborator previews
    can move to optional context, explicitly marked so absence is not success.
    """
    if request_size(messages(system, {**required, "context": []})) <= limit:
        return build_context(system, required, optional, limit)
    required = deepcopy(required)
    details = []

    def preview(row, fields, path):
        changed = False
        original = deepcopy(row)
        for key, cap in fields.items():
            if isinstance(row.get(key), str) and len(row[key].encode()) > cap:
                row[key] = clip(row[key], cap)
                changed = True
        if changed:
            row["details_optional"] = True
            details.append({"context_detail": {"path": path, "full": original}})

    progress = required.get("verified_progress") or {}
    for i, receipt in enumerate(progress.get("recent_executions", [])):
        preview(receipt, {"command": 120, "output": 120}, f"verified_progress.recent_executions[{i}]")
    last_test = progress.get("last_test") or {}
    for i, failure in enumerate(last_test.get("failures", [])):
        if isinstance(failure, dict):
            details.append({"context_detail": {"path": f"verified_progress.last_test.failures[{i}]", "full": deepcopy(failure)}})
            # Keep failure identity, status and return code, never turn failure
            # into absence of failures merely to make a prompt smaller.
            for key in list(failure):
                if key not in {"probe", "test", "id", "status", "exit_code"}:
                    failure.pop(key)
            failure["details_optional"] = True
    for field in ("directory", "peers", "work_peers"):
        for i, card in enumerate(required.get(field, [])):
            preview(card, {"profile": 160, "assignment": 240}, f"{field}[{i}]")
    for field, entries in (
        ("recruitment.introductions", (required.get("recruitment") or {}).get("introductions", [])),
        ("collaboration_offers", required.get("collaboration_offers", [])),
    ):
        for i, card in enumerate(entries):
            preview(card, {"plan": 400, "reason": 180}, f"{field}[{i}]")
    for i, entry in enumerate(required.get("shared_scratchpad", [])):
        preview(entry, {"text": 240, "evidence": 160}, f"shared_scratchpad[{i}]")
    for field in ("previous_inspection", "discovery_evidence"):
        if isinstance(required.get(field), dict):
            preview(required[field], {"text": 600}, field)
    if details:
        required["context_compaction"] = (
            "Some informational previews are abbreviated and marked details_optional. "
            "Full versions appear in context_detail when space permits. Ask the named "
            "collaborator or read the cited file for missing details. Formal proposals, "
            "money, ownership and authorization are unchanged."
        )
    return build_context(system, required, [*optional, *details], limit)


def build_review_context(system, required, optional, limit):
    """Retain financial/review facts; fit verbose evidence after them if needed."""
    if request_size(messages(system, {**required, "context": []})) <= limit:
        return build_context(system, required, optional, limit)
    required = deepcopy(required)
    details = []
    evidence = required.get("verified_evidence", {})
    for applicant in evidence.get("applicants", []):
        for index, receipt in enumerate(applicant.get("progress", {}).get("recent_executions", [])):
            details.append({"execution_detail": {"team": applicant["team"], "receipt_index": index,
                                                  **deepcopy(receipt)}})
            receipt["command"] = clip(receipt.get("command", ""), 120)
            receipt.pop("output", None)
            receipt["details_optional"] = True
    evidence["verbose_details_in_context_if_space"] = True
    if request_size(messages(system, {**required, "context": []})) > limit:
        public_test = evidence.get("public_test") or {}
        for failure in public_test.get("failures", []):
            details.append({"public_probe_failure_detail": deepcopy(failure)})
        if public_test.get("failures"):
            public_test["failures"] = [{"probe": f.get("probe"), "details_optional": True}
                                       for f in public_test["failures"]]
    # Status, exit codes, revision, counts, scores and all proposals stay required.
    # A truncated shell output must never be mistaken for a passing test.
    return build_context(system, required, details + optional, limit)
