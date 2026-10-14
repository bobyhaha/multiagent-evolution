# Validation: sponsored recursive protocol

## Output contract update — October 12, 2026

New configurations and the colony40 launcher enable strict output contracts by
default, with explicit legacy opt-out. Prompts now describe a single response
envelope. Validation errors identify the failing field and reach the next
allocated turn; malformed replies cannot execute actions or trigger free retries.
Board status and feedback retain their optional runtime semantics through null
fields in the strict wire schema.

The baseline passed 355 tests. After the change, **377 tests pass**, including
the default CLI demo, strict bank/worker/discovery paths, 40-agent mock accounting,
duplicate and simulated-turn rejection, field-specific feedback, and explicit
legacy compatibility. Ruff passes for the changed Python files. All verification
is offline or uses mock transports; this does not measure a live malformed-output
rate or benchmark improvement. Frozen experiment runtimes were not modified.
Schema bytes still count against context and reservation limits; an oversized
required context stops before a model call rather than silently increasing caps.

## Earlier experiment record

Implementation and checks performed October 9–10, 2026. The current mechanism
includes a bounded bank task board, exclusive root-team claims, freely revisable
worker strategies, recursive hiring/spawning, persistent coding state and automatic
deadline grading. Live Commit0 runs use GPT-6-Luna for both bank and workers.
The six-episode matched TinyDB comparison is complete: the board runs pass
75, 61 and 158 of 201 tests, versus 23, 31 and 41 without the board. Mean passed
tests are 98 versus 31.7. Board runs record zero integration-conflict events,
versus thirty in the controls, but do not hire or spawn. These are single-library
experiments, not evidence of general superiority or an emergent ant colony.
All recorded ant-colony development and study charges total $1.882783995, plus
up to $0.056384 in retained uncertain charges: below the user's $50 cap.

## Software checks

- **133 tests passed** under Python 3.14.2; Ruff passed.
- Version 0.3.0 wheel builds and includes the funding protocol, Docker coding
  adapter, and offline replay. CLI imports are tested outside the source folder.
- Original EoM core provenance remains pinned to
  `d272266f7d6a0c302b7af5d20f1326b63c5656fb`; unchanged copied files pass hash checks.
- Tests cover silent unfunded waiting, explicit payer authorization, application
  budget exhaustion, finite revisions, actionable feedback, rejection, consensual
  hiring, expired opportunities, local child/grandchild requests, recursive caps,
  source isolation, optimistic file writes, bounded paging, and missing scores.
  New checks cover cumulative integration, conflict preservation, bounded merge
  admission, transactional artifact limits, deadline grading after team closure,
  budget-stop export, precise test-revision tracking, command import, bounded
  escaped receipts, deduplicated failure feedback, malformed-response recovery,
  accurate remaining-work-call observations, atomic rejection/recovery of invalid
  Python updates, and bounded escaped context under both 24 KB and 64 KB settings.
  Further checks cover exact preservation of deleted implementation files during
  grading, maximal receipt packing, and public reward/cost visibility without
  leaking reference answers. Board checks cover atomic bounded updates, ownership
  controlled by grants, same-response approval/claim intent, duplicate funding
  prevention, top-ups, claim release, work suspension, feedback delivery, freely
  chosen strategies, and constant admission/context with 10 versus 1,000 agents.
  The experiment launcher is checked for finite dollar allocations, matched
  settings, and refusal to rerun an existing study directory.
  Current-file-version tests cover writes without an extra hash-only read,
  rejection after intervening edits, and the sixteen-entry inventory bound.
- Independent audit checks the credit identity, exactly-once reward, API receipts,
  each application's sponsor, and the application pool. Successful, interrupted,
  and error run logs all reconcile. All six completed comparison runs have
  verified usage and zero unresolved reservations; the earlier interrupted v2
  attempt retains two uncertain calls, as detailed below.
- The updated replay renders in the in-app browser with proposal, feedback,
  sponsorship, and coding-tool filters. Earlier logs without coding-event round
  labels are displayed using event ordering; raw logs remain unchanged.

## Scripted company demonstration

[`runs/sponsored-company-demo/replay.html`](runs/sponsored-company-demo/replay.html)
exercises bank revisions, rejection followed by sponsored hiring, local manager
reviews, recursive spawning and sleep. It grows from 6 to 16 agents, reaches
recruitment depth 2, and uses the direct-child cap of 2. One consenting hire is
recorded. It completes the arithmetic fixture in round 7.

```text
100,000 initial credits + 50,000 reward - 3,040 estimated token credits = 146,960
```

There are 84 scripted calls and no API charges. Maximum input is 4,098 bytes under
the 24,000-byte cap. Bank-sponsored applications consume 341 credits; employer
applications are separately charged to their sponsoring manager's allowance.
This is a scripted protocol exercise, not evidence of LLM performance or emergence.

## Admission scaling

[`runs/sponsored-scaling.json`](runs/sponsored-scaling.json) holds admission and
context settings constant in a one-round scripted check:

| Initial agents | Sponsored application calls | Unfunded social calls | Bank calls | Largest input bytes |
|---:|---:|---:|---:|---:|
| 10 | 2 | 0 | 1 | 2,999 |
| 100 | 2 | 0 | 1 | 2,999 |
| 1,000 | 2 | 0 | 1 | 3,000 |

This checks admission/context bounds, not full-population quality or total-system
constant computation. Funded active work still scales with active population.

## Commit0: real containers and original visible tests

The prepared TinyDB source is pinned to Commit0 base revision
`ed761a72c8c1e1cb24ca4dbcc089f35c5264d357`. A fresh download of that exact base
archive matched **all 22 checked files**: implementation package, original tests,
`pyproject.toml` and `pytest.ini`. No reference implementation or previous agent
submission was used. See [verification](runs/commit0-base-verification.json).

Docker image:
`sha256:e826b149e029b596e92384c94e1725b2afaa87a508eebf89a71de73110875fb9`.
Checks run as an unprivileged user, without network, host mounts or credentials,
with 768 MiB memory and one CPU. Every check starts from the original scaffold,
overlays only generated implementation Python files, and restores original tests
and build settings. This is an adapted offline evaluation, not claimed parity
with the official Commit0 Modal environment.

| Check | Observed outcome | Interpretation |
|---|---|---|
| Untouched base scaffold | `_immutable` import error; no JUnit score | Expected incomplete source; missing score preserved |
| Scripted coding fixture | Paged reads, hash-checked writes, Docker tests, and final artifact selection exercised; full suite remains unscored | Adapter/error-path test, not an LLM result |
| Original storage test module on deliberately partial fixture | **3 passed, 10 failed, 13 collected** | Genuine test execution and score parsing; not full-library accuracy or model performance |
| First live society pilot | Stopped in round 4 after discovering tool-interface errors; no source writes or final submission | Development failure retained, not a zero or successful benchmark score |
| Corrected live restart | Blocked before output directory creation or any API request: Keychain OSStatus `-128` | Historical credential-access failure |
| First all-Luna run | 127 calls, 2 hires, 1 source write, final submission in round 10; selected source passes **6/201** on a separate grader recheck | Live development result; no recursive spawning |
| Paging-fix all-Luna run | 223 calls, 5 hires, 1 spawn, 1 source write; no final submission in 10 rounds | Recruitment works, but task completion fails |

The first live pilot used GPT-6-Sol for the bank and GPT-6-Luna workers. It made
41 confirmed API calls (8 applications, 4 bank reviews, 5 formation calls, 2 local
reviews, 22 work calls), consuming 8,840 reported output tokens and **$0.026650250**.
A 42nd reserved call was cancelled before sending because the run STOP file was
set. Maximum input was 7,676 bytes. The bank did issue approval/revision/rejection
feedback, but agents repeatedly supplied string-valued numeric tool arguments;
14 list actions were rejected. Two job openings lacked the required working
capital. No successful live hiring or post-initialization spawning is claimed.

The interface now uses integer tool examples and scales grant/hiring/spawning
examples with the configured maximum-call reserve. Regression tests verify both.
At that stage prompts clarified that independent root teams had separate
repositories; modules had to be delegated inside one team for integration.
Those fixes were exercised in the first all-Luna run. Paging fixes cap
oversized read pages at 100 lines, explain that baseline diagnostics describe the
original scaffold, and use `pytest --tb=line` to prevent verbose failures from
exhausting the grader output cap.

All paid work uses the existing shared $100 campaign ledger. The original total
ceiling for this task's live checks is **$3**. Before workflow repairs, the live
development runs consumed **$0.126562800**, leaving **$2.873437200**. The first two all-Luna runs account
for **$0.099912550** of that total. After the user explicitly requested GPT-6-Luna and the saved
OpenRouter key, a fresh launch attempted the same exact Keychain item; macOS again
returned `-128`. Neither blocked launch sent an API request. No credential was
printed or written to project files, and no old campaign reservation was reset.

Evidence: [machine-readable results](runs/commit0-results.json),
[first live replay](runs/commit0-sponsored-live-v1/replay.html),
[first live accounting](runs/commit0-sponsored-live-v1/audit.json),
[original storage JUnit](runs/commit0-storage-integration/checks/original-storage-tests/junit.xml).

## All-Luna live runs

The user supplied an OpenRouter credential after the operating-system Keychain
read failed. It was passed through a hidden terminal input into the runner's
process environment, not written to project files or supplied to test containers.
`configs/commit0-luna-models.json` selects `openai/gpt-6-luna` for both roles.
The earlier Sol-bank configuration remains available for reproducibility.

The first all-Luna run used 127 confirmed calls, 22,208 output tokens, and
**$0.034783825**. It hired two existing agents, spawned no new agents, and changed
only `tinydb/utils.py`. Maximum input was 11,552 bytes. Its 21 oversized read
requests were rejected by the earlier strict page limit. The submitted source
hit the grader output cap while printing extensive failure tracebacks.

The separately recorded recheck used the exact already-selected source and
unchanged original test selection, with only traceback presentation shortened.
It completed with **6 passed, 70 failed, 125 errors, 201 total**. Most errors are
caused by missing implementations such as the abstract storage methods. No API
calls or source edits occurred during this recheck. Its score was not retroactively
credited to the society ledger: the original run still records an unscored terminal
error and zero reward. Source hashes and recheck evidence are retained in
`runs/commit0-sponsored-luna-v1/grading-recheck.json`.

The second all-Luna run starts again from the original scaffold with bounded
oversized reads and explicit baseline/current-result instructions. It used
223 confirmed calls, 40,205 output tokens, and **$0.065128725**, below its separate
$0.25 ceiling. Population grew from 6 to 7: five hires and one spawn occurred,
including moves between teams. Maximum observed direct children was 2 and
recruitment depth was 1 in both all-Luna runs. No deeper recursive hierarchy was
observed. Maximum input in the second run was **12,229 / 24,000 bytes**.

The second run made 67 directory listings, 76 file reads and one source write,
with no in-run test action. Oversized-page rejections fell to zero. Its other
rejections were nine messages outside the allowed neighborhood (or duplicate
recipients) and one attempt to list a file as a directory. The final round
included a manager closing its team instead of submitting. No root submitted
before the deadline, so there is no final score, no reward, and no post-hoc
selection or grading of a different candidate.

Both accounting audits pass and all API reservations are settled. Actual model
IDs in the request logs are `openai/gpt-6-luna` for both roles. Exact framework
source snapshots are retained beside each run's implementation hashes. The runs
are not a controlled comparison because the interface changed. Their logs are
preserved unchanged; fresh workflow-repair pilots are recorded separately below.

| All-Luna run | Paid calls | Hires / new spawns | Largest input | Cost | Task outcome |
|---|---:|---:|---:|---:|---|
| First | 127 | 2 / 0 | 11,552 bytes | $0.034783825 | Selected source: 6/201 on separate recheck |
| Paging fix | 223 | 5 / 1 | 12,229 bytes | $0.065128725 | No submission; unscored |

Evidence: [first run](runs/commit0-sponsored-luna-v1/report.json),
[first selected-source recheck](runs/commit0-sponsored-luna-v1/grading-recheck.json),
[original-test JUnit](runs/commit0-sponsored-luna-v1/coding-recheck/checks/final-selected/junit.xml),
[second run](runs/commit0-sponsored-luna-v2/report.json), and
[second run replay](runs/commit0-sponsored-luna-v2/replay.html).

Those traces motivated concrete patch/test feedback and automatic coding deadlines
before increasing population or budgets. Repeated inspection, team churn, and
failures to submit dominated the earlier behavior.

These runs test a working protocol, not a claim of emergent ant-colony
intelligence or a demonstrated cost/quality improvement over a single agent.
All live source edits come from the experimental agents. Evaluation and paging
fixes change the framework, not the generated candidate implementation.

## Workflow diagnosis against the economy-team implementation

Local source and completed logs were reread before changing the coding loop.
`code-testing-v1/runs/tinydb-luna-k5-v5-parallel-s7` passes **157/201** with
552 paid calls (400 work), costing **$0.574352635**. Its 129 edit-labelled
attempts are not 129 verified successful edits: the log records 25 changed
candidate workspaces and 9 accepted public contributions. It also has 23 test
actions. The solo run `tinydb-luna-solo-k1-v4-s7` passes **157/201** with
100 paid calls (80 work), costing **$0.108191845**. The native original-EoM
repair run passes **139/201**, but includes extra repair compute and is not a
fresh matched baseline.

The older coding loop supplies sandbox commands, two recent results, persistent
notes, cumulative public source, remaining-turn reminders and automatic final
export. The earlier ant-colony loop instead repeatedly listed/read files, lost
useful work context, isolated root contributions, and depended on an optional
manager submission. Administrative-call fractions were similar (roughly 27%);
inspection inside work calls was the larger observed problem. No old ant input
hit the 24 KB cap, and no output reached its 8,192-token ceiling, so simply raising
the output ceiling is not supported by that evidence. Short receipts and missing
continuation cues can lose useful information even below the total input cap.
Later traces repeatedly requested files larger than a receipt, motivating a
separate larger-but-still-constant input/receipt preset. The older economy-team
runs also used strict structured actions and a 96,000-character context ceiling;
these are additional comparison differences, not evidence for banking versus auctions.

This diagnosis does not establish that banking or shared wealth is intrinsically
worse than auctions. Models, context, worker counts, work-call allowances and
integration rules differ. A causal comparison still needs matched conditions.

## Workflow repair validation

Free Docker exercise `runs/coding-workflow-docker-smoke` verified that an isolated
command can add a Python implementation file and team notes, execute the file,
import the validated source, integrate a checkpoint, invoke original tests, and
export the artifact. It used an independent scaffold and a scripted probe, not
a live candidate. The otherwise incomplete scaffold remains unscored on the
full suite. This is a framework check, not a model-performance result.

The first repaired all-Luna run, `commit0-workflow-repair-luna-v3`, kept six
initial agents, a maximum of twelve, ten rounds, four work calls per round,
24 KB input and 8,192 output tokens. A fresh run from the original scaffold used
**212 calls, 46,630 output tokens, $0.101891825**. It produced two actual file
changes and one shared checkpoint. Automatic final selection completed with
**12 passed, 64 failed, 125 errors / 201**. Its credit audit passes, all API calls
are settled, and maximum context was **18,636 / 24,000 bytes**.

That pilot exposed additional problems: 23 malformed responses lacked useful
recovery feedback, bulk command output was truncated without a clear notice,
and workers did not see their remaining turn count. The final implementation
adds private format-error receipts without free retries, explicit truncation,
larger bounded previous receipts, distinct JUnit failures, and remaining-call
reminders. It also fixes a transactional synchronization edge case caught by a
regression test. The v3 implementation snapshot intentionally predates these
later changes; its record has not been rewritten to claim it ran the final code.

The next fresh 24 KB run, `commit0-workflow-repair-luna-v4`, completed with
**29 passed, 172 failed, 0 errors / 201**, using **182 calls, 46,897 output
tokens, $0.104286750**. It made 13 actual file-change events across four files,
including repeated query repairs, 9 explicit test-tool calls, and 7 integrated
checkpoint versions. Two hires and no new spawns occurred; population remained
6 and observed depth/direct-child count were both 1. The audit passes with no
unresolved billing. Maximum context was **23,979 / 24,000 bytes**; four calls
omitted optional context. Fourteen malformed responses and three rejected
message actions remain, so feedback did not eliminate action errors.

The v4 trace also showed a syntax-invalid query update entering the shared code
and consuming several rounds of repairs. The new atomic syntax guard rejects
such updates before mutation. A free regression check using the exact frozen
round-4 artifact confirms rejection at `tinydb/queries.py:186` while preserving
the prior public source: `runs/syntax-guard-regression/result.json`. This is a
test of the observed failure, not a counterfactual benchmark score.

The larger-context preset is tested separately in v5 with the same six initial
agents, ten rounds, four work calls and all-Luna model identities. Its fixed
input/receipt caps are 64 KB/16 KB, and it includes the syntax guard. While that
run was active, final regression fixes made receipt packing use the largest
prefix that fits (instead of halving), account for double JSON escaping against
the entire message cap, and preserve source-file deletions in grading. Public
reward/cost observations were also added. Those later changes are unit-tested;
v5's exact source snapshot predates them, so its quality cannot be attributed to
those changes. Live logs and candidate code are never edited retroactively.


## Workflow repair v5: larger fixed coding context

The completed all-Luna `commit0-workflow-repair-luna-v5` run passes **137/201**
original TinyDB tests, with 64 failures and no errors. It makes 223 paid calls,
including 173 work calls, with 18 source-write events, 18 explicit test actions,
125 exec actions, and 2 reads. Three hires occur; population remains six, maximum
recruitment depth is one, and the direct-child maximum is two. This is not evidence
of a deep emergent colony.

The model reports 52,538 output tokens and **$0.172183175** in API charges.
Maximum serialized context is 36,238 bytes under the fixed 64,000-byte cap;
no optional-context omissions occur. Seventeen replies are invalid and still
charged. Final selection is the automatic public checkpoint, independent of score.
The independent accounting audit passes and no API reservations remain unresolved.

The current grader independently rechecked the exact selected source and again
obtained 137/201; implementation hashes match the original exported checkpoint.
See `runs/commit0-v5-preserved-source-recheck/result.json`. No human source repair
was applied. The run predates the task board, explicit public payoff schedule,
and final receipt-packing refinements. It cannot isolate any one fix's effect.
The earlier economy-team 157/201 result uses different work/context settings and
is not a matched baseline.

## Bank board and agent-defined strategies: Luna study

The user subsequently authorized a **$50 total cap** for new experiments,
superseding the earlier $3 development ceiling. The planned comparison allocates
six independent episodes at $2 each, totaling a **$12 maximum** for the completed
comparison. Actual costs, including interrupted development attempts, are
reported separately. The pre-existing shared campaign ledger's $100 cap and
unresolved-call protections remain active; nothing was reset.

Both conditions use the same repaired code, all-Luna bank/workers, six initial
agents, twelve-agent ceiling, ten rounds, four work calls per round, 64 KB inputs,
and 16 KB tool receipts. The sole configuration change is board size six versus
zero; the treatment includes its paid initial planning call and ongoing board
review overhead. Three fresh runs per condition start from the original scaffold.
They are independent stochastic repetitions, not controlled random-seed pairs.
No best-of selection or warm start is used. Source hashes are frozen in the plan;
queued runs refuse to launch if the implementation changes.

The initial attempted study, `luna-board-study-20261009`, was stopped after its
first board response exposed a grant/claim transition bug: the model described
an intended claim while approving it, and the runtime rejected the update before
issuing the grant. Its two interrupted episodes cost **$0.010445325** in total
(board $0.006953675, no-board $0.003491650); four queued episodes never started.
Both financial audits pass with no unresolved calls. Their missing final scores
are retained, not mixed into the restarted quality comparison.

A regression now treats an unowned 'claimed' status as intent only: ownership is
created solely by a subsequently validated grant. A claim with no approved grant
stays open. The restarted predeclared comparison is
`runs/luna-board-study-v2-20261009/plan.json`.


The board-enabled scripted admission check (`runs/board-scaling.json`) retains
six board entries for populations 10, 100 and 1,000. Every case makes two
applications, zero unfunded social calls, and two bank calls (initial planning
plus the round review). Peak serialized input is respectively 6,450, 6,450 and
6,451 bytes. This validates admission and context bounds only, not inference
quality, total constant computation, or large-population task throughput.

The updated HTML replay was inspected in the in-app browser. It displays the
bank's current directions, bounded task ownership and acceptance checks,
recursive teams, and expandable agent-chosen strategies. Round navigation
updates the ownership display. Raw experiment logs are not modified by replay
generation.


### Interrupted second attempt and conservative billing audit

The v2 study's first two episodes ended in round 8 after provider requests failed
without usage receipts. Four queued episodes failed preflight before any paid
request. Confirmed v2 charges are $0.130348425 (board) and $0.103064775 (no board).
Each unfinished request retains its full $0.028192 maximum reservation. Raw run
reports retain `status: error`, no terminal score/reward, and one unresolved API
call each. Their credit-ledger audits still reconcile; verified API usage is not
claimed for these episodes.

After inspecting the terminated processes, error reports, call records and
independent audits, an explicit operator audit changed only these two shared
campaign reservations to retained-error accounting. Their actual charges remain
unknown and their complete dollar exposure remains counted. No reservation was
released, no prior run was resumed, and neither failed HTTP request was replayed.
The audit and before/after totals are saved at
`runs/luna-board-study-v2-20261009/retained-reservations-audit.json`.

Separate, API-free grades of the automatically exported public checkpoints yield
**43/201** (board) and **62/201** (no board), both with zero test errors. Export
hashes match exactly; source was not changed and no reward was retroactively
credited. These are interrupted-artifact results, not completed-study outcomes.

The board trial showed sixteen stale-hash write rejections versus three in the
board-free trial. Coding observations now expose at most sixteen current file
hashes (paths bounded to 240 bytes), so agents that inspect through `exec` can use
a real concurrency token without another hash-only read. The stale-write guard
remains intact. This additional repair is covered by two regressions and is
included in both conditions of the fresh v3 comparison:
`runs/luna-board-study-v3-20261009/plan.json`. That comparison again allocates six
fresh episodes at $2 each; all development charges and retained uncertainties
count against the user's $50 ceiling.

### Completed v3 comparison

All six predeclared episodes completed ten rounds using `openai/gpt-6-luna` for
the bank and workers. Each terminal artifact is the automatic public checkpoint,
not a candidate selected by test score. Every terminal grade ran all 201 original
tests, with zero test errors; remaining tests failed. No human changed candidate
source. The independent study audit verifies the matching scaffold, frozen
implementation hashes, model IDs, context sizes, topology bounds, per-run caps,
and credit/API accounting for all six episodes.

| Condition | Repetition | Tests passed / 201 | API cost | Paid calls | Source-write events | Hires / new spawns |
|---|---:|---:|---:|---:|---:|---:|
| Board | 1 | 75 | $0.206296175 | 231 | 21 | 0 / 0 |
| Board | 2 | 61 | $0.163351910 | 188 | 17 | 0 / 0 |
| Board | 3 | 158 | $0.215802985 | 242 | 20 | 0 / 0 |
| No board | 1 | 23 | $0.150409450 | 181 | 13 | 1 / 0 |
| No board | 2 | 31 | $0.189593950 | 228 | 17 | 1 / 0 |
| No board | 3 | 41 | $0.208546450 | 242 | 16 | 2 / 0 |

The board's mean is **98/201** and median **75/201**, versus a mean of
**31.7/201** and median **31/201** without it. Total board cost is **$0.585451070**,
versus **$0.548549850** for the controls: about 6.7% more dollars for higher
observed quality in this sample. This is not a demonstrated absolute cost saving.
There are only three stochastic repetitions per condition, one library, and no
API seed control. The large within-condition variation limits generalization.
The earlier 137/201 development pilot and 157/201 economy-team result used
different implementations or settings and are not matched controls for this study.

The board conditions log **zero integration-conflict events**, versus **7, 13 and
10** in the controls. These count conflict occurrences, not unique files or all
redundant effort. The bank also visibly revises overlapping proposals: in board
run 2, rounds 1–3 each redirect a duplicate proposal to complementary work before
funding (event sequences 47, 118 and 225). No board updates are rejected and the
runtime exact-task duplicate guard needs no interventions in these six runs.
This supports the coordination mechanism; it does not establish perfect semantic
deduplication across differently worded tasks.

Every run starts and peaks at six agents; none spawns a new agent. Board teams
remain single-agent, with peak concurrent team counts 5, 4 and 5. Controls record
four hires in total and reach depth one, with at most one observed direct child.
The configured limit remains two direct children per manager recursively.
Workers change their own strategy strings 38, 27 and 43 times with the board,
and 32, 38 and 36 times without it. These are actual string changes, not counts of
repeated identical updates, and are not evidence of useful specialization.
No worker roles are predefined, but much of the observed division of work is
steered by the bank's module-level tasks. **A recursive ant-colony organization
has not emerged in this experiment.** A useful next test would compare coarse
bank objectives against fine decomposition, leaving subtask formation to grant
recipients; it should not mandate job titles or require hiring to manufacture a
desired tree.

Maximum observed input is **45,358 / 64,000 bytes**, with no optional-context
omissions. All bank proposal batches and boards stay within their two-proposal
and six-entry limits. No stale-file-hash action rejections recur after current
versions were added to observations. Remaining interface waste includes 44
invalid replies across board runs versus 23 in controls, rejected messages
outside local limits, and nine transactional rejections for an oversized notes
file in control run 3. These failures remain recorded and charged; read counts
and test executions are not automatically classified as redundant work.

### Final spending audit

The six completed episodes cost **$1.134000920**. Including both interrupted
study attempts, confirmed new-study charges are **$1.377859445**, plus a retained
uncertain maximum of **$0.056384**. Including all earlier recorded ant-colony
development pilots as well yields **$1.882783995 confirmed**, or at most
**$1.939167995** under the recorded reservations. This leaves **$48.060832005**
below the $50 cap even under that broader accounting. No paid runs remain active.
Unknown charges are not presented as confirmed payments or silently refunded.

Evidence: [predeclared plan](runs/luna-board-study-v3-20261009/plan.json),
[all-run analysis](runs/luna-board-study-v3-20261009/analysis.json),
[independent validation](runs/luna-board-study-v3-20261009/validation.json),
[budget accounting](runs/luna-board-study-v3-20261009/budget.json), and
[board run 3 replay](runs/luna-board-study-v3-20261009-board-r3/replay.html).

## ProgramBench high-reasoning study — started October 10, 2026

The prior Luna/Commit0 study above is complete. A separate ProgramBench study is
now recorded in `runs/programbench-mixed-high-20261010`. Its initial population
is 19 workers plus an Astra bank: 2 Astra, 8 Sol, and 10 Luna in total. All
inference requests explicitly use high reasoning, including grant applications,
reviews, the bank, and newly spawned workers. Roles are not assigned by tier.
The two-child recursive cap remains enforced; the total population ceiling is
32 including the bank, with 64,000 serialized input bytes per call.

The predeclared allocation is a $5 pilot plus four $20 episodes: colony and
single-Astra conditions on xsv and hexyl. A separate durable $100 study ledger
counts actual charges and every unsettled reservation across those episodes;
$15 is unallocated. Unknown calls stop queued spending without automatic
retries. Do not interpret this setup as a completed full-benchmark evaluation.

Preflight: **146 automated tests pass**, and Ruff passes. A real Docker fixture
verified ordinary reference probing, absence of the reference/API credentials
from work containers, independent builds, and checkpoint integration. Its
protected native evaluation was launched separately from agent experiments.
Two earlier free adapter checks found and fixed hidden configuration-file
handling and executable permission normalization before paid inference.

The paid pilot has started and dispatched requests with high reasoning. Its
bank created complementary task areas, and one manager autonomously spawned
a Sol helper. This is an observed delegation, not evidence that a useful
recursive ant colony has emerged. No final ProgramBench result is claimed in
this entry. Live state, charges, and completed outcomes are in
`study.json`, `campaign.sqlite`, episode `report.json`/`audit.json`, and
`analysis.json` in the study directory. Refresh the analysis with:

```sh
.venv/bin/python scripts/summarize_programbench_study.py runs/programbench-mixed-high-20261010
```

The requested single-agent extension adds single-Sol and single-Luna controls
on both tasks, alongside the already queued single-Astra controls. These use
high reasoning, the same tools, 30 rounds, up to four work calls per round, and
the same 64 KB context cap. Tests exercise each tier as exactly one actor and
verify that it makes only work calls, with no paid bank or applications.
Three additional allocation tests check the shared study ceiling. The original
148-test suite and all three added allocation checks pass; Ruff passes.

The supplemental controls are queued behind the primary study, using its
existing ledger and a separate frozen runtime. Their caps are $5 per Sol run
and $2 per Luna run: **$14 additional allocation, $99 combined, $1 unallocated**.
The original colony/Astra caps remain $20 per episode. The differing caps and
any resulting stops must remain visible in comparisons. `baseline-extension.json`
and `baseline-source-hashes.json` record the amendment; original source hashes
are preserved. This entry records configuration and checks, not final results.

## ProgramBench failure analysis and repaired rerun — October 10, 2026

The first study stopped after hexyl's native grader timed out starting a Docker
container. Its shared stop interrupted xsv at round 22. Confirmed spending was
$19.896917925, with no outstanding reservations. Historical xsv results were
623/1185 for the interrupted colony ($4.873356625) and 946/1182 for the
30-round single Astra ($13.351125). This is not a completed matched comparison.

Trace-based regressions reproduce and repair accepted applications being
misclassified as refusals, agents unable to request funding below their call
reserve, missing affordability signals, shell commands being counted as reads,
automatic team dissolution, and one root ending the whole society episode.
The new operating-cash guard prevents grants from consuming the bank's next
review reserve. Local renewal requests propagate recursively without a paid
polling call or a global roster; managers still decide approvals.

**164 automated tests and Ruff passed before launch.** Tests include zero-balance
child/grandchild renewal, a thousand-agent bounded-admission case, explicit
consent and incomplete replies, preserved accounting, stale readiness rejection,
post-generation grant limits, and financial versus grading failure isolation.
A fresh free Docker smoke run passed source isolation, reference probing,
independent builds and integration. Both xsv and hexyl image startup checks
returned success. No fresh native score is claimed by these preflight checks.

The repaired study is `runs/programbench-repaired-high-20261010`. It uses the
original `runs/programbench-mixed-high-20261010/campaign.sqlite`, preserving all
625 prior paid receipts. Its source snapshot is immutable. The six-round pilot
has started; eight fresh colony/single-agent conditions follow only after its
native evaluation and accounting gate pass. Total newly allocated ceilings are
$78; prior plus new maximum is $97.896917925, below the authorized $100.
Check `study.json`, `outcomes.json`, and episode reports for current completion;
this entry records launch, not a successful performance improvement.

## Parallel 40-agent experiment — October 10, 2026

At the user's request, `runs/programbench-colony40-high-20261010` adds one fresh
xsv condition with 40 initial agents (bank included), up to 64 total agents,
60 rounds, high reasoning, and a $15 episode ceiling. It runs beside the existing
20-agent colony and single-Astra study, without modifying their frozen runtime.
All requests use the original $100 campaign ledger, including prior charges.
Nominal queued ceilings are now competing upper bounds rather than an additive
allocation guarantee; actual charges plus live/uncertain reservations remain
subject to the shared global gate.

**178 tests passed before launch; Ruff passed.** New regressions cover matching
credit/provider reservations, Unicode input, unknown-model/message fallbacks,
receipt-limit breaches, work below the old conservative reservation, expiring
progress-conditioned grants, recursive manager renewal from child evidence,
scope changes, request ceilings, deferred funding, event-driven bank review,
stagnation review/grace, the exact 40-agent model mix, and parallel budget
admission with pending charges included. The free Docker smoke run at
`runs/programbench-colony40-smoke-20261010` passed isolation, reference probing,
independent building and source integration with zero model cost.

The live run was verified to load 39 workers plus one bank, 60 rounds and all
four opt-in mechanism flags. Its first high-reasoning call was dispatched, and
both this runtime and the previous study's runtime still matched their frozen
hashes. No native benchmark score or ant-colony emergence is claimed at launch.
## Collaboration prompt and bounded work contacts — 2026-10-10

Added the requested worker instruction: "When in team work with the team members
closely. You may also communicate with agents from other teams." Recursive hiring
and spawning already apply to every funded worker. Work now exposes at most
`peer_contacts` rotating funded peers in addition to direct parent/children;
the same symmetric contact list is retained across each round's work barriers.
Messages may cross teams, while budget authority and scratchpad access retain
their existing boundaries. No new model call is made to discover contacts.

Validation: **182 tests passed**, including cross-team delivery after the work
barrier, charged generation, private scratchpad isolation, rejection of unlisted
recipients, and bounded contacts/context at 6, 60, and 200 funded agents. Ruff
passed for the changed Python files. The running repaired and 40-agent studies'
frozen runtime hashes were verified unchanged; this change applies to fresh runs.

## Sponsored introductions and recursive recruitment — 2026-10-10

Bank revise/reject decisions can now introduce a free applicant to a named funded
owner. A bounded local queue carries the latest proposal; owners may forward an
introduction to a direct child without increasing their direct-child limit.
Forwarding preserves the expiry deadline. Introductions do not transfer funds or
authorize free conversation. Named offers and a host-side declared-scope index
replace reliance on accidental rotating-peer encounters for recruitment.

Managers can preapprove one scoped trial offer. Explicit acceptance of the exact
assignment and allowance hires without a second review generation; changed terms
still need paid review. Screening checks funding for the offer and retained
manager coordination runway. Recruitment budget receipts expose conservative
working-capital and screening/review requirements without creating money. Roles,
team size, recruitment, and subdivision remain agent choices.

Validation: **200 tests passed; Ruff passed for `ant_colony` and `tests`.** The 18
new recruitment cases cover bank introductions, forwarding from a saturated root,
recursive hiring/spawning through depth three, the two-child cap, next-round
newborn activation, missing/false acceptance, changed terms, duplicate hiring,
expiry, bounded queues, one-shot/cancellable offers, and insufficient liquidity.
Matching tests at 6, 60, and 200 initial agents find a relevant candidate outside
the rotating peer list using the same two model calls and bounded input context.
A full scripted round loop exercises referral, local forwarding and trial hiring
with persisted events and passes the financial audit.

Both existing study runtimes still match their frozen source hashes (44 files in
the repaired study and 47 in the 40-agent study). These changes apply to fresh
runs; no paid experiment was started for this fix. Scripted tests establish
mechanism correctness, not better benchmark performance or emergent organization.

## Fresh recruitment experiment launch — 2026-10-10

At the user's request, `runs/programbench-recruitment40-high-20261010` starts a
fresh xsv episode, `v4-recruitment40-xsv`, from the blank benchmark seed. The mix
matches the preceding 40-agent condition: four Astra including the bank, sixteen
Sol, and twenty Luna, all with high reasoning. Limits remain 60 rounds, 64 total
agents, two direct children, depth six, and a $15 episode ceiling. It shares the
original cumulative $100 ledger and two API request slots with the existing
experiments. Earlier runtimes and experiments were left in place.

Preflight passed **202 tests and Ruff**, plus the free Docker adapter smoke check
at `runs/programbench-recruitment-smoke-20261010`: source isolation, credential
isolation, reference probing, independent building, and integration. Launch now
accepts a unique episode ID and rejects IDs already present in the shared ledger.
The sponsorship event records the exact message-priced reservation, matching the
subsequent call event. Previously it recorded a full-context maximum, which made
the independent audit reject valid, smaller request-priced reservations. A new
full-run regression covers the request-priced audit without weakening validation.

All 48 frozen runtime files matched their launch hashes, including the new
recruitment module. The first high-reasoning request was dispatched. This entry
records launch only; final native score, actual cost, and useful recursive
organization remain to be measured.

## Campaign recovery and larger fixed capacities — 2026-10-11

The preceding recruitment episode stopped during round two when the older
`v2-colony-xsv` request timed out. It used $0.470979245 and its selected checkpoint
scored 329/1185. Three agents worked; two trial offers and one bank introduction
were recorded before interruption. No hires or spawns completed. This is an
interrupted experiment, not evidence that the recruitment fixes failed.

Manual review confirmed one unresolved TimeoutError reservation, $0.36384, with
no settled receipt or observed usage violation. The full amount remains counted
as unknown cost; the request is not retried. The ledger was backed up, the global
STOP archived, and the incident recorded in
`runs/campaign-recovery-20261011/accounting-review.json`. The user explicitly
authorized a $500 cumulative campaign ceiling. A durable ledger setting and
amendment record enforce that ceiling across new processes without resetting
the existing $54.00784462 of spending and reservations.

Future observed transport TimeoutErrors quarantine their episode and retain its
entire reservation. Other episodes may proceed within the same global dollar
gate. Missing/invalid billing, actual limit violations, pending calls at shutdown,
and failed audits still require a global stop. No request is automatically retried.
Historical sponsorship authorization may exceed the smaller request reservation;
the auditor now accepts a positive reservation within its authorized maximum,
while still rejecting unauthorized sponsors or amounts above that maximum.
Re-auditing the older 40-agent run succeeds without modifying historical logs.

Validation: **211 tests and Ruff passed**. New tests cover durable ceiling
amendments, preserved old charges and holds, shared remaining headroom, prevention
of retrying a quarantined episode, unrelated episode progress, global stops for
other billing failures, and sponsorship authorization ceilings. An expanded replay
of the previous bank observations, using four maximum-length proposal plans and
feedback fields, reached 26,611 bytes within the unchanged 32,000-byte coordination
cap. This is a fixture check; the hard context bound still applies to every call.

The fresh restart is `runs/programbench-recruitment40-capacity-high-20261011`,
episode `v5-recruitment40-capacity-xsv`. It retains 40 initial agents (four Astra
including the bank, sixteen Sol, twenty Luna), high reasoning, 60 rounds, a $15
episode ceiling, depth six, and a maximum of 64 agents including the bank.
Fixed capacities increase to four bank proposals/reviews, three local reviews,
and three direct children. Roles and actual recruitment remain voluntary. The
prompt favors unnamed matched openings unless there is a specific introduction
or agreed collaborator, reducing contention for the same visible peer.
The benchmark starts from its original seed; graded artifacts and hidden-test
feedback are not reused. Recruitment, prompts, and capacity changes are combined,
so this run alone cannot isolate which change affects performance.

## Explicit recruitment capital and outcome ownership — 2026-10-11

The live v5 run exposed a liquidity gap: a Luna child with 37,219 credits could
afford its own two-work-call reserve (30,824), so ordinary funding recovery did
not ask for support. A minimum trial hire plus screening and retained formation
runway required 42,960. The new paid-formation `recruitment_request` asks for one
concrete hire or spawn and computes the shortfall including the owner's working
capital and pending direct-child commitments. It goes through existing bounded
parent/bank review; no request creates money, model calls, or automatic hiring.
Existing funded agents can receive small shortfalls. Recruitment still requires
an explicit opening or spawn, and employment still requires consent.

Worker prompts now emphasize outcome ownership, independently verifiable parallel
subwork, interfaces, acceptance criteria, integration, and recursive authority
including for trial hires. Every introduction calls for a useful offer, forwarding,
a justified funding request, or a brief reason against recruitment. No roles,
population targets, or required depth are assigned. Bank and local reviewers see
the recruitment cost breakdown. Runtime operating top-ups preserve the child's
assignment. Funded rejection defers further requests through a cooldown instead
of permanently closing funding.

Validation: **237 tests passed; Ruff passed for `ant_colony` and `tests`.** New
cases reproduce the observed cash gap and exercise request, parent approval,
depth-two hire, spawn, exact one-credit shortfalls, rejection/revision, expiry,
scope changes, upstream liquidity propagation, consent, degree/depth limits,
and a full paid-phase scripted run with a valid accounting audit. Context tests
retain fixed local review limits at 6, 60, and 200 initial agents.

An expanded replay of 399 actual v5 call inputs, with new prompts and recruitment
metadata, caught a bank overflow when four maximum-length proposals coincided
with execution logs. Bank context construction now makes verbose evidence
optional only when needed, preserving all proposal/budget facts and execution
status, exit code, revision, counts and public scores. The replay now passes:
bank at most 31,807 bytes, application 19,486, formation 26,982, review 25,946,
and work 53,307. Bounds stay 32,000 for coordination and 64,000 for work. The
preflight record is `runs/delegation-preflight-20261011.json`. These are fixture
and mechanism checks, not evidence of better benchmark performance.

The preceding v5 runtime remains unchanged: all 48 frozen file hashes match.
The new condition is a fresh xsv seed with 40 initial agents including the bank
(4 Astra, 16 Sol, 20 Luna), all high reasoning, up to 60 rounds, maximum 64 total
agents, three direct children, depth six, four bank and three local reviews.
The episode ceiling is $15 within the original cumulative $500 campaign ledger.
Prompts, recruitment capital, renewal fixes, and evidence compaction change
together, so the comparison cannot isolate their individual effects.

Launch confirmed at `runs/programbench-delegation40-high-20261011`, episode
`v6-delegation40-xsv`. All 49 frozen runtime hashes match. At the launch check,
round one was in progress, two calls had settled for $0.081696, and all dispatched
requests used high reasoning. Final score and useful recursive organization
remain to be measured.

## All-Astra composition comparison — 2026-10-11

At the user's request, the launcher now supports `--model-mix all-astra`. The
condition contains 39 initial Astra workers and one Astra bank. Only Astra is
available for future spawns; the provider configuration also contains only Astra.
High reasoning, 60-round horizon, population ceiling 64 including bank, three
direct children, depth six, four bank and three local reviews, and $15 episode
ceiling stay fixed. The original $500 shared campaign ledger and all holds remain.

Validation: **238 tests and Ruff passed**, including the launcher. The new
configuration differs from the frozen v6 configuration only in `initial_models`
and `worker_models`. Every core runtime source file matches v6 byte-for-byte;
only the launcher changed for the model option and accurate experiment metadata.
No prompt, communication, funding, or stopping-policy repair is bundled into this
comparison. Model-priced reserves and illustrative budgets necessarily change.
This is one fresh run, not a replicated or equal-actual-spend comparison, and
40 initial agents need not become 40 active workers.

The reference mixed runs are both complete and independently audit successfully:
v6 scored 692/1185 (58.3966%) in 27 rounds for $7.847733490, while v5 scored
728/1182 (61.5905%) in 44 rounds for $13.153097435. Both reached depth one only.
The all-Astra experiment starts from the original blank benchmark seed; no
previous source artifacts, hidden-test results, or post-hoc diagnosis are included
in agent observations. Before launch the campaign accounted total was $75.008675545,
including the retained $0.36384 unresolved historical reservation.

Launch confirmed at `runs/programbench-all-astra40-high-20261011`, episode
`v7-all-astra40-xsv`. All 49 frozen files match launch hashes, the initial roster
contains 39 Astra workers, and the provider configuration and spawn allowlist
contain only Astra. The first high-reasoning call settled at $0.0736925 and the
next request was dispatched. `comparison-preflight.json` records the source and
configuration comparison. The existing 20-minute heartbeat now follows v7 through
native grading and will compare it with both mixed colonies and single Astra.

## User-amended all-Astra budget and hierarchy bias — 2026-10-11

The user then explicitly raised the all-Astra experiment total to $100, including
prior spending, and requested a hierarchy preference in every agent's prompt.
The live v7 process had immutable in-memory provider and society budgets and no
prompt reload or complete state-resume mechanism. Its episode-local STOP let the
in-flight request settle normally. Ten paid calls settled at $0.8007995 with no
unresolved requests; the accounting audit passes. The operator stop occurred in
round two. Automatic evaluation of its early checkpoint was unscored with
`native_result_with_errors`; this superseded attempt is not a complete treatment
result or zero accuracy. Events, source snapshots, and its STOP are preserved.

The shared ledger's new operator-only per-run amendment method requires a concrete
reason, no pending calls, and a cap covering all existing charges and holds within
the campaign ceiling. V7's cap was sealed at $0.8007995. The replacement attempt
receives $99.199200: combined caps $99.9999995, conservatively below $100. The
campaign ceiling remains $500 and the historical $0.36384 unknown charge is held.
The before-ledger snapshot and identical before/after call-row hashes are saved in
`runs/astra-budget-amendment-20261011/amendment.json` and `campaign-before.sqlite`.

New opt-in `hierarchy_bias` injects the same user preference into the bank and
all worker phases, inherited by spawned agents. It favors nested subprojects,
delegated outcome ownership with authority to hire/spawn, adequate runway,
integration, and compact upward reporting. Agents must still follow consent,
spending, contact, and child caps; no fixed specialist roles or depth quota is
introduced. Existing ownership is framed as a coordination boundary rather than
a prohibition on complementary help. Larger budget and prompting now change
together; this is not a model-only or equal-budget comparison against v6.

Validation: **240 tests and Ruff passed**. New tests verify inherited bank/worker
prompts and that sealed prior-attempt charges/holds plus the replacement cannot
exceed the total, preserving old call rows and refusing cap changes during pending
calls. The new run is `runs/programbench-astra40-hierarchy-high-20261011`, episode
`v8-all-astra40-hierarchy-xsv`. It starts from a fresh seed with 39 Astra workers
and one Astra bank, high reasoning and unchanged 60-round/degree/depth/context
limits. All 49 frozen source hashes match. At launch verification, two paid calls
settled for $0.15351; every observed prompt contained the hierarchy preference
and every dispatched call used high reasoning. The 20-minute heartbeat follows
v8 and reports experiment spending inclusive of v7.


## 2026-10-12 — Artifact contracts and code review

- Added opt-in frozen work contracts, source-bound runtime receipts, parent/bank
  handoff review, stale-evidence invalidation and waiting-work suppression.
- Repaired partial allocation updates, stale readiness on done tasks, missing
  finalization feedback, retirement handling and changes after public selection.
- Added fixed ten-agent Astra configuration and full prompt export.
- Offline validation: **415 tests passed**, Ruff passed across runtime/scripts/tests.
  Sample production prompts fit the fixed 64 KB input cap, including response schemas.
- Semantic acceptance remains a reviewer judgment. No benchmark improvement claim;
  the user-authorized run has a separate $100 settled-plus-reserved episode cap.

The early v17 pilot exposed repeated documentation/contract path friction. It was
stopped with valid accounting at $3.849748, zero outstanding API reservations, and
before protected evaluation began. Added direct read-only documentation access,
SPEC.md input pinning, precise path errors and documentation paging coverage.
**419 tests passed** after these fixes. The v18 restart is capped at $96.15, with
v17's sealed cost included: combined maximum $99.999748.

Recruitment diagnosis during v18 (not injected into the frozen run):
Round 2 funded three outcome owners. Owners a0001 and a0003 used
recruitment_request despite sufficient existing capital; the runtime recorded
recruitment_already_affordable, which creates a funding plan rather than a job.
Owner a0002 opened a job for a0006, but that candidate occupied a bank-review slot
that round. In round 3, a0001/a0003 opened actual jobs; a0002 replaced its opening
with a0005 and incorrectly described a separate funding request as another hire.
Three hires then completed in round 3, so six workers became funded. This is
prompt/interface ambiguity plus bounded scheduling latency, not a cash shortage.
Updated formation/bank guidance distinguishes funding, offers, consent and active
membership; clarifies the single-opening replacement rule; and adds explicit
activation action/phase metadata to funding plans. No automatic hire or spending
authority was added. Tests: 419 passed, Ruff passed. Production prompt previews
are saved in prompts-recruitment-refinement; they are offline and are NOT the
v18 treatment. The v18 immutable runtime retains its original prompts.

Bounded-memory clarification (offline refinement, not injected into v18):
Recorded work observations showed a0004 retaining an empty memory while repeatedly
inspecting shared files; other workers retained useful but sometimes stale notes.
Added concise guidance explaining bounded per-call history, replacement-memory
semantics, preservation of essential findings/interfaces/checks/next action, and
reuse of unchanged file versions and saved evidence. This is a prompt hypothesis,
not a measured improvement. No history/context ceilings were increased.

Large-command receipt correction (not injected into frozen v18):
Actual request c0000208/a0004 contained coding.result={"truncated": true} after a
large source-writing command. The command echo alone could exhaust the receipt
budget and discard status, exit code and changed-file information. Abbreviate
oversized echoed commands with a SHA-256 identity; preserve outcome facts and a
bounded changed-file summary when other metadata cannot fit. Original audit
results are never mutated. Two new regression cases cover successful/failed large
commands through the production observation, with oversized-metadata coverage.
421 tests pass. Replayed 137 actual tool receipts at zero API cost: all recorded
status/exit-code values retained, original audit objects unchanged, and every
visible receipt within 16,000 bytes (maximum 15,174). See receipt-replay-check.json.
The final offline prompt previews, including hiring and memory refinements, are
in prompts-final-preview. The paid v18 run retains its original frozen runtime.

Current-prompt/context replay: 263 recorded v18 request states repacked with the
latest prompts, activation metadata and corrected receipt display. All fit the
unchanged 64,000-byte cap, including response schemas (maximum 63,932 bytes).
Formal work contracts, tasks, assignments, money, proposals, board and action
schemas were preserved exactly. Four additional optional context blocks were
omitted; one previously lost latest receipt was restored. No API calls occurred.
This verifies context safety, not the behavioral efficacy of the prompt changes.
See prompt-replay-check.json.

Live prompt refinement authorized by the user during round 13:
The running system prompts remain frozen, but existing work observations read
auxiliary PROJECT_NOTES.md dynamically. Added a bounded, versioned guidance
helper that preserves agent notes, saves backups and records planned/applied
changes separately from runtime events. It refuses completed/evaluating episodes
and only applies during pending model requests. Tests cover preservation,
idempotence, bounds, audit records and completion guards. From call c0000415 this
is an operator-assisted adaptive run, not a wholly fixed-prompt baseline. Policies
v001-v003 target repeated reads, missing memory updates, stale receipts after
tracked report edits, and runtime rejection recovery. All seven funded workers
received guidance in recorded work requests. Formation/bank calls do not receive
project notes. Exact text is in reports/work-contracts-astra10-20261012/prompts-live.txt.

Trace-driven rejection visibility fix (current code, not hot-loaded into v18):
The partition owner requested more than twelve capture paths twice; the generic
Invalid probe rejection was in optional inbox context, while coding.result still
showed an older execution. Required private context now retains up to three recent
action rejection causes until a successful action of the same kind supersedes
them. Probe file/capture limit errors include the limit and requested count, and
the workbench instructions state the limits. Live v003 separately told the owner
the twelve-capture bound; call c0000430 requested twelve paths successfully.
432 tests pass; Ruff passes for changed runtime, helper and test files. A zero-API
stress replay added three maximum-length errors to 402 recorded worker requests:
all fit 64,000 bytes including schemas (maximum 63,972), with rejection details,
task, assignment, money, action schema and work contracts preserved. Thirty-nine
optional blocks were additionally omitted. See action-error-replay-check.json.
Behavioral improvement is not established by this context-safety replay.

The live run has two rejected malformed replies through round 13, both unfinished
JSON envelopes followed by whitespace until the output limit. No actions from
either reply executed. Concision/closing guidance may help, but does not replace
validation. A five-minute thread heartbeat now reviews traces and refines guidance
until completion, preserving the combined $100 cap and final-only native grading.

V18 final native result and accounting (2026-10-12, finished seq7297):
Final native score978/1182 =82.7411%; public diagnostic25/27 and independent
agent suite57/59 are distinct measures.204 native checks did not pass; hidden case
contents/failure breakdown were not inspected or returned to agents. The run
completed32 rounds via automatic_stagnation_checkpoint, without current accepted
team readiness (latest contracts: working4/revise3).616 model calls;2 malformed
responses rejected without actions;14 action rejections. Existing strict fixtures
and seeded failures were retained. Seven workers were funded from9 configured
workers plus the bank; one structural worker retired itself, no replacement.

V18 API spend$89.7758805 plus pilot$3.849748 = $93.6256285 under$100. Final
report.json/audit.json/outcomes.json agree; accounting_valid,usage_verified,
accounting_identity and complete_evaluation are true. Zero pending, unresolved or
quarantined run charges. Six unrelated historical holds totaling$4.94717 remain
unchanged; caps/deadline preserved. Model-usage cost is distinct from simulated
reward credits. No additional paid run or inference was launched by monitoring.

Actual16 recorded prompt variants are exported and verified against source events
in reports/work-contracts-astra10-20261012/prompts-recorded-v18. Verbatim system
texts are in system-prompts.txt;39 representative guidance requests cover all
seven delivered versions. Versionsv001-v007 reached111 requests;v008 was applied
but never delivered and cannot be credited with an effect. System prompts stayed
frozen; this is an operator-assisted adaptive run, not a controlled comparison.

Main remaining limitations: unaffordable parent control calls left child funds
stranded; repeated coordination/funding requests consumed remaining rights;
truncated diagnostics and missing memory caused repeated reads and stale beliefs;
tracked coverage edits invalidated receipts; ephemeral /tmp reports triggered
repeated full-suite regeneration. Contracts enforced honest blockers but did not
solve these scheduling/context failures. Repository-only fixes were not hot-loaded.
Last code validation remains432 tests passing and changed-file Ruff passing; no
code changed during final reporting. Detailed results and audit are in
reports/work-contracts-astra10-20261012/final-results.txt and final-verification.json.
Live notes edits stopped at native evaluation; heartbeat is PAUSED after verified
completion. No native-feedback continuation was performed; chat remains open.

Runtime recovery follow-up (2026-10-12, new experiment not launched):
Implemented opt-in bounded paid control calls for stranded funds and sleeping
executors, explicit proposal withdrawal, owner control reserves, durable host
execution evidence with bounded retrieval, and explicit incomplete checkpoint
selection. Source and test changes still invalidate contract evidence; later
reports can use the host record tool without changing submitted files. Prompts
explain ephemeral sandboxes and require compact evidence-based next steps.
444 tests pass, including 12 new zero-API recovery scenarios; changed-file Ruff
passes. A real two-container smoke recovered 66,600 bytes through 19 bounded
pages after /tmp disappeared, without source changes, API calls or native tests.
See reports/runtime-recovery-astra10-20261012/validation.json and
implementation-review.txt for exact checks, source hashes and limitations, and
prompts-final/system-prompts.txt for the actual offline prompt text.
The fresh 10-Astra fixed-prompt configuration is prepared; its paid budget is
pending user clarification. No new paid calls or campaign mutations occurred.

V19 launch authorized: user explicitly approved a new $100 cap. The fresh
10-Astra runtime-recovery run is active with fixed prompts and a five-hour
episode-specific deadline, leaving the old campaign deadline unchanged.
The new deadline isolation regression passes; full suite now445 passed and Ruff
passes. Initial paid bank call settled successfully. Details and actual starting
prompts: reports/runtime-recovery-astra10-20261012/launch.json and
prompts-recorded-start. The monitor is active with no treatment edits.

### v19 live-guidance authorization — 2026-10-12

User authorized continuous trace-based prompt refinement after the fixed prefix. Immutable v001 was applied at seq3288 via auxiliary work-observation project notes and first delivered at c0000297/seq3293; six requests verified, including a0008. Frozen runtime/system prompts and original agent notes are preserved. Exact text and audit are under `reports/runtime-recovery-astra10-20261012/prompts-live.txt` and `live-guidance/`. This is now an operator-assisted adaptive phase, not a wholly fixed-prompt or controlled causal comparison. The separate $100 cap, deadline1791864928.070796 and historical holds are unchanged; final native evaluation remains unread.

V19 inference ended — 2026-10-13 03:03 UTC
Bank selected public checkpoint29 explicitly incomplete at seq6790/round25; native
evaluation began6792 and its score is pending. All608 calls settled at$84.9015470,
zero v19 reservations; separate$100 cap and historical holds/deadlines preserved.
Public24/24 concerns checkpoint29's diagnostics;25 probes were observed in total,
including one final BOM/CSV probe without a local comparison or source repair.
Transformations is accepted/current and ready. Core was accepted, then renewed a
new boundary contract before completing team readiness; conformance remains blocked.
No source edits occurred in the final closeout. Live guidance edits have stopped.
Actual18 prompt variants and31 direct-delivery representatives for8 guidance
versions (154 guided requests) were exported and matched against recorded events
in reports/runtime-recovery-astra10-20261012/prompts-recorded-v19.
Remaining trace concerns: exact-minimum transfers lose work eligibility to formation
fees; sponsored applications consume parent reserves; pending bank handoffs wait
for periodic review after the first queue item; formation omits contract state;
status messages wake accepted workers; a new final probe was cut off before local
comparison by stagnation selection. Preserve these as future improvements, without
weakening strict acceptance or changing the frozen treatment. Final report/audit/
outcomes verification and native-score comparison remain pending evaluation.

V19 verified final completion — 2026-10-13 (supersedes pending evaluation notes)
Native999/1182 =84.5178%,183 not passed; public checkpoint29 diagnostic24/24
is separate. Bank-selected incomplete checkpoint at round25; no full task or
reference-parity claim. Transformations ready; core renewed closeout unfinished;
independent-conformance acceptance blocked. Final seq6806, worker exit0.
All608 calls settled at$84.9015470, pending$0, remaining$15.0984530 under the
separate$100 cap. Report/audit/outcomes, ledger and trace agree; accounting_valid,
usage_verified, accounting_identity and complete_evaluation are true. Prior
v17/v18 spending/caps, both deadlines and6 historical holds/$4.94717 preserved.
All58 frozen runtime hashes match. No paid continuation or private test inspection.
Compared descriptively with v18:21 more native passes (+1.77665 percentage points),
$4.8743335 lower episode cost,9 vs7 active workers,1 vs2 malformed replies,14 vs7
acceptance events. Coordination share rose22.13% to24.90%; invalidations12 to25.
Work memory usage rose92/406 to202/381; durable retrieval occurred4 times.
Priorities: reserve actual execution across coordination phases; drain review
queues; show authoritative phase-wide contract state; avoid status-message wakeups;
preserve completed milestones during bounded renewal; allow final probe comparison
before stagnation selection; move status reports outside tracked candidate source.
These are future improvements, not changes hot-loaded into the completed run.
Exported18 exact recorded prompt variants and31 delivery representatives covering
all8 guidance versions/154 work requests. Fixed prefix plus operator-assisted
adaptive phase; multiple mechanisms changed, so no causal attribution.
Report: reports/runtime-recovery-astra10-20261012/final-results.txt; assertions:
final-verification.json; actual prompts: prompts-recorded-v19/system-prompts.txt,
guidance-policies.txt and guidance-manifest.json. Runtime tests remain445 passing;
final edits are documentation only. Heartbeat PAUSED; chat left open.
