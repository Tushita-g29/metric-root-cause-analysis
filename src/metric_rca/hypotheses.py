from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import t, ttest_ind
from statsmodels.stats.multitest import multipletests

DEFAULT_HYPOTHESIS_DIMENSIONS = [
    "region",
    "device_category",
    "product_category",
    "traffic_channel",
]


def _build_daily_revenue_for_period(df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    """Return one row per calendar day with zero revenue on no-purchase days."""
    try:
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
    except Exception as exc:
        raise ValueError("baseline_start, baseline_end, current_start, and current_end must be valid dates.") from exc

    if start_dt > end_dt:
        raise ValueError("Period start date must be on or before the end date.")

    full_range = pd.date_range(start=start_dt, end=end_dt, freq="D")

    if df.empty:
        return pd.DataFrame({"event_date": full_range, "daily_revenue": 0.0})

    filtered = df.loc[(df["event_date"] >= start_dt) & (df["event_date"] <= end_dt)].copy()
    daily = (
        filtered.assign(event_date=pd.to_datetime(filtered["event_date"]))
        .groupby("event_date", as_index=False)["item_revenue_usd"]
        .sum()
        .rename(columns={"item_revenue_usd": "daily_revenue"})
    )

    full = pd.DataFrame({"event_date": full_range})
    result = full.merge(daily, on="event_date", how="left").fillna({"daily_revenue": 0.0})
    return result.sort_values("event_date").reset_index(drop=True)


def _compute_mean_difference_ci(
    current_values: np.ndarray,
    baseline_values: np.ndarray,
    current_avg: float,
    baseline_avg: float,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Return a 95% confidence interval for the difference in average daily revenue."""
    diff_mean = current_avg - baseline_avg

    if len(current_values) == 0 or len(baseline_values) == 0:
        return diff_mean, diff_mean

    current_var = float(np.var(current_values, ddof=1)) if len(current_values) > 1 else 0.0
    baseline_var = float(np.var(baseline_values, ddof=1)) if len(baseline_values) > 1 else 0.0
    se = np.sqrt((current_var / len(current_values)) + (baseline_var / len(baseline_values)))

    if se == 0 or not np.isfinite(se):
        return diff_mean, diff_mean

    if len(current_values) > 1 and len(baseline_values) > 1:
        df = (
            ((current_var / len(current_values)) + (baseline_var / len(baseline_values))) ** 2
            / (
                ((current_var / len(current_values)) ** 2) / (len(current_values) - 1)
                + ((baseline_var / len(baseline_values)) ** 2) / (len(baseline_values) - 1)
            )
        )
    else:
        df = 1.0

    critical = float(t.ppf(1 - alpha / 2, df=max(df, 1)))
    margin = critical * se
    return diff_mean - margin, diff_mean + margin


def _build_bh_adjusted_pvalues(raw_p_values: pd.Series, alpha: float = 0.05) -> pd.Series:
    """Apply Benjamini-Hochberg FDR correction to the raw p-values."""
    valid = raw_p_values.notna()
    if not valid.any():
        return pd.Series(np.nan, index=raw_p_values.index, dtype=float)

    adjusted = pd.Series(np.nan, index=raw_p_values.index, dtype=float)
    _, p_adj, _, _ = multipletests(raw_p_values.loc[valid].to_numpy(dtype=float), alpha=alpha, method="fdr_bh")
    adjusted.loc[valid] = p_adj
    return adjusted


def test_segment_revenue_declines(
    cleaned_df: pd.DataFrame,
    baseline_start: str,
    baseline_end: str,
    current_start: str,
    current_end: str,
    dimensions: list[str] = DEFAULT_HYPOTHESIS_DIMENSIONS,
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Evaluate segment-level revenue contributors for association with a recent decline. This is not proof of causation."""
    if cleaned_df.empty:
        raise ValueError("cleaned_df cannot be empty.")

    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError("dimensions must be a non-empty list of column names.")

    required = {"event_date", "item_revenue_usd"}
    missing = required - set(cleaned_df.columns)
    if missing:
        raise ValueError(f"cleaned_df is missing required columns: {sorted(missing)}")

    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1.")

    try:
        baseline_dt_start = pd.to_datetime(baseline_start)
        baseline_dt_end = pd.to_datetime(baseline_end)
        current_dt_start = pd.to_datetime(current_start)
        current_dt_end = pd.to_datetime(current_end)
    except Exception as exc:
        raise ValueError("baseline_start, baseline_end, current_start, and current_end must be valid dates.") from exc

    if baseline_dt_start > baseline_dt_end:
        raise ValueError("baseline_start must be on or before baseline_end.")
    if current_dt_start > current_dt_end:
        raise ValueError("current_start must be on or before current_end.")

    rows: list[dict[str, Any]] = []

    for dimension in dimensions:
        if dimension not in cleaned_df.columns:
            raise ValueError(f"Dimension '{dimension}' does not exist in cleaned_df.")

        for segment_value in sorted(cleaned_df[dimension].dropna().astype(str).str.strip().unique().tolist()):
            if segment_value == "nan":
                continue

            base_segment = cleaned_df.loc[cleaned_df[dimension].astype(str).str.strip().eq(segment_value)].copy()
            baseline_segment = base_segment.loc[
                (base_segment["event_date"] >= baseline_dt_start)
                & (base_segment["event_date"] <= baseline_dt_end)
            ].copy()
            current_segment = base_segment.loc[
                (base_segment["event_date"] >= current_dt_start)
                & (base_segment["event_date"] <= current_dt_end)
            ].copy()

            if baseline_segment.empty or current_segment.empty:
                baseline_daily = _build_daily_revenue_for_period(baseline_segment, baseline_start, baseline_end)
                current_daily = _build_daily_revenue_for_period(current_segment, current_start, current_end)
                baseline_values = baseline_daily["daily_revenue"].to_numpy(dtype=float)
                current_values = current_daily["daily_revenue"].to_numpy(dtype=float)
                baseline_avg = float(np.mean(baseline_values)) if len(baseline_values) else 0.0
                current_avg = float(np.mean(current_values)) if len(current_values) else 0.0
                pct_change = 0.0 if baseline_avg == 0 else ((current_avg - baseline_avg) / baseline_avg) * 100.0
                mean_diff = current_avg - baseline_avg
                ci_low, ci_high = _compute_mean_difference_ci(current_values, baseline_values, current_avg, baseline_avg, alpha=alpha)
                welch_t_statistic = np.nan
                p_value = np.nan
                cohen_d = np.nan
                baseline_total = float(baseline_values.sum())
                current_total = float(current_values.sum())
                nonzero_baseline_days = int((baseline_values > 0).sum())
                nonzero_current_days = int((current_values > 0).sum())
                revenue_shortfall = max(0.0, (baseline_avg * len(current_values)) - current_total)
            else:
                baseline_daily = _build_daily_revenue_for_period(baseline_segment, baseline_start, baseline_end)
                current_daily = _build_daily_revenue_for_period(current_segment, current_start, current_end)

                baseline_values = baseline_daily["daily_revenue"].to_numpy(dtype=float)
                current_values = current_daily["daily_revenue"].to_numpy(dtype=float)

                baseline_total = float(baseline_values.sum())
                current_total = float(current_values.sum())
                baseline_avg = float(np.mean(baseline_values)) if len(baseline_values) else 0.0
                current_avg = float(np.mean(current_values)) if len(current_values) else 0.0
                pct_change = 0.0 if baseline_avg == 0 else ((current_avg - baseline_avg) / baseline_avg) * 100.0
                mean_diff = current_avg - baseline_avg
                ci_low, ci_high = _compute_mean_difference_ci(current_values, baseline_values, current_avg, baseline_avg, alpha=alpha)

                if len(baseline_values) > 0 and len(current_values) > 0:
                    try:
                        welch_t_statistic, p_value = ttest_ind(
                            current_values,
                            baseline_values,
                            equal_var=False,
                            alternative="less",
                        )
                    except Exception:
                        welch_t_statistic = np.nan
                        p_value = np.nan
                    if np.isnan(welch_t_statistic) or np.isnan(p_value):
                        welch_t_statistic = np.nan
                        p_value = np.nan

                    if np.isfinite(welch_t_statistic) and np.isfinite(p_value):
                        pooled_var = (
                            ((len(baseline_values) - 1) * np.var(baseline_values, ddof=1))
                            + ((len(current_values) - 1) * np.var(current_values, ddof=1))
                        ) / (len(baseline_values) + len(current_values) - 2)
                        cohen_d = float((current_avg - baseline_avg) / np.sqrt(pooled_var)) if pooled_var > 0 else 0.0
                    else:
                        cohen_d = np.nan
                else:
                    welch_t_statistic = np.nan
                    p_value = np.nan
                    cohen_d = np.nan

                nonzero_baseline_days = int((baseline_values > 0).sum())
                nonzero_current_days = int((current_values > 0).sum())
                revenue_shortfall = max(0.0, (baseline_avg * len(current_values)) - current_total)

            row = {
                "dimension": dimension,
                "segment": segment_value,
                "baseline_start": baseline_dt_start,
                "baseline_end": baseline_dt_end,
                "current_start": current_dt_start,
                "current_end": current_dt_end,
                "baseline_total_revenue": baseline_total,
                "current_total_revenue": current_total,
                "baseline_avg_daily_revenue": baseline_avg,
                "current_avg_daily_revenue": current_avg,
                "percentage_change": pct_change,
                "mean_daily_revenue_difference": mean_diff,
                "confidence_interval_lower": ci_low,
                "confidence_interval_upper": ci_high,
                "welch_t_statistic": welch_t_statistic,
                "raw_p_value": p_value,
                "cohen_d": cohen_d,
                "baseline_nonzero_days": nonzero_baseline_days,
                "current_nonzero_days": nonzero_current_days,
                "revenue_shortfall": revenue_shortfall,
                "is_actionable": segment_value.strip() != "Unknown",
                "adjusted_p_value": np.nan,
                "is_statistically_significant": False,
            }
            rows.append(row)

    results = pd.DataFrame(rows)
    if results.empty:
        return results

    valid_mask = results["raw_p_value"].notna()
    if valid_mask.any():
        results["adjusted_p_value"] = np.nan
        results.loc[valid_mask, "adjusted_p_value"] = _build_bh_adjusted_pvalues(results.loc[valid_mask, "raw_p_value"], alpha=alpha).to_numpy()

    results["is_statistically_significant"] = (
        results["raw_p_value"].notna()
        & (results["adjusted_p_value"].notna())
        & (results["adjusted_p_value"] < alpha)
        & (results["percentage_change"] < 0)
    )
    results["is_statistically_significant"] = results["is_statistically_significant"].fillna(False)

    return results


def rank_hypotheses(results_df: pd.DataFrame) -> pd.DataFrame:
    """Rank contributor hypotheses by revenue shortfall and adjusted evidence strength. This is association ranking, not proof of causation."""
    if results_df.empty:
        return results_df.copy()

    ranked = results_df.loc[
        results_df["is_actionable"]
        & results_df["is_statistically_significant"]
        & (results_df["revenue_shortfall"] > 0)
    ].copy()

    if ranked.empty:
        return ranked

    ranked = ranked.sort_values(["revenue_shortfall", "adjusted_p_value"], ascending=[False, True]).reset_index(drop=True)
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    return ranked
