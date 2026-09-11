# Architecture

## High-level flow

Browser dashboard -> FastAPI -> investigation modules -> optional Gemini explanation

## Actual implemented components

### 1. Dashboard
- Static files live under src/metric_rca/static
- index.html, styles.css, and app.js serve the browser UI
- The dashboard checks /health and calls investigation endpoints when the user clicks buttons
- AI explanation is requested only after an explicit user action

### 2. FastAPI backend
- File: src/metric_rca/api.py
- Routes implemented:
  - GET /
  - GET /health
  - GET /investigate?mode=real|demo
  - GET /investigate/explanation?mode=real|demo
- The app resolves the dataset path from the repository structure rather than using a hardcoded Windows path

### 3. Data layer
- File: src/metric_rca/data.py
- Responsibilities:
  - read the CSV
  - validate required columns
  - normalize text values
  - convert numeric fields
  - remove invalid rows
  - return a data-quality report

### 4. Anomaly detection
- File: src/metric_rca/anomaly.py
- Responsibilities:
  - aggregate daily revenue
  - detect whether recent revenue shifts are statistically supported
  - compute a p-value and effect summary

### 5. Demo simulation
- File: src/metric_rca/demo.py
- Responsibilities:
  - create a copy of the dataset
  - simulate a direct-traffic revenue reduction in a date window
  - flag the result as simulated

### 6. Hypothesis testing and ranking
- File: src/metric_rca/hypotheses.py
- Responsibilities:
  - build daily revenue for baseline and current periods
  - compare segments by dimension
  - apply FDR correction
  - rank likely contributors

### 7. Confound and overlap detection
- File: src/metric_rca/confounds.py
- Responsibilities:
  - measure dimension associations
  - identify overlap between ranked segments
  - emit warnings that overlapping contributors should not be treated as independent causal factors

### 8. Investigation orchestration
- File: src/metric_rca/investigation.py
- Responsibilities:
  - call the cleaning, anomaly, demo, hypothesis, and confound modules
  - return JSON-safe results
  - integrate the end-to-end workflow for real and demo modes

### 9. Optional Gemini explanation layer
- File: src/metric_rca/gemini_explainer.py
- Responsibilities:
  - load the API key from the project-root .env using python-dotenv
  - default to gemini-3.5-flash-lite unless GEMINI_MODEL overrides it
  - create a prompt from already-computed evidence only
  - return explanation text and the model name

### 10. Public rate limiting
- File: src/metric_rca/rate_limit.py
- Responsibilities:
  - identify the client IP
  - restrict GET /investigate/explanation with an in-memory sliding window
  - return HTTP 429 when the limit is exceeded

## Data flow for a real investigation

1. Browser requests /investigate?mode=real
2. FastAPI resolves the dataset path under the repository
3. Investigation pipeline loads and cleans the CSV
4. Daily revenue is aggregated and anomaly detection is run
5. Segments are tested and ranked by statistical support
6. Confounding and overlap warnings are attached
7. JSON-safe result is returned to the browser

## Data flow for an AI explanation

1. User clicks Generate AI Explanation on the dashboard
2. Browser calls /investigate/explanation?mode=real|demo
3. FastAPI enforces the public endpoint rate limiter
4. Investigation result is computed and reused
5. Only status, simulation flag, anomaly metrics, ranked findings, and confound warnings are sent to Gemini
6. The Gemini prompt asks for concise, evidence-based, non-causal language
7. The explanation is returned to the client

## Key design principle

The system is deliberately framed as evidence discovery, not proof of cause. That principle applies to both the dashboard wording and the Gemini prompt.
