# Provider and compute plan

No credentials were available in this task's process. The SF Compute usage link
opened a sign-in page, so account balance and remaining credits were not verified.
No model calls, GPU allocation, purchases or account changes were performed.

## Recommended sequence

Start with the scripted checks, then a four-agent OpenRouter pilot to check JSON
validity, communication and cost. Use `qwen/qwen3-32b` as an initial economical
backbone, with `qwen/qwen3.8-flash` as a second condition. Use Qwen3-8B on an SF
Compute GPU when repeated calls make a fixed model deployment economical or when
you need reproducible weights and a fixed serving stack. These are pilot choices,
not demonstrated best models for this task.

The [OpenRouter model API](https://openrouter.ai/api/v1/models) returned the
following prices when read September 25, 2026 (USD per million tokens):

| Model ID | Input | Output |
|---|---:|---:|
| `qwen/qwen3-32b` | 0.080 | 0.280 |
| `qwen/qwen3-8b` | 0.117 | 0.455 |
| `qwen/qwen3.8-flash` | 0.150 | 0.470 |
| `qwen/qwen3.5-35b-a3b` | 0.3125 | 1.250 |
| `qwen/qwen3.8-27b` | 0.420 | 3.000 |

These are API catalogue quotes, not guaranteed provider-specific invoice rates;
the human-facing page differed for one model. Refresh with `test.py models` and
save the result. Pin a provider using `--provider-order` when comparing model
behavior across runs. The runner disables provider fallback when an order is set,
and logs the returned provider/model identifiers. It supports an explicit
thinking-mode switch; use the same setting across comparisons.

For intuition, 1,000 calls averaging 3,000 input and 700 output tokens would cost
approximately $0.44 at the quoted Qwen3-32B token rates, before retries, extra
trigger calls, routing differences, or other charges. This is only a planning
calculation; real prompts may be much longer. The conservative runtime reservation
uses bytes as an input-token upper estimate and configurable price bounds, so it
will intentionally stop earlier than an optimistic price estimate suggests.

Use an upstream API-key spending limit in addition to the local budget. OpenRouter
documents [key-level limits](https://openrouter.ai/docs/guides/overview/auth/management-api-keys).
The program does not create or change keys. It sends OpenRouter credentials only
to the official OpenRouter base URL and refuses authenticated redirects.

## SF Compute is GPU infrastructure, not the same token API

The [Autoresearch documentation](https://autoresearch.sfcompute.com/llms.txt)
and [OpenAPI schema](https://autoresearch.sfcompute.com/openapi.json) expose node,
command, usage, and billing operations. This is distinct from the OpenRouter chat
endpoint. The current usage read is `GET /preview/usage` with a bearer token:

```bash
# Supply SFC_API_KEY in the shell, not in source control or the command string.
python3 test.py sf-usage
```

The implementation includes a read-only usage client and a GPU-node runner. It
does not automatically allocate or stop nodes because no account authentication
or priced deployment was available to verify. Current API schemas were downloaded
to `research/sfcompute-openapi.json` for inspection.

For a provisioned **dedicated experiment node**, copy the code and run:

```bash
python infra/run_qwen_local.py --model Qwen/Qwen3-8B \
  --project capital --episodes 4 --max-calls 150 \
  --wall-seconds 1800 --out runs/sf-qwen8b-pilot
```

The node needs an installed vLLM version compatible with the model, such as the
platform's documented `vllm-0.26-cuda12.9` image if still available. Confirm image
availability and runtime versions at allocation. The script uses a loopback-only
server and runs the experiment on the same node, avoiding a publicly exposed model
endpoint. It refuses to borrow an already listening service, waits for the desired
model ID, bounds startup and experiment duration, and terminates the serving
process group on exit. **It does not stop cloud-node billing.** Collect artifacts
and stop that node through the platform afterward.

The [Qwen3-8B model card](https://huggingface.co/Qwen/Qwen3-8B) documents vLLM
serving and switching off thinking. The runner uses the compatible API and
`chat_template_kwargs.enable_thinking=false` by default. A larger Qwen model may
need additional GPU memory or tensor parallelism; the script exposes
`--tensor-parallel-size` without claiming a tested hardware configuration.

For an existing service, use the direct adapter:

```bash
python test.py run --provider compatible --model Qwen/Qwen3-8B \
  --base-url http://127.0.0.1:8000/v1 --api-key-env SOCIETY_LOCAL_UNUSED_KEY \
  --agents 4 --episodes 4 --eval-episodes 2 --steps 16 \
  --max-calls 150 --max-usd 10 --out runs/local-qwen
```

For self-hosted inference the USD reservation is only a token-equivalent local
guard, **not actual GPU rent**. Use platform spending controls, a wall-time limit,
the quoted node rate and minimum billing period to budget real compute. A fresh
node, its downloads, idle time and minimum charges can dominate a tiny pilot.

## Cost accounting and failure behavior

- The budget covers action, trigger, membership, hiring, acceptance, reflection,
  mutation and institution calls. A sweep shares one allowance across cells.
- Input-byte and maximum-output reservations are made before sending a request.
  They remain charged to the local allowance on uncertain transport failures.
- No automatic retry risks issuing a second billable call after an ambiguous
  response. The completed episode checkpoint can be resumed with prior usage.
- Invalid JSON is logged and becomes an invalid decision. It never receives a
  scripted fallback answer in a live experiment.
- API usage, actual provider-reported cost when available, latency and request IDs
  are logged. A missing reported cost does not prove a request was free.
- HTTP behavior, payloads, spend limits, JSON failures and error handling were
  exercised against a local fake server. Live OpenRouter, vLLM and SF hardware
  compatibility remain unverified until an authenticated pilot is run.
