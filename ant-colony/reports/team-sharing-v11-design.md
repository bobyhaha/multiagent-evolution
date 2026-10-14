# V11: preserve useful teams, share evidence, reduce coordination failures

## Evidence from V10

The completed quality-first 40-Astra run scored 1,096/1,332 native cases
(82.2823%) in 60 rounds, costing $96.990195 across 779 calls. Eleven worker
identities worked, with four hires, four new spawns and maximum depth two.
Only one productive worker was at depth two. The three root teams divided
integration, analytics and data operations; this produced useful module ownership
and regression repair. Tree depth alone does not establish useful specialization.

The trace contains 66 invalid JSON replies, 71 rejected message batches and 21
introduction-queue rejections. All 71 rejected message batches included `to: bank`.
The previous recipient validator rejected the whole batch, including legitimate
teammate messages. These failures were not evidence that peer degree was too small:
quality-first workers could already address every live worker. Several malformed
replies contained a second simulated action object despite provider JSON-object
mode. Discarding ambiguous replies is necessary, but loses a paid work opportunity.

The last recorded productive step was round 24. Rounds 25–60 cost about $3.00;
this tail inflated rounds more than dollars. Non-work phases cost $21.2631375
(about 22% of total). Visible probes reached 32/32, which did not imply native
completeness. The original quality-first stagnation branch requested review but
could never stop before the hard deadline.

## Implemented treatment

- `team_sharing=true` explicitly enables the new mechanism. Historical/default
  mechanisms and frozen experiment runtimes remain unchanged.
- Keep recursive teams, three direct children and depth six. No fixed specialist
  roles or mandatory recruitment. The root and at most one root-appointed teammate
  are cross-team liaisons; the extra appointment expires after four rounds.
- Direct work messages stay within a funded team, or between liaisons. Unfunded
  applicants retain sponsored discovery, offers and common evidence publication.
- Append-only shared posts carry author, team, round, topic, status, evidence
  reference and at most 900 bytes of body. A correction is another post. Retrieval
  selects at most three latest-by-author/topic entries, prioritizing one recent
  unresolved blocker. Detailed notes remain team-local. Posts are claims, not
  verified execution evidence. The bank receives bounded shared entries at review.
- `bank` messages publish attributed shared updates rather than calling the bank.
  Each recipient is validated independently; one bad address cannot discard
  successful teammate deliveries. Failures distinguish invalid, duplicate,
  retired and unauthorized cross-team addresses.
- Introduction storage can queue one current referral per candidate. Only the
  configured review batch is shown or considered for the next hiring admission.
  Queueing creates no grant or inference call. Existing consent and budget checks
  remain mandatory. Queued introductions get a bounded additional waiting period.
- After six rounds without recorded productive work, request bank strategy review.
  If no progress appears in the next four rounds, select the integrated checkpoint.
  A new productive step resets this clock. Messages and shared posts do not count.
- Prompts require evidence-based coverage, local regression/metamorphic checks and
  explicit untested boundaries. Passing public probes is not sufficient coverage.
  No previous implementation, hidden feedback or task-specific repair instructions
  enter the fresh run.
- Prompts explicitly prohibit simulated subsequent turns. Ambiguous multi-object
  JSON still executes nothing; no paid retry or permissive concatenation is added.
  Whether this reduces malformed outputs is an experimental question.

## Scalability and limits

Maximum inference context remains 64,000 serialized UTF-8 bytes for work and
32,000 for coordination. Messages remain capped at four per reply, inboxes at
eight, bank reviews at four proposals and local reviews at three. Common evidence
is retrieved rather than broadcast into every transcript. Host-side storage and
search grow with accumulated work; this is bounded model context, not a claim of
constant total runtime or storage. The root is always a liaison, so expiry does
not strand a team. Any teammate can publish a shared blocker.

Progress is the existing source-write/fresh-revision-test proxy. It is not proof of
correctness and can count documentation edits or miss useful unchanged-code
investigation. This treatment does not claim to solve semantic progress detection.

## Validation and experiment

Regression tests cover local and liaison authorization, temporary appointments,
unfunded publication, per-recipient failure isolation, bank update routing,
immutable corrections, bounded retrieval/context, overflow introduction queues,
stagnation and progress reset, strict JSON parsing, and a complete mocked
40-agent episode with independently audited dollar accounting. A separate Docker
smoke checks isolation, public probing, build and integration; its fixture artifacts
are never used as the paid experiment seed.

The fresh ProgramBench xsv attempt uses 39 Astra workers plus one Astra bank,
high reasoning, up to 60 rounds, at most 64 agents including the bank, and a
$100 attempt ceiling. Seal completed V10 at its actual settled cost before
registering V11. V7 + V8 (including its full unresolved reservation) + V10 +
V11 ceilings sum to $199.3266655, within the existing $200 all-Astra total.
The original $500 campaign cap and historical holds remain unchanged.

Compare native counts, score, actual spend, coordination cost, rejected messages,
malformed replies, participation, useful depth and shared-evidence use against V10
and existing solo-Astra references. V10 had a larger available ceiling; solo runs
had different horizons and budgets. This is one compound treatment and one fresh,
uncontrolled provider-seed run, not a causal ablation or statistically reliable
claim of superiority.
