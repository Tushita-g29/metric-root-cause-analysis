# Project Memory

This document is a dated handoff summary for future Codex or project continuation work.

Date: 2026-09-11

## Live URL
https://metric-root-cause-analysis.onrender.com

## Project objective
The project detects business-metric changes and investigates statistically supported associated contributors. It is designed to identify whether a recent shift is meaningful and which segments are associated with the change, without making unsupported causal claims.

## Dataset
- Dataset path: data/raw/google_merchandise_sales.csv

## Current architecture
- Dashboard: static HTML/CSS/JS served at /
- Backend: FastAPI
- Investigation pipeline: data cleaning -> anomaly detection -> hypothesis testing -> confound checks -> result formatting
- Optional explanation layer: Gemini summary from already-computed evidence only
- Public explanation endpoint protection: in-memory sliding-window IP rate limiter

## Real versus demo mode
- Real mode uses the actual local dataset.
- Demo mode uses a simulated direct-traffic revenue drop against a copied dataset and is clearly marked as simulated.

## Evidence-only Gemini rules
- Only the already-computed investigation result is sent to the model.
- No CSV access occurs in the explanation layer.
- No re-analysis is done in the prompt layer.
- Findings are described as associated contributors.
- Overlap/confound warnings are called out where present.
- No causal claims are presented as proven facts.

## Environment variables
Variable names only, never values:
- GEMINI_API_KEY
- GEMINI_MODEL
- EXPLANATION_RATE_LIMIT
- EXPLANATION_RATE_WINDOW_SECONDS

## Public endpoint protections
- GET /investigate/explanation is limited to 3 requests per IP per hour by default.
- The limiter is in-memory and resets when the process restarts.

## Local run command
set PYTHONPATH=src && .venv\Scripts\python.exe -m uvicorn metric_rca.api:app --host 127.0.0.1 --port 8000

## Test command
set PYTHONPATH=src && .venv\Scripts\python.exe -m pytest tests/test_gemini_explainer.py tests/test_api.py tests/test_rate_limit.py -q

## Completed work summary
- Sales data cleaning and quality checks implemented
- Anomaly detection implemented and validated
- Demo simulation implemented
- Contributor ranking and statistical safeguards implemented
- Confound and overlap warnings implemented
- Investigation orchestration implemented
- Dashboard served at the root path
- Public explanation endpoint implemented with rate limiting
- Gemini explanation layer implemented with evidence-only rules

## Known limitations
- The project is a prototype, not a production monitoring platform.
- The rate limiter is in-memory and not durable.
- The explanation endpoint still requires a valid Gemini key in the project-root .env file for live usage.
- The project intentionally avoids causal claims even when a ranked contributor pattern is strong.

## Recommended next study path
1. Start with data.py and investigation.py
2. Read anomaly.py and hypotheses.py next
3. Review confounds.py and rate_limit.py
4. Read the API and the dashboard files last
5. Use the tests as executable examples of intended behavior

## Interview-ready summary
- This project uses statistical evidence to rank associated contributors for a metric change.
- It does not claim root cause unless the data explicitly supports it, and it frames findings conservatively.
- Demo mode is intentionally simulated to test the pipeline safely.
- The dashboard is plain HTML/CSS/JavaScript served by FastAPI, with a static front end and a small backend service layer.
- The Gemini layer is optional and can only summarize evidence already computed by the investigation pipeline.
