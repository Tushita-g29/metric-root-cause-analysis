from __future__ import annotations

from typing import Any

import pandas as pd


def simulate_segment_revenue_drop(
    cleaned_df: pd.DataFrame,
    segment_column: str,
    segment_value: str,
    revenue_multiplier: float,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return a copied DataFrame with simulated revenue reduction for a segment/date window."""
    if segment_column not in cleaned_df.columns:
        raise ValueError(f"Segment column '{segment_column}' does not exist in the DataFrame.")
    if not 0 < revenue_multiplier < 1:
        raise ValueError("revenue_multiplier must be between 0 and 1.")

    df = cleaned_df.copy()
    if start_date is None:
        start_date = df["event_date"].min().strftime("%Y-%m-%d")
    if end_date is None:
        end_date = df["event_date"].max().strftime("%Y-%m-%d")

    try:
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
    except Exception as exc:
        raise ValueError("start_date and end_date must be valid date values.") from exc

    date_mask = (df["event_date"] >= start_dt) & (df["event_date"] <= end_dt)
    segment_mask = df[segment_column].astype(str).str.strip().eq(str(segment_value).strip())
    affected_mask = date_mask & segment_mask

    if not affected_mask.any():
        raise ValueError(
            f"No rows match segment_column='{segment_column}', segment_value='{segment_value}', and date range {start_date} to {end_date}."
        )

    original_affected_revenue = float(df.loc[affected_mask, "item_revenue_usd"].sum())
    df.loc[affected_mask, "item_revenue_usd"] = (
        df.loc[affected_mask, "item_revenue_usd"] * revenue_multiplier
    )
    simulated_affected_revenue = float(df.loc[affected_mask, "item_revenue_usd"].sum())
    revenue_removed = original_affected_revenue - simulated_affected_revenue

    metadata = {
        "is_simulated": True,
        "scenario_name": "custom_segment_revenue_drop",
        "segment_column": segment_column,
        "segment_value": segment_value,
        "start_date": start_date,
        "end_date": end_date,
        "revenue_multiplier": revenue_multiplier,
        "affected_row_count": int(affected_mask.sum()),
        "original_affected_revenue": original_affected_revenue,
        "simulated_affected_revenue": simulated_affected_revenue,
        "revenue_removed": revenue_removed,
    }

    return df, metadata


def create_default_demo_scenario(cleaned_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Create a default demo scenario that simulates a severe direct-traffic outage near the end of the dataset."""
    df = cleaned_df.copy()
    start_date = df["event_date"].max() - pd.Timedelta(days=27)
    end_date = df["event_date"].max()
    return simulate_segment_revenue_drop(
        df,
        segment_column="traffic_channel",
        segment_value="(direct) / (none)",
        revenue_multiplier=0.05,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
    )
