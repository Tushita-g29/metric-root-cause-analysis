# Product Requirements Document

## Live URL

https://metric-root-cause-analysis.onrender.com

## Product goal

This project detects business-metric changes and investigates statistically supported associated contributors. It is designed to help a user understand whether a recent shift in revenue or another key metric is meaningful, and which segments are most associated with the change.

The system intentionally avoids causal claims. Findings are associated contributors, not proven causes.

## Dataset and operating base

- Dataset path: data/raw/google_merchandise_sales.csv
- Primary backend: FastAPI
- Frontend: static HTML, CSS, and browser JavaScript
- Investigation flow: dashboard -> FastAPI -> statistical investigation -> optional Gemini evidence summary

## Core behaviors implemented

### Data handling
- The project reads the local raw sales CSV.
- Data cleaning validates required columns and normalizes fields.
- A data-quality report is created for row counts, date ranges, total revenue, and category distributions.

### Investigation modes
- Real mode: uses the actual local dataset.
- Demo mode: uses a copied dataset with a simulated direct-traffic revenue drop to exercise the workflow safely.

### Statistical investigation
- Daily revenue is aggregated by event date.
- A recent revenue drop is evaluated with Welch's t-test in the anomaly detector.
- Segment-level revenue declines are tested across fixed dimensions such as region, device category, product category, and traffic channel.
- Benjamini-Hochberg FDR adjustment is used for the ranking stage.
- Confound and overlap warnings are created when strongly associated dimensions or segments overlap.

### Output framing
- Investigation results are returned as JSON-safe dictionaries.
- Findings are presented as associated contributors, not causal explanations.
- If the anomaly is not statistically supported, the system reports no anomaly rather than claiming a problem.

## User-facing API behavior

- GET /health returns a simple service-status response.
- GET /investigate?mode=real|demo runs the real investigation pipeline.
- GET /investigate/explanation?mode=real|demo creates a concise text summary only after the investigation result already exists.

## Public explanation endpoint constraints

- The public explanation endpoint is limited to 3 requests per IP per hour by default.
- The limiter is in-memory and thread-safe.
- The override environment variable names are:
  - EXPLANATION_RATE_LIMIT
  - EXPLANATION_RATE_WINDOW_SECONDS

## Gemini constraints

The Gemini explanation layer is intentionally constrained to consume only already-computed investigation evidence.

Rules actually implemented:
- It reads only the existing investigation dictionary.
- It does not read the CSV again.
- It does not rerun analytics.
- It does not invent new statistical values.
- It uses wording like "associated contributors" instead of cause claims.
- It labels simulated incidents as simulated.
- It states when no statistically supported anomaly exists.
- It notes overlap/confound warnings when present.

## Environment variables

The system uses environment-variable names only, without committed values:
- GEMINI_API_KEY
- GEMINI_MODEL
- EXPLANATION_RATE_LIMIT
- EXPLANATION_RATE_WINDOW_SECONDS

## Completed scope

Implemented work includes:
- sales-data cleaning and validation
- anomaly detection
- demonstration workflow
- contribution ranking with statistical checks
- confound and overlap warnings
- FastAPI endpoints
- static dashboard
- optional Gemini explanation layer
- rate limiting for the public explanation endpoint

## Known limitations

- The project is a lightweight analytics prototype rather than a production-grade monitoring platform.
- The explanation endpoint requires a valid Gemini API key in the project-root .env file when used in a real environment.
- The rate limiter is in-memory only; it resets when the process restarts.
- The statistical pipeline is designed for evidence review and interpretation, not absolute causal proof.
- No database layer is present.
- The project does not include a real-time scheduler or alerting system.

## Future improvements

Possible next steps include:
- richer dashboard drilldowns and charts
- saved historical investigations
- standardized alerting workflows
- more robust config management
- broader metric families beyond revenue
- stronger user authentication and operational guardrails
