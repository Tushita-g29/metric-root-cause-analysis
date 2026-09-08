from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

DEFAULT_HYPOTHESIS_DIMENSIONS = [
    "region",
    "device_category",
    "product_category",
    "traffic_channel",
]


def _validate_dimensions(df: pd.DataFrame, dimensions: list[str]) -> list[str]:
    """Validate the supplied dimension names against the DataFrame."""
    if df is None or df.empty:
        raise ValueError("df cannot be empty.")

    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError("dimensions must be a non-empty list of column names.")

    unique_dimensions = list(dict.fromkeys(dimensions))
    if len(unique_dimensions) != len(dimensions):
        raise ValueError("dimensions must not contain duplicates.")

    missing = [column for column in unique_dimensions if column not in df.columns]
    if missing:
        raise ValueError(f"Invalid dimension(s): {missing}")

    return unique_dimensions


def _cramers_v_from_contingency(contingency_table: pd.DataFrame) -> float:
    """Compute Cramér's V for a contingency table."""
    if contingency_table.empty:
        return 0.0

    values = contingency_table.to_numpy(dtype=float)
    if values.size == 0:
        return 0.0

    if values.shape[0] == 1 or values.shape[1] == 1:
        return 0.0

    chi_square_statistic, _, _, _ = chi2_contingency(values, correction=False)
    total_count = float(values.sum())
    if total_count == 0:
        return 0.0

    min_dimension = min(values.shape[0] - 1, values.shape[1] - 1)
    if min_dimension <= 0:
        return 0.0

    return float(np.sqrt(chi_square_statistic / (total_count * min_dimension)))


def measure_dimension_associations(
    df: pd.DataFrame,
    dimensions: list[str] = DEFAULT_HYPOTHESIS_DIMENSIONS,
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Measure pairwise categorical dependence for the supplied dimensions."""
    validated = _validate_dimensions(df, dimensions)

    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1.")

    prepared = df.loc[:, validated].copy()
    for column in validated:
        prepared[column] = prepared[column].astype("string").fillna("Unknown")

    rows: list[dict[str, object]] = []
    for left_index in range(len(validated)):
        for right_index in range(left_index + 1, len(validated)):
            dimension_a = validated[left_index]
            dimension_b = validated[right_index]

            contingency = pd.crosstab(prepared[dimension_a], prepared[dimension_b])
            if contingency.empty or contingency.shape[0] == 0 or contingency.shape[1] == 0:
                rows.append(
                    {
                        "dimension_a": dimension_a,
                        "dimension_b": dimension_b,
                        "sample_size": int(len(df)),
                        "chi_square_statistic": np.nan,
                        "p_value": np.nan,
                        "cramers_v": np.nan,
                        "is_statistically_significant": False,
                    }
                )
                continue

            try:
                chi_square_statistic, p_value, _, _ = chi2_contingency(contingency.to_numpy(dtype=float), correction=False)
                cramers_v = _cramers_v_from_contingency(contingency)
            except ValueError:
                rows.append(
                    {
                        "dimension_a": dimension_a,
                        "dimension_b": dimension_b,
                        "sample_size": int(len(df)),
                        "chi_square_statistic": np.nan,
                        "p_value": np.nan,
                        "cramers_v": np.nan,
                        "is_statistically_significant": False,
                    }
                )
                continue

            rows.append(
                {
                    "dimension_a": dimension_a,
                    "dimension_b": dimension_b,
                    "sample_size": int(len(df)),
                    "chi_square_statistic": float(chi_square_statistic),
                    "p_value": float(p_value),
                    "cramers_v": float(cramers_v),
                    "is_statistically_significant": bool(np.isfinite(p_value) and p_value < alpha),
                }
            )

    return pd.DataFrame(
        rows,
        columns=[
            "dimension_a",
            "dimension_b",
            "sample_size",
            "chi_square_statistic",
            "p_value",
            "cramers_v",
            "is_statistically_significant",
        ],
    )


def flag_confound_warnings(
    ranked_hypotheses_df: pd.DataFrame,
    associations_df: pd.DataFrame,
    cramers_v_threshold: float = 0.30,
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Flag overlapping contributor signal warnings when paired dimensions are associated."""
    if ranked_hypotheses_df is None or ranked_hypotheses_df.empty:
        return pd.DataFrame(columns=["dimension_a", "dimension_b", "cramers_v", "p_value", "warning_text"])

    if associations_df is None or associations_df.empty:
        return pd.DataFrame(columns=["dimension_a", "dimension_b", "cramers_v", "p_value", "warning_text"])

    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1.")
    if not 0 <= cramers_v_threshold <= 1:
        raise ValueError("cramers_v_threshold must be between 0 and 1.")

    ranked_dimensions = set(
        ranked_hypotheses_df["dimension"].dropna().astype(str).str.strip().tolist()
    )
    if not ranked_dimensions:
        return pd.DataFrame(columns=["dimension_a", "dimension_b", "cramers_v", "p_value", "warning_text"])

    eligible_pairs = associations_df.loc[
        associations_df["dimension_a"].isin(ranked_dimensions)
        & associations_df["dimension_b"].isin(ranked_dimensions)
        & associations_df["is_statistically_significant"]
        & (associations_df["cramers_v"] >= cramers_v_threshold)
        & (associations_df["p_value"].notna())
        & (associations_df["p_value"] < alpha)
    ].copy()

    if eligible_pairs.empty:
        return pd.DataFrame(columns=["dimension_a", "dimension_b", "cramers_v", "p_value", "warning_text"])

    warnings = []
    for _, row in eligible_pairs.iterrows():
        dimension_a = str(row["dimension_a"])
        dimension_b = str(row["dimension_b"])
        cramers_v = float(row["cramers_v"])
        p_value = float(row["p_value"])
        warnings.append(
            {
                "dimension_a": dimension_a,
                "dimension_b": dimension_b,
                "cramers_v": cramers_v,
                "p_value": p_value,
                "warning_text": (
                    f"Overlapping contributor signal: {dimension_a} and {dimension_b} are statistically associated "
                    f"(Cramér's V={cramers_v:.3f}, p={p_value:.3g}). This overlap means the contributor signals are not independent "
                    "and should be interpreted as shared patterning rather than separate causal factors."
                ),
            }
        )

    return pd.DataFrame(
        warnings,
        columns=["dimension_a", "dimension_b", "cramers_v", "p_value", "warning_text"],
    )
