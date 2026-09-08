import numpy as np
import pandas as pd
import pytest

from metric_rca.confounds import flag_confound_warnings, measure_dimension_associations


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
