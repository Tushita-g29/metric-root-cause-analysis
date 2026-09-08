import pandas as pd
import pytest

from metric_rca.data import load_and_clean_sales_data


def _write_csv(tmp_path, rows):
    csv_path = tmp_path / "sales.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    return csv_path


def test_placeholder_mapping(tmp_path):
    rows = [
        {
            "event_date": "2016-10-08",
            "session_id": "abc-1",
            "region": "not available in demo dataset",
            "device_category": " ",
            "traffic_channel": "(direct) / (none)",
            "product_category": "(not set)",
            "item_revenue_usd": 15.5,
            "item_quantity": 1,
        }
    ]

    df = load_and_clean_sales_data(_write_csv(tmp_path, rows))

    assert df.loc[0, "region"] == "Unknown"
    assert df.loc[0, "product_category"] == "Unknown"
    assert df.loc[0, "device_category"] == "Unknown"
    assert df.loc[0, "traffic_channel"] == "(direct) / (none)"


def test_direct_traffic_is_preserved(tmp_path):
    rows = [
        {
            "event_date": "2016-10-09",
            "session_id": "abc-2",
            "region": "California",
            "device_category": "desktop",
            "traffic_channel": "(direct) / (none)",
            "product_category": "Apparel",
            "item_revenue_usd": 20.0,
            "item_quantity": 2,
        }
    ]

    df = load_and_clean_sales_data(_write_csv(tmp_path, rows))

    assert df.loc[0, "traffic_channel"] == "(direct) / (none)"


def test_invalid_and_negative_revenue_rows_are_dropped(tmp_path):
    rows = [
        {
            "event_date": "2016-10-10",
            "session_id": "good-1",
            "region": "New York",
            "device_category": "mobile",
            "traffic_channel": "google / organic",
            "product_category": "Office",
            "item_revenue_usd": 50.0,
            "item_quantity": 3,
        },
        {
            "event_date": "2016-10-11",
            "session_id": "bad-1",
            "region": "Texas",
            "device_category": "desktop",
            "traffic_channel": "google / cpc",
            "product_category": "Drinkware",
            "item_revenue_usd": 0,
            "item_quantity": 1,
        },
        {
            "event_date": "2016-10-12",
            "session_id": "bad-2",
            "region": "Illinois",
            "device_category": "desktop",
            "traffic_channel": "google / organic",
            "product_category": "Apparel",
            "item_revenue_usd": -10,
            "item_quantity": 2,
        },
        {
            "event_date": "bad-date",
            "session_id": "bad-3",
            "region": "Florida",
            "device_category": "tablet",
            "traffic_channel": "dfa / cpm",
            "product_category": "Lifestyle",
            "item_revenue_usd": 30,
            "item_quantity": 1,
        },
        {
            "event_date": "2016-10-13",
            "session_id": "bad-4",
            "region": "Washington",
            "device_category": "mobile",
            "traffic_channel": "google / organic",
            "product_category": "Electronics",
            "item_revenue_usd": "not-a-number",
            "item_quantity": 1,
        },
    ]

    df = load_and_clean_sales_data(_write_csv(tmp_path, rows))

    assert len(df) == 1
    assert df.iloc[0]["session_id"] == "good-1"


def test_missing_required_column_raises_value_error(tmp_path):
    csv_path = tmp_path / "missing_column.csv"
    pd.DataFrame(
        [
            {
                "event_date": "2016-10-08",
                "session_id": "abc",
                "region": "California",
                "device_category": "desktop",
                "traffic_channel": "(direct) / (none)",
                "product_category": "Apparel",
                "item_revenue_usd": 10.99,
            }
        ]
    ).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="missing required columns"):
        load_and_clean_sales_data(csv_path)
