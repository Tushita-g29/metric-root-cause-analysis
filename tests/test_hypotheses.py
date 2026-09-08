import pandas as pd
import pytest

from metric_rca.hypotheses import rank_hypotheses, test_segment_revenue_declines as run_segment_revenue_declines


def _make_daily_df():
    dates = pd.date_range("2024-01-01", periods=140, freq="D")
    rows = []
    for idx, day in enumerate(dates):
        if idx < 70:
            region = "California"
            device = "desktop"
            product = "Apparel"
            traffic = "(direct) / (none)"
            revenue = 100.0
        elif idx < 98:
            region = "California"
            device = "desktop"
            product = "Apparel"
            traffic = "google / organic"
            revenue = 80.0
        elif idx < 112:
            region = "New York"
            device = "mobile"
            product = "Office"
            traffic = "(direct) / (none)"
            revenue = 120.0
        else:
            region = "California"
            device = "desktop"
            product = "Apparel"
            traffic = "(direct) / (none)"
            revenue = 20.0
        rows.append(
            {
                "event_date": day,
                "session_id": f"s{idx}",
                "region": region,
                "device_category": device,
                "traffic_channel": traffic,
                "product_category": product,
                "item_revenue_usd": revenue,
                "item_quantity": 1,
            }
        )
    return pd.DataFrame(rows)


def test_strong_direct_traffic_drop_is_significant_and_ranks_first():
    df = _make_daily_df()

    results = run_segment_revenue_declines(
        df,
        baseline_start="2024-01-01",
        baseline_end="2024-02-09",
        current_start="2024-02-10",
        current_end="2024-03-30",
        dimensions=["traffic_channel"],
    )

    ranked = rank_hypotheses(results)
    direct = ranked[ranked["segment"] == "(direct) / (none)"]

    assert not direct.empty
    assert direct.iloc[0]["rank"] == 1
    assert bool(direct.iloc[0]["is_statistically_significant"]) is True
    assert direct.iloc[0]["revenue_shortfall"] > 0
    assert "confidence_interval_lower" in results.columns
    assert "adjusted_p_value" in results.columns


def test_stable_traffic_is_not_flagged_as_significant():
    dates = pd.date_range("2024-01-01", periods=84, freq="D")
    df = pd.DataFrame(
        {
            "event_date": dates,
            "session_id": [f"s{i}" for i in range(len(dates))],
            "region": "California",
            "device_category": "desktop",
            "traffic_channel": "google / organic",
            "product_category": "Apparel",
            "item_revenue_usd": [100.0] * len(dates),
            "item_quantity": [1] * len(dates),
        }
    )

    results = run_segment_revenue_declines(
        df,
        baseline_start="2024-01-01",
        baseline_end="2024-02-23",
        current_start="2024-02-24",
        current_end="2024-03-25",
        dimensions=["traffic_channel"],
    )

    assert results["is_statistically_significant"].sum() == 0


def test_unknown_is_reported_but_not_actionable_or_rankable():
    df = pd.DataFrame(
        {
            "event_date": pd.date_range("2024-01-01", periods=84, freq="D"),
            "session_id": [f"s{i}" for i in range(84)],
            "region": ["Unknown"] * 84,
            "device_category": ["desktop"] * 84,
            "traffic_channel": ["(direct) / (none)"] * 84,
            "product_category": ["Unknown"] * 84,
            "item_revenue_usd": [100.0] * 84,
            "item_quantity": [1] * 84,
        }
    )

    results = run_segment_revenue_declines(
        df,
        baseline_start="2024-01-01",
        baseline_end="2024-02-23",
        current_start="2024-02-24",
        current_end="2024-03-25",
        dimensions=["region", "product_category"],
    )

    unknown_rows = results[results["segment"] == "Unknown"]
    assert not unknown_rows.empty
    assert (unknown_rows["is_actionable"] == False).all()
    assert rank_hypotheses(results).empty


def test_expected_columns_exist():
    dates = pd.date_range("2024-01-01", periods=84, freq="D")
    df = pd.DataFrame(
        {
            "event_date": dates,
            "session_id": [f"s{i}" for i in range(len(dates))],
            "region": ["California"] * len(dates),
            "device_category": ["desktop"] * len(dates),
            "traffic_channel": ["(direct) / (none)"] * len(dates),
            "product_category": ["Apparel"] * len(dates),
            "item_revenue_usd": [10.0] * len(dates),
            "item_quantity": [1] * len(dates),
        }
    )

    results = run_segment_revenue_declines(
        df,
        baseline_start="2024-01-01",
        baseline_end="2024-02-23",
        current_start="2024-02-24",
        current_end="2024-03-25",
        dimensions=["traffic_channel"],
    )

    for col in [
        "confidence_interval_lower",
        "confidence_interval_upper",
        "adjusted_p_value",
        "is_statistically_significant",
        "revenue_shortfall",
    ]:
        assert col in results.columns


def test_invalid_or_insufficient_periods_raise_value_error():
    df = pd.DataFrame(
        {
            "event_date": pd.date_range("2024-01-01", periods=30, freq="D"),
            "session_id": [f"s{i}" for i in range(30)],
            "region": ["California"] * 30,
            "device_category": ["desktop"] * 30,
            "traffic_channel": ["(direct) / (none)"] * 30,
            "product_category": ["Apparel"] * 30,
            "item_revenue_usd": [10.0] * 30,
            "item_quantity": [1] * 30,
        }
    )

    with pytest.raises(ValueError, match="must be on or before|must be valid"):
        run_segment_revenue_declines(
            df,
            baseline_start="2024-02-20",
            baseline_end="2024-02-10",
            current_start="2024-02-11",
            current_end="2024-03-01",
            dimensions=["traffic_channel"],
        )

    with pytest.raises(ValueError, match="non-empty list|Dimension"):
        run_segment_revenue_declines(
            df,
            baseline_start="2024-01-01",
            baseline_end="2024-01-15",
            current_start="2024-01-16",
            current_end="2024-01-30",
            dimensions=[],
        )
