from __future__ import annotations

from types import SimpleNamespace

import pytest

from metric_rca.gemini_explainer import generate_evidence_backed_explanation


class FakeGeminiClient:
    def __init__(self):
        self.calls = []

    class Models:
        def __init__(self, parent):
            self.parent = parent

        def generate_content(self, model, contents):
            self.parent.calls.append({"model": model, "contents": contents})
            return SimpleNamespace(text="This is a simulated anomaly with associated contributors and overlap warnings.")

    @property
    def models(self):
        return FakeGeminiClient.Models(self)


def test_generate_evidence_backed_explanation_uses_fake_client() -> None:
    fake_client = FakeGeminiClient()
    investigation = {
        "status": "anomaly_detected",
        "is_simulated": True,
        "anomaly": {"is_drop_anomaly": True, "drop_size": 0.45},
        "ranked_findings": [{"dimension": "traffic_channel", "p_value": 0.01, "effect_size": -0.34}],
        "confound_warnings": [{"dimension_pair": ["traffic_channel", "device_category"], "warning": "overlap"}],
    }

    result = generate_evidence_backed_explanation(investigation, client=fake_client)

    assert result["model"] == "gemini-2.5-flash-lite"
    assert "associated contributors" in result["explanation"] or "associated" in result["explanation"]
    assert fake_client.calls[0]["model"] == "gemini-2.5-flash-lite"
    assert "status" in fake_client.calls[0]["contents"]
    assert "confound_warnings" in fake_client.calls[0]["contents"]


def test_generate_evidence_backed_explanation_requires_dict() -> None:
    with pytest.raises(ValueError):
        generate_evidence_backed_explanation([])


def test_generate_evidence_backed_explanation_uses_env_override(monkeypatch) -> None:
    fake_client = FakeGeminiClient()
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    investigation = {
        "status": "no_anomaly",
        "is_simulated": False,
        "anomaly": {"is_drop_anomaly": False},
        "ranked_findings": [],
        "confound_warnings": [],
    }

    result = generate_evidence_backed_explanation(investigation, client=fake_client)

    assert result["model"] == "gemini-2.5-pro"
    assert fake_client.calls[0]["model"] == "gemini-2.5-pro"
