from __future__ import annotations

from typing import Any

import pandas as pd

REQUIRED_COLUMNS = [
    "event_date",
    "session_id",
    "region",
    "device_category",
    "traffic_channel",
    "product_category",
    "item_revenue_usd",
    "item_quantity",
]


def _clean_text_column(series: pd.Series) -> pd.Series:
    """Trim whitespace and convert empty strings to missing values."""
    return series.astype("string").str.strip().replace("", pd.NA)


def load_and_clean_sales_data(csv_path: str | Any) -> pd.DataFrame:
    """Read and clean the raw sales CSV file used by the RCA project."""
    df = pd.read_csv(csv_path)

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(
            "CSV file is missing required columns: " + ", ".join(missing_columns)
        )

    df = df.copy()
    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df["item_revenue_usd"] = pd.to_numeric(df["item_revenue_usd"], errors="coerce")
    df["item_quantity"] = pd.to_numeric(df["item_quantity"], errors="coerce")

    df["region"] = _clean_text_column(df["region"]).replace(
        {"not available in demo dataset": "Unknown", "(not set)": "Unknown"}
    )
    df["region"] = df["region"].fillna("Unknown")

    df["product_category"] = _clean_text_column(df["product_category"]).replace(
        {"(not set)": "Unknown"}
    )
    df["product_category"] = df["product_category"].fillna("Unknown")

    for col in ["device_category", "traffic_channel"]:
        df[col] = _clean_text_column(df[col]).fillna("Unknown")

    df["region"] = df["region"].replace("", "Unknown")
    df["product_category"] = df["product_category"].replace("", "Unknown")
    df["device_category"] = df["device_category"].replace("", "Unknown")
    df["traffic_channel"] = df["traffic_channel"].replace("", "Unknown")

    valid_rows = (
        df["event_date"].notna()
        & df["item_revenue_usd"].notna()
        & df["item_quantity"].notna()
        & (df["item_revenue_usd"] > 0)
        & (df["item_quantity"] > 0)
    )
    df = df.loc[valid_rows].copy()
    df = df.sort_values("event_date").reset_index(drop=True)

    return df


def build_data_quality_report(df: pd.DataFrame) -> dict[str, Any]:
    """Return a lightweight summary of the cleaned sales data."""
    return {
        "row_count": int(len(df)),
        "date_range": {
            "start": df["event_date"].min().strftime("%Y-%m-%d"),
            "end": df["event_date"].max().strftime("%Y-%m-%d"),
        },
        "total_revenue": float(df["item_revenue_usd"].sum()),
        "unique_sessions": int(df["session_id"].nunique()),
        "category_counts": {
            "region": df["region"].value_counts().to_dict(),
            "device_category": df["device_category"].value_counts().to_dict(),
            "traffic_channel": df["traffic_channel"].value_counts().to_dict(),
            "product_category": df["product_category"].value_counts().to_dict(),
        },
    }
