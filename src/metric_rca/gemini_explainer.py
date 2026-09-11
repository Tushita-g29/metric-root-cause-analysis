from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from google import genai
except Exception:  # pragma: no cover - handled in tests via dependency injection
    genai = None


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _load_gemini_api_key() -> str:
    load_dotenv(_project_root() / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to the project-root .env file before using Gemini explanations.")
    return api_key


def _normalize_evidence(investigation_result: dict[str, Any]) -> dict[str, Any]:
    """Extract only the evidence that may be presented to Gemini."""
    return {
        "status": investigation_result.get("status"),
        "is_simulated": investigation_result.get("is_simulated"),
        "anomaly": investigation_result.get("anomaly"),
        "ranked_findings": investigation_result.get("ranked_findings"),
        "confound_warnings": investigation_result.get("confound_warnings"),
    }


def _build_prompt(evidence: dict[str, Any]) -> str:
    return (
        "You are summarizing this investigation strictly from the supplied evidence. "
        "Write concise plain English for a business audience. "
        "Use the phrase 'associated contributors' instead of claiming root cause. "
        "Never state a causal relationship as a proven cause. "
        "If the incident was simulated, clearly label it as simulated. "
        "If no statistically supported anomaly exists, say that no statistically supported anomaly was detected. "
        "If there are overlap/confound warnings, mention them as overlap or confounding concerns, not as proof of cause. "
        "Base your explanation only on the evidence below.\n\n"
        f"Evidence: {json.dumps(evidence, ensure_ascii=True, sort_keys=True)}"
    )


def generate_evidence_backed_explanation(
    investigation_result: dict[str, Any],
    client: Any | None = None,
) -> dict[str, Any]:
    """Generate a concise explanation from the already-computed investigation result only."""
    if not isinstance(investigation_result, dict):
        raise ValueError("investigation_result must be a dictionary.")

    evidence = _normalize_evidence(investigation_result)
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    if client is None:
        if genai is None:
            raise RuntimeError("Google Gen AI SDK is unavailable.")
        api_key = _load_gemini_api_key()
        client = genai.Client(api_key=api_key)

    prompt = _build_prompt(evidence)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
    )

    text = getattr(response, "text", None)
    if text is None:
        text = str(response)

    return {
        "explanation": text,
        "model": model_name,
    }
