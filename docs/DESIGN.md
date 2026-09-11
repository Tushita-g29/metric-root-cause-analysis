# Design Notes

## Design philosophy

The project is intentionally simple, transparent, and beginner-friendly. The objective is to make investigation logic easy to follow without hiding statistical nuance behind a black-box pipeline.

## Frontend design

The browser dashboard is built with plain HTML, CSS, and browser JavaScript.

Why this design was chosen:
- no dependency installation needed for the UI
- easy to serve with FastAPI
- transparent and portable for a portfolio project
- suitable for a simple analytics interface without a framework

## Backend design

The backend uses FastAPI because it exposes a clean route structure and keeps the project easy to test.

The API is intentionally split into:
- standard investigation routes
- a public explanation route that is rate-limited
- evidence-only summarization logic that is separate from the statistical pipeline

## Investigation framing

The design emphasizes that findings are not final explanations.

This is reflected in:
- the wording in the dashboard
- the prompt sent to Gemini
- the overlap/confound warning cards
- the project documentation and team communication

## Data model design

The investigation returns a JSON-safe dictionary, which is essential for both the browser and the API layer. The project converts pandas and numpy objects into plain Python values before returning them.

## Dashboard UX goals

- show whether the investigation succeeded
- show whether the result is simulated or real
- show the anomaly summary clearly
- show data-quality information
- present the ranked contributors in a table
- explain overlap/confound warnings in clear, non-causal language
- keep the AI explanation in a separate section until explicitly requested

## Security and safety design

The public explanation endpoint is intentionally limited and framed as a utility for summarizing evidence, not as an unrestricted AI endpoint.

Key constraints:
- no key exposure in the browser
- no raw CSV access in the Gemini prompt layer
- no causal claim generation
- in-memory rate limiting only

## What this design does not do

This project does not include:
- a database
- authentication or authorization logic
- real-time monitoring infrastructure
- scheduled job execution
- an external API gateway or service mesh
- a custom ML model training pipeline
