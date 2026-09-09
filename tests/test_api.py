from __future__ import annotations

import pandas as pd
from fastapi.testclient import TestClient

import metric_rca.api as api_module
from metric_rca.api import app

client = TestClient(app)


def _write_synthetic_sales_csv(path) -> None:
    dates = pd.date_range("2024-01-01", periods=120, freq="D")
    rows: list[dict[str, object]] = []

    for day_index, event_date in enumerate(dates):
        base_revenue = 120 + (day_index % 9) * 4
        for channel in ["(direct) / (none)", "organic_search", "paid_search"]:
            channel_multiplier = 1.0 if channel == "(direct) / (none)" else 0.8
            for region in ["North", "South", "West"]:
                rows.append(
                    {
                        "event_date": event_date.strftime("%Y-%m-%d"),
                        "session_id": f"s-{day_index}-{channel}-{region}",
                        "region": region,
                        "device_category": "desktop" if day_index % 2 == 0 else "mobile",
                        "traffic_channel": channel,
                        "product_category": "Apparel" if day_index % 2 == 0 else "Office",
                        "item_revenue_usd": round(base_revenue * channel_multiplier, 2),
                        "item_quantity": 2,
                    }
                )

    pd.DataFrame(rows).to_csv(path, index=False)


def test_dashboard_root_returns_title() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Metric Root-Cause Analysis" in response.text


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_investigate_real_mode_returns_no_anomaly(tmp_path, monkeypatch) -> None:
    csv_path = tmp_path / "sales.csv"
    _write_synthetic_sales_csv(csv_path)
    monkeypatch.setattr(api_module, "DATASET_PATH", csv_path)

    response = client.get("/investigate", params={"mode": "real"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "no_anomaly"
    assert payload["is_simulated"] is False


def test_investigate_demo_mode_returns_anomaly(tmp_path, monkeypatch) -> None:
    csv_path = tmp_path / "sales.csv"
    _write_synthetic_sales_csv(csv_path)
    monkeypatch.setattr(api_module, "DATASET_PATH", csv_path)

    response = client.get("/investigate", params={"mode": "demo"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_simulated"] is True
    assert payload["status"] == "anomaly_detected"
    assert payload["anomaly"]["is_drop_anomaly"] is True


def test_invalid_mode_returns_client_validation_error() -> None:
    response = client.get("/investigate", params={"mode": "invalid"})
    assert response.status_code == 422
