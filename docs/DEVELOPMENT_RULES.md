# Development Rules

## Scope rules

This repository has a clear design rule: do not expand scope beyond the actual implemented investigation workflow.

- Keep the project focused on metric investigation and contributor association.
- Do not add database code.
- Do not add new dependencies.
- Do not modify .env values or commit secrets.
- Do not change the raw dataset.
- Do not alter the statistical pipeline or analytics logic without a clear reason.

## Evidence-first rules

- Rankings are based on statistical signals, not proof of causation.
- Findings are described as associated contributors.
- Demo incidents are explicitly marked as simulated.
- No anomaly is reported when the evidence does not support it.

## Gemini rules

The optional Gemini layer must only summarize already-computed evidence.

Actual rules:
- do not read the CSV again
- do not rerun analytics in the prompt layer
- do not invent values
- only send the computed result to the API model call
- output concise plain English
- never use causal wording as a proven claim
- mention overlap/confound warnings when they exist

## Rate-limit rules

The public explanation endpoint is protected by an in-memory sliding-window limiter.

Default behavior:
- 3 requests per IP per 3600 seconds

Environment variables names:
- EXPLANATION_RATE_LIMIT
- EXPLANATION_RATE_WINDOW_SECONDS

## Local environment rules

The project expects these environment-variable names to exist when the optional Gemini explanation is used:
- GEMINI_API_KEY
- GEMINI_MODEL

No values are checked into the repository.

## Run and test rules

For local development, use:

set PYTHONPATH=src && .venv\Scripts\python.exe -m uvicorn metric_rca.api:app --host 127.0.0.1 --port 8000

For tests, use:

set PYTHONPATH=src && .venv\Scripts\python.exe -m pytest tests/test_gemini_explainer.py tests/test_api.py tests/test_rate_limit.py -q

## Working assumptions

- The browser dashboard is a portfolio-friendly UI and does not replace the API layer.
- The backend is the main source of truth for the investigation workflow.
- The investigation output is JSON-safe and intentionally simple for frontend rendering.
- The project is a safe, educational RCA prototype with explicit caveats.
