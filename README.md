# Metric Root-Cause Analysis

Live demo: https://metric-root-cause-analysis.onrender.com

Metric Root-Cause Analysis is a lightweight analytics project for detecting business-metric changes and investigating statistically supported associated contributors. The goal is to identify whether a recent metric shift is meaningful, then rank likely contributing segments without overstating causation.

Findings are associated contributors, not proven causes. Demo incidents are simulated and are intended for safe, reproducible testing of the investigation pipeline.

## Project goal

The project helps teams detect unusual business-metric movement, such as an unexpected drop in revenue, and investigate which dimensions are statistically associated with the change. It uses a structured workflow that emphasizes evidence, reproducibility, and clear caveats around overlap and confounding.

## Features

- data cleaning and quality checks
- anomaly detection for recent metric shifts
- contributor ranking with statistical safeguards
- confound and overlap warnings
- demo and real-data modes
- Gemini explanation generated only from already-computed evidence

## Architecture

Browser dashboard → FastAPI → statistical investigation → optional Gemini evidence summary

## Demo and real-data modes

Demo Mode uses a copy of the real dataset with a deliberately simulated incident. This allows the project to test the investigation workflow in a safe and reproducible way without presenting the result as evidence of a real production outage.

## Local run

```powershell
set PYTHONPATH=src && .venv\Scripts\python.exe -m uvicorn metric_rca.api:app --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000/
```

## API endpoints

- /health
- /investigate?mode=real|demo
- /investigate/explanation?mode=real|demo

These endpoints expose the investigation workflow and the optional evidence-backed explanation layer while keeping all findings framed as associated contributors rather than proven causes.

## Environment variables

The app uses the following environment variables without committed values:

- GEMINI_API_KEY
- GEMINI_MODEL
- EXPLANATION_RATE_LIMIT
- EXPLANATION_RATE_WINDOW_SECONDS

The public explanation endpoint is rate-limited to 3 requests per IP per hour by default. This guard helps reduce abusive or repeated Gemini explanation requests without affecting the rest of the API surface.

## Safety and interpretation

- Findings are associated contributors, not proven causes.
- Demo incidents are simulated.
- Overlap and confound warnings are treated as evidence of shared patterning, not proof of independent causal drivers.
- The Gemini explanation is generated only from already-computed investigation results and never from raw CSV analysis rerun in the prompt layer.
