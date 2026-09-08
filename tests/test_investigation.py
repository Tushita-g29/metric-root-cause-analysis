import json
from pathlib import Path

import pandas as pd
import pytest

from metric_rca.investigation import run_investigation


def _write_df(csv_path: Path, df: pd.DataFrame) -> None:
    df.to_csv(csv_path, index=False)


def test_real_mode_with_no_drop_returns_no_anomaly(tmp_path):
    csv_path = tmp_path / "stable_sales.csv"
    dates = pd.date_range("2024-01-01", periods=200, freq="D")
    df = pd.DataFrame(
        {
            "event_date": dates,
            "session_id": [f"s{i}" for i in range(len(dates))],
            "region": ["California"] * len(dates),
            "device_category": ["desktop"] * len(dates),
            "traffic_channel": ["google / organic"] * len(dates),
            "product_category": ["Apparel"] * len(dates),
            "item_revenue_usd": [100.0] * len(dates),
            "item_quantity": [1] * len(dates),
        }
    )
    _write_df(csv_path, df)

    result = run_investigation(str(csv_path), mode="real", current_days=28, baseline_days=56)

    assert result["status"] == "no_anomaly"
    assert result["mode"] == "real"
    assert result["is_simulated"] is False
    assert result["ranked_findings"] == []


def test_demo_mode_returns_anomaly_detected_and_ranked_findings(tmp_path):
    csv_path = tmp_path / "sales_demo.csv"
    dates = pd.date_range("2017-01-01", periods=200, freq="D")
    rows = []
    for idx, day in enumerate(dates):
        traffic = "(direct) / (none)" if idx % 2 == 0 else "google / organic"
        revenue = 100.0 + (idx % 7) * 10.0
        rows.append(
            {
                "event_date": day,
                "session_id": f"s{idx}",
                "region": "California" if idx % 3 != 0 else "New York",
                "device_category": "desktop" if idx % 2 == 0 else "mobile",
                "traffic_channel": traffic,
                "product_category": "Apparel" if idx % 3 == 0 else "Office",
                "item_revenue_usd": revenue,
                "item_quantity": 1,
            }
        )
    df = pd.DataFrame(rows)
    _write_df(csv_path, df)

    result = run_investigation(str(csv_path), mode="demo", current_days=28, baseline_days=56)

    assert result["status"] == "anomaly_detected"
    assert result["mode"] == "demo"
    assert result["is_simulated"] is True
    assert len(result["ranked_findings"]) > 0
    assert isinstance(result["confound_warnings"], list)


def test_invalid_mode_raises_clear_value_error(tmp_path):
    csv_path = tmp_path / "sales.csv"
    df = pd.DataFrame(
        {
            "event_date": pd.date_range("2024-01-01", periods=10, freq="D"),
            "session_id": [f"s{i}" for i in range(10)],
            "region": ["California"] * 10,
            "device_category": ["desktop"] * 10,
            "traffic_channel": ["google / organic"] * 10,
            "product_category": ["Apparel"] * 10,
            "item_revenue_usd": [100.0] * 10,
            "item_quantity": [1] * 10,
        }
    )
    _write_df(csv_path, df)

    with pytest.raises(ValueError, match="mode must be either 'real' or 'demo'"):
        run_investigation(str(csv_path), mode="invalid")


def test_result_is_json_serializable(tmp_path):
    csv_path = tmp_path / "sales_json.csv"
    dates = pd.date_range("2017-01-01", periods=200, freq="D")
    df = pd.DataFrame(
        {
            "event_date": dates,
            "session_id": [f"s{i}" for i in range(len(dates))],
            "region": ["California"] * len(dates),
            "device_category": ["desktop"] * len(dates),
            "traffic_channel": ["(direct) / (none)"] * len(dates),
            "product_category": ["Apparel"] * len(dates),
            "item_revenue_usd": [100.0] * len(dates),
            "item_quantity": [1] * len(dates),
        }
    )
    _write_df(csv_path, df)

    result = run_investigation(str(csv_path), mode="demo", current_days=28, baseline_days=56)
    json.dumps(result)
