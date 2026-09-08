import numpy as np
import pandas as pd
import pytest

from metric_rca.confounds import (
    flag_confound_warnings,
    flag_segment_overlap_warnings,
    measure_dimension_associations,
    measure_ranked_segment_overlap,
)


def test_strongly_associated_pair_has_high_significant_cramers_v():
    df = pd.DataFrame(
        {
            "region": ["California"] * 100 + ["New York"] * 100,
            "device_category": ["desktop"] * 100 + ["mobile"] * 100,
            "product_category": ["Apparel"] * 200,
            "traffic_channel": ["google / organic"] * 200,
        }
    )

    associations = measure_dimension_associations(df, dimensions=["region", "device_category"])

    assert len(associations) == 1
    assert associations.iloc[0]["cramers_v"] > 0.80
    assert bool(associations.iloc[0]["is_statistically_significant"]) is True
    assert associations.iloc[0]["p_value"] < 0.05


def test_approximately_independent_pair_has_low_cramers_v():
    df = pd.DataFrame(
        {
            "region": ["California"] * 50 + ["New York"] * 50 + ["California"] * 50 + ["New York"] * 50,
            "device_category": ["desktop"] * 50 + ["desktop"] * 50 + ["mobile"] * 50 + ["mobile"] * 50,
            "product_category": ["Apparel"] * 200,
            "traffic_channel": ["google / organic"] * 200,
        }
    )

    associations = measure_dimension_associations(df, dimensions=["region", "device_category"])

    assert len(associations) == 1
    assert associations.iloc[0]["cramers_v"] < 0.20
    assert bool(associations.iloc[0]["is_statistically_significant"]) is False


def test_warnings_appear_only_for_eligible_high_association_pairs():
    df = pd.DataFrame(
        {
            "region": ["California"] * 40 + ["New York"] * 40 + ["California"] * 40 + ["New York"] * 40,
            "device_category": ["desktop"] * 80 + ["mobile"] * 80,
            "product_category": ["Apparel"] * 80 + ["Office"] * 80,
            "traffic_channel": ["google / organic"] * 160,
        }
    )

    associations = measure_dimension_associations(df, dimensions=["region", "device_category", "product_category"])
    ranked = pd.DataFrame(
        {
            "dimension": ["region", "device_category", "product_category"],
            "segment": ["California", "desktop", "Apparel"],
            "revenue_shortfall": [100.0, 80.0, 50.0],
            "is_actionable": [True, True, True],
            "is_statistically_significant": [True, True, True],
            "adjusted_p_value": [0.01, 0.02, 0.03],
        }
    )

    warnings = flag_confound_warnings(ranked, associations, cramers_v_threshold=0.30)

    assert not warnings.empty
    assert set(warnings["dimension_a"]).union(set(warnings["dimension_b"])) <= {"region", "device_category", "product_category"}
    assert all("Overlapping contributor signal" in text for text in warnings["warning_text"])


def test_invalid_dimensions_or_empty_input_raise_value_error():
    empty_df = pd.DataFrame()
    with pytest.raises(ValueError, match="empty"):
        measure_dimension_associations(empty_df, dimensions=["region"])

    df = pd.DataFrame({"region": ["California"], "device_category": ["desktop"]})
    with pytest.raises(ValueError, match="Invalid dimension"):
        measure_dimension_associations(df, dimensions=["region", "not_a_real_column"])

    with pytest.raises(ValueError, match="non-empty list"):
        measure_dimension_associations(df, dimensions=[])


def test_strongly_overlapping_pair_produces_high_conditional_overlap_and_warning():
    df = pd.DataFrame(
        {
            "event_date": pd.date_range("2024-01-01", periods=200, freq="D"),
            "region": ["California"] * 150 + ["New York"] * 50,
            "device_category": ["desktop"] * 150 + ["mobile"] * 50,
            "product_category": ["Apparel"] * 200,
            "traffic_channel": ["(direct) / (none)"] * 200,
        }
    )

    ranked = pd.DataFrame(
        {
            "rank": [1, 2],
            "dimension": ["region", "device_category"],
            "segment": ["California", "desktop"],
        }
    )

    overlaps = measure_ranked_segment_overlap(
        df,
        ranked,
        current_start="2024-01-01",
        current_end="2024-07-17",
        top_n=5,
    )

    assert len(overlaps) == 1
    assert overlaps.iloc[0]["pct_b_given_a"] >= 0.70
    assert overlaps.iloc[0]["pct_a_given_b"] >= 0.70
    warning_df = flag_segment_overlap_warnings(overlaps)
    assert not warning_df.empty
    assert "Overlapping ranked contributor signals" in warning_df.iloc[0]["warning_text"]


def test_weak_unrelated_pair_produces_no_warning():
    df = pd.DataFrame(
        {
            "event_date": pd.date_range("2024-01-01", periods=200, freq="D"),
            "region": ["California"] * 100 + ["New York"] * 100,
            "device_category": ["desktop"] * 100 + ["mobile"] * 100,
            "product_category": ["Apparel"] * 200,
            "traffic_channel": ["(direct) / (none)"] * 200,
        }
    )

    ranked = pd.DataFrame(
        {
            "rank": [1, 2],
            "dimension": ["region", "device_category"],
            "segment": ["California", "desktop"],
        }
    )

    overlaps = measure_ranked_segment_overlap(
        df,
        ranked,
        current_start="2024-01-01",
        current_end="2024-01-31",
        top_n=5,
    )
    assert len(overlaps) == 1
    warning_df = flag_segment_overlap_warnings(overlaps, conditional_share_threshold=0.70)
    assert warning_df.empty


def test_invalid_date_ranges_or_missing_ranked_columns_raise_value_error():
    df = pd.DataFrame(
        {
            "event_date": pd.date_range("2024-01-01", periods=30, freq="D"),
            "region": ["California"] * 30,
            "device_category": ["desktop"] * 30,
        }
    )
    ranked = pd.DataFrame({"dimension": ["region"], "segment": ["California"]})

    with pytest.raises(ValueError, match="on or before"):
        measure_ranked_segment_overlap(df, ranked, current_start="2024-02-02", current_end="2024-01-01")

    with pytest.raises(ValueError, match="must include 'dimension' and 'segment'"):
        measure_ranked_segment_overlap(df, pd.DataFrame({"rank": [1]}), "2024-01-01", "2024-01-10")
