"""Replay invalid JSON decoding offline. Never execute actions or call a provider."""

import argparse
from collections import Counter
import json
from pathlib import Path

from ant_colony.structured import actions, decode, flat_to_wire, observation


def analyze(path):
    reservations, latest, reasons = {}, {}, Counter()
    recoverable = []
    checked = 0
    for line in Path(path).open():
        event = json.loads(line)
        if event["event"] == "call_reserved":
            reservations[event["call_id"]] = observation(event["messages"])
        elif event["event"] == "call":
            latest[event["actor"]] = event
        elif event["event"] == "invalid_reply":
            checked += 1
            call = latest.get(event["actor"], {})
            contract = reservations.get(call.get("call_id"), {})
            try:
                reply, recovered = decode(call.get("text"), 16384 * 32)
                if not recovered:
                    raise ValueError("Not an empty-companion recovery")
                catalog = contract.get("schema", {})
                if not catalog:
                    raise ValueError("Missing recorded phase schema")
                normalized = actions(flat_to_wire(reply, catalog), catalog)
                recoverable.append({"call_id": call["call_id"], "phase": contract["phase"],
                                    "actions": sorted(normalized)})
            except (ValueError, TypeError, RecursionError) as exc:
                reasons[str(exc)] += 1
    return {"source": str(Path(path).resolve()), "invalid_replies_checked": checked,
            "recoverable": len(recoverable), "still_rejected": sum(reasons.values()),
            "rejection_reasons": dict(reasons), "recoverable_calls": recoverable,
            "actions_executed": 0, "paid_calls": 0,
            "scope": "Offline syntax/schema recovery only; no inference about task score"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events", type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(args.events), indent=2))
