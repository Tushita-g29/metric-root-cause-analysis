from __future__ import annotations

import numpy as np
import pandas as pd


def aggregate_daily_revenue(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate revenue by day and include zero-revenue days with no sales."""
    if cleaned_df.empty:
        return pd.DataFrame(columns=["event_date", "daily_revenue"])

    if "event_date" not in cleaned_df.columns or "item_revenue_usd" not in cleaned_df.columns:
        raise ValueError("cleaned_df must include event_date and item_revenue_usd columns")

    daily = (
        cleaned_df.assign(event_date=pd.to_datetime(cleaned_df["event_date"]))
        .groupby("event_date", as_index=False)["item_revenue_usd"]
        .sum()
        .rename(columns={"item_revenue_usd": "daily_revenue"})
    )

    start_date = daily["event_date"].min()
    end_date = daily["event_date"].max()
    full_date_range = pd.date_range(start=start_date, end=end_date, freq="D")

    daily = (
        pd.DataFrame({"event_date": full_date_range})
        .merge(daily, on="event_date", how="left")
        .fillna({"daily_revenue": 0.0})
    )

    return daily[["event_date", "daily_revenue"]].sort_values("event_date").reset_index(drop=True)


def detect_recent_revenue_drop(
    daily_revenue_df: pd.DataFrame,
    current_days: int = 28,
    baseline_days: int = 56,
    z_threshold: float = -2.0,
) -> dict:
    """Detect a statistically supported recent negative revenue shift."""
    if len(daily_revenue_df) < current_days + baseline_days:
        raise ValueError(
            "Not enough daily revenue history. Need at least current_days + baseline_days rows."
        )

    if "event_date" not in daily_revenue_df.columns or "daily_revenue" not in daily_revenue_df.columns:
        raise ValueError("daily_revenue_df must include event_date and daily_revenue columns")

    daily_revenue_df = daily_revenue_df.sort_values("event_date").reset_index(drop=True).copy()
    current = daily_revenue_df.iloc[-current_days:]
    baseline = daily_revenue_df.iloc[-(current_days + baseline_days):-current_days]

    baseline_total = float(baseline["daily_revenue"].sum())
    current_total = float(current["daily_revenue"].sum())

    baseline_avg = float(baseline["daily_revenue"].mean())
    current_avg = float(current["daily_revenue"].mean())

    pct_change = 0.0 if baseline_avg == 0 else ((current_avg - baseline_avg) / baseline_avg) * 100.0

    baseline_std = float(baseline["daily_revenue"].std(ddof=0))
    if baseline_std == 0:
        z_score = 0.0
    else:
        z_score = float((current_avg - baseline_avg) / baseline_std)

    is_drop_anomaly = (pct_change < 0) and (z_score <= z_threshold)

    return {
        "current_period_start": current["event_date"].min(),
        "current_period_end": current["event_date"].max(),
        "baseline_period_start": baseline["event_date"].min(),
        "baseline_period_end": baseline["event_date"].max(),
        "baseline_total_revenue": baseline_total,
        "current_total_revenue": current_total,
        "baseline_avg_daily_revenue": baseline_avg,
        "current_avg_daily_revenue": current_avg,
        "percentage_change": pct_change,
        "baseline_std_dev": baseline_std,
        "z_score": z_score,
        "is_drop_anomaly": is_drop_anomaly,
    }
