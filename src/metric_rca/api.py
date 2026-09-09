from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query

from metric_rca.gemini_explainer import generate_evidence_backed_explanation
from metric_rca.investigation import run_investigation

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = REPO_ROOT / "data" / "raw" / "google_merchandise_sales.csv"

app = FastAPI(title="Metric Root Cause Analysis API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Return the API health state."""
    return {"status": "ok"}


@app.get("/investigate")
def investigate(
    mode: Literal["real", "demo"] = Query(..., description="Analysis mode: real or demo."),
) -> dict:
    """Run the RCA workflow for the local sales dataset and return the JSON-safe result."""
    dataset_path = DATASET_PATH
    if not dataset_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Dataset not found at {dataset_path}. Expected the local sales CSV to exist in the repository data directory.",
        )

    try:
        return run_investigation(str(dataset_path), mode=mode)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Dataset not found at {dataset_path}. Expected the local sales CSV to exist in the repository data directory.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid investigation request: {exc}") from exc


@app.get("/investigate/explanation")
def investigate_explanation(
    mode: Literal["real", "demo"] = Query(..., description="Analysis mode: real or demo."),
) -> dict:
    """Run the RCA workflow and return a concise Gemini-backed explanation based only on the evidence."""
    dataset_path = DATASET_PATH
    if not dataset_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Dataset not found at {dataset_path}. Expected the local sales CSV to exist in the repository data directory.",
        )

    try:
        investigation_result = run_investigation(str(dataset_path), mode=mode)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Dataset not found at {dataset_path}. Expected the local sales CSV to exist in the repository data directory.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid investigation request: {exc}") from exc

    try:
        return generate_evidence_backed_explanation(investigation_result)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
