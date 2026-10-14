# V12: two-round open contact window

The user selected option 2 and explicitly requested stopping V11 and restarting.
This is a fresh 40-Astra, high-reasoning ProgramBench xsv run with
`team_sharing=true` and `open_contact_rounds=2`.

During rounds 1 and 2, any worker taking a funded or sponsored turn may message
any other known live worker, including an unfunded applicant or a member of
another team. Topic lookup can return these collaborators, with the same bounded
directory size. No full-population transcript or roster is injected. Messaging
does not grant membership, money, editing authority, or free inference.

From round 3, direct messages again stay within teams or between liaisons. Shared
scratchpad publication and bounded retrieval remain available. Teams and hierarchy
persist across the transition. At most four messages per reply, eight inbox
entries, and the existing serialized context limits apply throughout.

This changes contact permissions and corresponding prompt/context guidance only.
Discovery admission remains eight agents per round; no universal orientation
round, additional bank review slots, special funding priority, or extra inference
is introduced. Recursive hiring, sponsorship and all financial controls remain.

Tests cover the exact round-2/round-3 transition, unfunded contact without free
inference, lookup/visible-peer consistency, retired and invalid recipients, volume
limits, configuration validation, and unchanged treatment settings. All 274 tests
and lint passed before launch. V11 frozen sources remain untouched.

V11 stopped at the user's request with $7.68422 settled, no held charges and a
passing financial audit. Its early checkpoint evaluation was unscored with
`native_result_with_errors`; it is neither a completed treatment nor zero accuracy.
The generic runtime called this an automatic budget checkpoint, but the actual
trigger was the operator STOP, not budget exhaustion.

V12 has a $92.98 attempt cap. V7, V8 (including its $1.11669 unresolved hold),
V10, V11 and V12 ceilings total $199.9908855 within the existing $200 all-Astra
allowance. The shared campaign remains capped at $500. Historical call rows were
hashed before/after sealing V11 and are unchanged. See
`runs/v12-open-contact-validation/budget-amendment.json`.

Compare participation, team formation, cross-team messages during the window,
liaison handoff, useful implementation/integration, malformed replies, native
score and actual cost. V11 is an interrupted reference; V10 and solo runs have
different budgets/horizons. One fresh run with no controlled provider seed cannot
establish a causal benefit from open communication.
