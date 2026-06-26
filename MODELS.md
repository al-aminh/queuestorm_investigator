# Model Strategy

## Default model

QueueStorm Investigator uses a deterministic rule-based model by default.

It runs inside the FastAPI process and requires no external model, GPU, model download, or API key.

## Why rule-based is default

The hackathon task requires stable fintech support decisions:

- exact response schema
- exact enum values
- evidence-backed transaction selection
- safe escalation
- no credential requests
- no unauthorized refund/reversal promises
- robust handling of malformed and multilingual inputs

A deterministic pipeline is better for these requirements because it is fast, reproducible, explainable, and low-cost.

## What the rule model does

The rule model handles:

1. Prompt-injection detection
2. Phishing/social-engineering detection
3. Case classification
4. Transaction matching score
5. Duplicate payment grouping
6. Evidence verdict
7. Department routing
8. Severity assignment
9. Human-review decision
10. Safe agent/customer text generation
11. Final response sanitization

## Optional LLM usage

LLM usage is not required and is disabled by default.

Environment variables are included only for future optional text polishing:

```env
USE_LLM=false
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
REQUEST_TIMEOUT_SECONDS=25
```

If a team later enables an LLM, the deterministic rules should still remain the source of truth for:

- `relevant_transaction_id`
- `evidence_verdict`
- `case_type`
- `department`
- `severity`
- `human_review_required`
- `reason_codes`
- safety sanitizer results

The LLM should only polish text after the deterministic decision has already been made.

## Cost reasoning

Default runtime cost is zero beyond server hosting because no paid model is called.

This avoids:

- API key management during judging
- rate-limit failures
- external latency
- quota exhaustion
- nondeterministic model outputs

## Where the model runs

The deterministic model runs locally inside the Python API container/process.

No data leaves the service.
