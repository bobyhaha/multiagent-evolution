ACTUAL V18 RECORDED PROMPTS

Generated with scripts/export_prompts.py after inference ended at seq7281.
manifest.json indexes 16 distinct recorded system-prompt/phase combinations.
Each recorded-*.txt contains the exact system and observation messages; the
corresponding JSON also contains its structured response format. Exported messages
were checked against the original call_reserved events. The two contract rule
files match the frozen runtime values.

Live guidance entered optional PROJECT_NOTES context, not system-prompt reload.
Policies v001-v007 were delivered in 111 recorded requests. v008 was applied to
notes but never delivered before inference ended; no behavioral effect is claimed.
guidance-delivery-manifest.json indexes 39 exact representative requests across
all delivered versions, stored in ../live-guidance/requests. Complete policy
text, including the undelivered v008 proposal, is in ../prompts-live.txt.

This was an operator-assisted adaptive run, not a controlled causal comparison.
The repository prompts-current.txt is an offline preview and is not the run
treatment. No additional model inference was invoked for this export.
