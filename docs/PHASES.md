# Project Phases

## Completed work

### Phase 1: Data preparation
- Load and clean the local sales CSV
- Validate required columns
- Standardize text and numeric values
- Represent the cleaned dataset and data-quality summary

### Phase 2: Anomaly detection
- Aggregate daily revenue
- Compare recent periods with baseline periods
- Use a statistical test to decide if a drop is meaningful
- Return anomaly metadata for the dashboard and investigation pipeline

### Phase 3: Demo simulation
- Create a simulated direct-traffic outage
- Apply the change only to a copied dataset
- Label the result as simulated and keep it separate from the actual data mode

### Phase 4: Contributor ranking
- Compare revenue shifts across segments and dimensions
- Apply multiple testing correction
- Rank the most relevant contributor segments

### Phase 5: Confound checks
- Measure shared structure between dimensions
- Detect overlap and confounding concerns
- Warn that overlap does not prove cause

### Phase 6: Investigation orchestration
- Combine all pipeline stages into one consistent output
- Return JSON-safe results for the browser and API consumers

### Phase 7: Dashboard and API polish
- Serve the static dashboard at /
- Expose health and investigation endpoints
- Provide real and demo investigation actions in the UI

### Phase 8: Gemini explanation layer
- Reuse the already-computed investigation result
- Build a prompt from a narrow evidence subset only
- Return explanation text and model name

### Phase 9: Abuse protection
- Add a thread-safe in-memory public endpoint rate limiter
- Apply it only to GET /investigate/explanation
- Include environment-variable-based overrides

## Known limitations

- The system does not perform continuous monitoring or scheduled alerts.
- The in-memory limiter resets on process restart.
- The real dataset is not transformed in place; the investigation creates derived results from the cleaned version.
- The project intentionally does not claim causality.

## Future improvements

Possible roadmap items:
- richer historical trend analysis
- external metric inputs and time windows beyond the current dataset
- more advanced anomaly scoring across multiple KPIs
- saved investigation snapshots
- additional UX polish for business stakeholders
- more operational logging and observability
