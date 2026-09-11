# Study Guide

This guide is designed for a beginner or a future contributor who wants to understand the project without relying on earlier chat history.

## How to approach the repository

Read the project in this order:
1. docs/PRD.md
2. docs/ARCHITECTURE.md
3. src/metric_rca/data.py
4. src/metric_rca/anomaly.py
5. src/metric_rca/demo.py
6. src/metric_rca/hypotheses.py
7. src/metric_rca/confounds.py
8. src/metric_rca/investigation.py
9. src/metric_rca/api.py
10. src/metric_rca/gemini_explainer.py
11. src/metric_rca/rate_limit.py
12. static dashboard files under src/metric_rca/static

## What each module does

### data.py
This is the ingestion and cleaning module. It handles:
- reading the CSV
- validating required column names
- cleaning text values
- converting data types
- summarizing data quality

A beginner should focus on how the module creates a clean DataFrame while preserving a stable structure for downstream analysis.

### anomaly.py
This module decides whether the business metric has changed meaningfully.

Key concepts:
- daily revenue aggregation
- baseline vs recent time window comparison
- Welch's t-test or equivalent statistical test
- effect size and p-value interpretation

This is where the system asks: "Is there an actual anomaly?"

### demo.py
This module creates a safe simulation of a business incident.

It is useful for demonstrating the workflow without interfering with real data. It copies the dataset and creates a variation in the direct-traffic revenue segment to simulate a drop.

### hypotheses.py
This module tries to explain the drop by testing segments.

It explores questions such as:
- Which device categories are weaker?
- Which channels are overrepresented in the drop?
- Which product lines seem associated with the metric decline?

It also applies multiple-testing correction through the Benjamini-Hochberg method so that ranking reflects evidence without overclaiming.

### confounds.py
This module checks for overlapping structure between dimensions.

For example:
- mobile users may also be concentrated in a specific region
- a segment may overlap heavily with another dimension

That matters because overlapping contributors are not independent causes. The warnings are designed to prevent a false sense of certainty.

### investigation.py
This module is the orchestrator. It ties together:
- data cleaning
- anomaly detection
- demo simulation
- ranked hypotheses
- confound checks
- result formatting

If you want the full workflow in one place, this is the file to read first.

### api.py
This is the FastAPI layer.

Routes serve:
- dashboard landing page
- health checks
- investigation runs
- explanation endpoints

The API is intentionally narrow and does not hide the logic inside a complex service layer.

### gemini_explainer.py
This module summarizes investigation results in plain English.

Important constraint: it is not a second analysis engine. It is a wrapper around the already-computed evidence. The explanation layer should summarize, not invent.

### rate_limit.py
This file protects the public explanation endpoint. It enforces a per-IP in-memory request limit and returns a 429 if the user exceeds the threshold.

## Useful interview talking points

### Why this project matters
It shows a solid understanding of:
- data cleaning
- statistical hypothesis testing
- evidence-based reporting
- API design
- front-end integration
- operational safety

### Why the project is honest
The project is careful not to say something is the root cause when the evidence only suggests a strong association. This is an important business and data-science habit.

### Why the dashboard is useful
The dashboard exposes the investigation result in a plain, understandable format for non-technical users while keeping the backend logic transparent and reproducible.

## Suggested exercises

1. Run the real investigation on the local dataset and inspect the JSON output.
2. Run the demo mode and compare the structure of the result.
3. Change the rate limit values in the environment and confirm behavior changes.
4. Remove or disable the Gemini API key and ensure the app still works in a non-AI mode.
5. Add a new segment dimension or a new report card while preserving the evidence-first design.

## Important design reminders

- The project is evidence-led, not causality-led.
- The investigation is an operational tool, not a final diagnosis.
- The code is intentionally simple enough to study and extend.
- Documentation is part of the product, not an afterthought.
