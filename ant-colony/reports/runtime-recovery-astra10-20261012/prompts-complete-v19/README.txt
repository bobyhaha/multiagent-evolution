V19 complete recorded prompt package

all-recorded-requests.jsonl contains all608 recorded model requests, in trace order.
Each record includes call ID, phase, actor, round and the verbatim messages.
These include the frozen system instructions, task, dynamic observations, memory,
contracts, tool results, messages and live project-note guidance actually delivered.
The response-format object is reconstructed from each message list using the
frozen runtime builder, not independently captured as a network payload.

full-worker-prompt.txt is the full final work request c0000605 (a0001, round24),
including its complete system and observation text and reconstructed response schema.
full-worker-prompt.json provides the same request in structured form.

recorded-variants/ contains the existing18 system/phase variants, their complete
first requests, system-prompts.txt, all8 immutable guidance policies, and31 verified
representative guided requests. Policies can contain guidance never delivered to a
particular team; all-recorded-requests.jsonl records what each model actually saw.

Source: the completed v19 experiment's call_reserved events. No model responses,
protected benchmark test contents or credentials are included. Guidance was added
through work observations; system prompts remained frozen. This package describes
an operator-assisted adaptive experiment, not a single static prompt.
