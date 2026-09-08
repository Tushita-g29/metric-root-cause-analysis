import pandas as pd
import pytest

from metric_rca.anomaly import aggregate_daily_revenue, detect_recent_revenue_drop


def test_days_without_purchases_are_zeroed():
    df = pd.DataFrame(
        {
            "event_date": ["2024-01-01", "2024-01-03"],
            "item_revenue_usd": [100.0, 50.0],
        }
    )

    result = aggregate_daily_revenue(df)

    assert list(result["event_date"]) == [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-01-02"),
        pd.Timestamp("2024-01-03"),
    ]
    assert list(result["daily_revenue"]) == [100.0, 0.0, 50.0]


def test_clear_recent_decline_is_statistically_detected():
    dates = pd.date_range("2024-01-01", periods=84, freq="D")
    baseline_revenue = [100.0, 98.0, 102.0, 96.0, 104.0] * 11 + [100.0]
    current_revenue = [10.0] * 28
    revenue = baseline_revenue + current_revenue

    df = pd.DataFrame({"event_date": dates, "daily_revenue": revenue})
    result = detect_recent_revenue_drop(df, current_days=28, baseline_days=56)

    assert result["is_drop_anomaly"] is True
    assert result["percentage_change"] < 0
    assert result["p_value"] < 0.05


def test_stable_or_higher_recent_period_is_not_drop():
    dates = pd.date_range("2024-01-01", periods=84, freq="D")
    baseline_revenue = [100.0] * 56
    current_revenue = [150.0] * 28
    revenue = baseline_revenue + current_revenue

    df = pd.DataFrame({"event_date": dates, "daily_revenue": revenue})
    result = detect_recent_revenue_drop(df, current_days=28, baseline_days=56)

    assert result["is_drop_anomaly"] is False


def test_insufficient_history_raises_value_error():
    dates = pd.date_range("2024-01-01", periods=70, freq="D")
    df = pd.DataFrame({"event_date": dates, "daily_revenue": [100.0] * 70})

    with pytest.raises(ValueError, match="Not enough daily revenue history"):
        detect_recent_revenue_drop(df, current_days=28, baseline_days=56)


def test_zero_variation_input_does_not_crash():
    dates = pd.date_range("2024-01-01", periods=84, freq="D")
    df = pd.DataFrame({"event_date": dates, "daily_revenue": [50.0] * 84})

    result = detect_recent_revenue_drop(df, current_days=28, baseline_days=56)

    assert isinstance(result["p_value"], float)
    assert result["is_drop_anomaly"] is False
