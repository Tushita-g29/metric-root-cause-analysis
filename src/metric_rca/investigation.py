from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from metric_rca.anomaly import aggregate_daily_revenue, detect_recent_revenue_drop
from metric_rca.confounds import (
    DEFAULT_HYPOTHESIS_DIMENSIONS,
    flag_segment_overlap_warnings,
    measure_ranked_segment_overlap,
)
from metric_rca.data import build_data_quality_report, load_and_clean_sales_data
from metric_rca.demo import create_default_demo_scenario
from metric_rca.hypotheses import rank_hypotheses, test_segment_revenue_declines


def _json_safe(value: Any) -> Any:
    """Convert pandas and numpy objects to JSON-serializable Python objects."""
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, pd.Series):
        return value.to_dict()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, set):
        return [_json_safe(v) for v in value]
    return value


def _day_window_valid(current_days: int, baseline_days: int) -> bool:
    """Return whether the day-window configuration is valid."""
    return isinstance(current_days, int) and isinstance(baseline_days, int) and current_days > 0 and baseline_days > 0


def run_investigation(
    csv_path: str,
    mode: str = "real",
    current_days: int = 28,
    baseline_days: int = 56,
    alpha: float = 0.05,
    top_n: int = 5,
) -> dict[str, Any]:
    """Run the full investigation flow for real or demo data and return JSON-safe analytics output."""
    if mode not in {"real", "demo"}:
        raise ValueError("mode must be either 'real' or 'demo'.")
    if not _day_window_valid(current_days, baseline_days):
        raise ValueError("current_days and baseline_days must both be positive integers.")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1.")
    if top_n <= 0:
        raise ValueError("top_n must be a positive integer.")

    cleaned_df = load_and_clean_sales_data(csv_path)
    data_quality = build_data_quality_report(cleaned_df)
    is_simulated = False
    scenario_metadata: dict[str, Any] = {}
    analysis_df = cleaned_df

    if mode == "demo":
        analysis_df, scenario_metadata = create_default_demo_scenario(cleaned_df)
        is_simulated = bool(scenario_metadata.get("is_simulated", False))

    daily_revenue = aggregate_daily_revenue(analysis_df)
    anomaly = detect_recent_revenue_drop(
        daily_revenue,
        current_days=current_days,
        baseline_days=baseline_days,
        alpha=alpha,
    )

    if not anomaly.get("is_drop_anomaly", False):
        result = {
            "status": "no_anomaly",
            "mode": mode,
            "is_simulated": is_simulated,
            "data_quality": _json_safe(data_quality),
            "anomaly": _json_safe(anomaly),
            "message": "No statistically supported drop anomaly was detected in the selected period.",
            "ranked_findings": [],
        }
        return _json_safe(result)

    hypothesis_results = test_segment_revenue_declines(
        analysis_df,
        baseline_start=anomaly["baseline_period_start"].strftime("%Y-%m-%d"),
        baseline_end=anomaly["baseline_period_end"].strftime("%Y-%m-%d"),
        current_start=anomaly["current_period_start"].strftime("%Y-%m-%d"),
        current_end=anomaly["current_period_end"].strftime("%Y-%m-%d"),
        dimensions=DEFAULT_HYPOTHESIS_DIMENSIONS,
        alpha=alpha,
    )

    ranked_findings = rank_hypotheses(hypothesis_results)
    ranked_findings = ranked_findings.head(int(top_n)).copy().reset_index(drop=True)

    overlap_df = measure_ranked_segment_overlap(
        analysis_df,
        ranked_findings,
        current_start=anomaly["current_period_start"].strftime("%Y-%m-%d"),
        current_end=anomaly["current_period_end"].strftime("%Y-%m-%d"),
        top_n=int(top_n),
    )
    overlap_warnings = flag_segment_overlap_warnings(overlap_df)

    result = {
        "status": "anomaly_detected",
        "mode": mode,
        "is_simulated": is_simulated,
        "scenario_metadata": _json_safe(scenario_metadata),
        "data_quality": _json_safe(data_quality),
        "anomaly": _json_safe(anomaly),
        "ranked_findings": _json_safe(ranked_findings.to_dict(orient="records")),
        "confound_warnings": _json_safe(overlap_warnings.to_dict(orient="records")),
        "message": (
            "A statistically supported drop anomaly was detected. The ranked findings below are contributor associations "
            "for the current period, not proven real-world causes."
        ),
    }
    return _json_safe(result)
