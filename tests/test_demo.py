import pandas as pd
import pytest

from metric_rca.demo import create_default_demo_scenario, simulate_segment_revenue_drop


def test_original_dataframe_is_unchanged():
    df = pd.DataFrame(
        {
            "event_date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "traffic_channel": ["(direct) / (none)", "google / organic", "(direct) / (none)"],
            "item_revenue_usd": [100.0, 50.0, 30.0],
        }
    )

    original = df.copy(deep=True)
    _ = simulate_segment_revenue_drop(
        df,
        segment_column="traffic_channel",
        segment_value="(direct) / (none)",
        revenue_multiplier=0.5,
        start_date="2024-01-01",
        end_date="2024-01-03",
    )

    pd.testing.assert_frame_equal(df, original)


def test_only_matching_rows_in_selected_date_range_are_changed():
    df = pd.DataFrame(
        {
            "event_date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]),
            "traffic_channel": [
                "(direct) / (none)",
                "(direct) / (none)",
                "google / organic",
                "(direct) / (none)",
            ],
            "item_revenue_usd": [100.0, 80.0, 60.0, 40.0],
        }
    )

    simulated, metadata = simulate_segment_revenue_drop(
        df,
        segment_column="traffic_channel",
        segment_value="(direct) / (none)",
        revenue_multiplier=0.5,
        start_date="2024-01-02",
        end_date="2024-01-03",
    )

    assert simulated.loc[0, "item_revenue_usd"] == 100.0
    assert simulated.loc[1, "item_revenue_usd"] == 40.0
    assert simulated.loc[2, "item_revenue_usd"] == 60.0
    assert simulated.loc[3, "item_revenue_usd"] == 40.0
    assert metadata["affected_row_count"] == 1


def test_invalid_multipliers_and_no_match_raise_value_error():
    df = pd.DataFrame(
        {
            "event_date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "traffic_channel": ["(direct) / (none)", "google / organic"],
            "item_revenue_usd": [100.0, 50.0],
        }
    )

    with pytest.raises(ValueError, match="between 0 and 1"):
        simulate_segment_revenue_drop(
            df,
            segment_column="traffic_channel",
            segment_value="(direct) / (none)",
            revenue_multiplier=1.5,
        )

    with pytest.raises(ValueError, match="No rows match"):
        simulate_segment_revenue_drop(
            df,
            segment_column="traffic_channel",
            segment_value="newsletter",
            revenue_multiplier=0.5,
            start_date="2024-01-01",
            end_date="2024-01-02",
        )


def test_default_scenario_returns_simulated_direct_traffic_only():
    df = pd.DataFrame(
        {
            "event_date": pd.to_datetime([
                "2024-01-01",
                "2024-01-02",
                "2024-01-03",
                "2024-01-04",
                "2024-01-05",
            ]),
            "traffic_channel": [
                "(direct) / (none)",
                "(direct) / (none)",
                "google / organic",
                "(direct) / (none)",
                "google / organic",
            ],
            "item_revenue_usd": [100.0, 80.0, 60.0, 40.0, 50.0],
        }
    )

    simulated, metadata = create_default_demo_scenario(df)

    assert metadata["is_simulated"] is True
    assert metadata["segment_value"] == "(direct) / (none)"
    assert simulated.loc[simulated["traffic_channel"] == "google / organic", "item_revenue_usd"].tolist() == [60.0, 50.0]
