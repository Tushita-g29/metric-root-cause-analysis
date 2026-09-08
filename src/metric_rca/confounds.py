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


def measure_ranked_segment_overlap(
    df: pd.DataFrame,
    ranked_hypotheses_df: pd.DataFrame,
    current_start: str,
    current_end: str,
    top_n: int = 5,
) -> pd.DataFrame:
    """Measure overlap between ranked segments from different dimensions in the current period."""
    if df is None or df.empty:
        raise ValueError("df cannot be empty.")
    if ranked_hypotheses_df is None or ranked_hypotheses_df.empty:
        raise ValueError("ranked_hypotheses_df cannot be empty.")
    if "event_date" not in df.columns:
        raise ValueError("df must include an 'event_date' column.")
    if "dimension" not in ranked_hypotheses_df.columns or "segment" not in ranked_hypotheses_df.columns:
        raise ValueError("ranked_hypotheses_df must include 'dimension' and 'segment' columns.")
    if top_n <= 0:
        raise ValueError("top_n must be a positive integer.")

    try:
        start_dt = pd.to_datetime(current_start)
        end_dt = pd.to_datetime(current_end)
    except Exception as exc:
        raise ValueError("current_start and current_end must be valid dates.") from exc

    if start_dt > end_dt:
        raise ValueError("current_start must be on or before current_end.")

    current_period = df.loc[(df["event_date"] >= start_dt) & (df["event_date"] <= end_dt)].copy()
    if current_period.empty:
        raise ValueError("No rows in df fall within the inclusive current-period date range.")

    ranked = ranked_hypotheses_df.copy()
    if "rank" in ranked.columns:
        ranked = ranked.sort_values("rank").copy()
    ranked = ranked.head(int(top_n)).copy()
    if ranked.empty:
        raise ValueError("No ranked contributor rows are available for the requested top_n selection.")

    rows: list[dict[str, object]] = []
    total_rows = len(current_period)

    for left_index in range(len(ranked)):
        for right_index in range(left_index + 1, len(ranked)):
            row_a = ranked.iloc[left_index]
            row_b = ranked.iloc[right_index]
            dimension_a = str(row_a["dimension"]).strip()
            segment_a = str(row_a["segment"]).strip()
            dimension_b = str(row_b["dimension"]).strip()
            segment_b = str(row_b["segment"]).strip()

            if dimension_a == dimension_b:
                continue
            if dimension_a not in current_period.columns or dimension_b not in current_period.columns:
                raise ValueError(f"Current-period df is missing required dimensions: {dimension_a}, {dimension_b}")

            a_mask = current_period[dimension_a].astype(str).str.strip().eq(segment_a)
            b_mask = current_period[dimension_b].astype(str).str.strip().eq(segment_b)
            n_a = int(a_mask.sum())
            n_b = int(b_mask.sum())
            n_both = int((a_mask & b_mask).sum())

            if n_a == 0 or n_b == 0:
                pct_b_given_a = np.nan
                pct_a_given_b = np.nan
                lift = np.nan
                chi_square_statistic = np.nan
                p_value = np.nan
                phi_coefficient = np.nan
            else:
                pct_b_given_a = float(n_both / n_a)
                pct_a_given_b = float(n_both / n_b)
                lift = float((n_both / n_a) / (n_b / total_rows)) if n_b > 0 and total_rows > 0 else np.nan
                table = np.array(
                    [[n_both, n_a - n_both], [n_b - n_both, total_rows - n_a - n_b + n_both]],
                    dtype=float,
                )
                if np.any(table < 0):
                    chi_square_statistic = np.nan
                    p_value = np.nan
                    phi_coefficient = np.nan
                elif np.all(table == 0) or np.any(table.sum(axis=1) == 0) or np.any(table.sum(axis=0) == 0):
                    chi_square_statistic = np.nan
                    p_value = np.nan
                    phi_coefficient = np.nan
                else:
                    try:
                        chi_square_statistic, p_value, _, _ = chi2_contingency(table, correction=False)
                    except ValueError:
                        chi_square_statistic = np.nan
                        p_value = np.nan
                        phi_coefficient = np.nan
                    else:
                        a, b, c, d = table.ravel()
                        denominator = np.sqrt((a + b) * (c + d) * (a + c) * (b + d))
                        phi_coefficient = 0.0 if denominator == 0 else float(abs((a * d - b * c) / denominator))

            rows.append(
                {
                    "dimension_a": dimension_a,
                    "segment_a": segment_a,
                    "dimension_b": dimension_b,
                    "segment_b": segment_b,
                    "rows_in_a": n_a,
                    "rows_in_b": n_b,
                    "rows_in_both": n_both,
                    "pct_b_given_a": pct_b_given_a,
                    "pct_a_given_b": pct_a_given_b,
                    "lift": lift,
                    "chi_square_statistic": chi_square_statistic,
                    "p_value": p_value,
                    "phi_coefficient": phi_coefficient,
                }
            )

    return pd.DataFrame(
        rows,
        columns=[
            "dimension_a",
            "segment_a",
            "dimension_b",
            "segment_b",
            "rows_in_a",
            "rows_in_b",
            "rows_in_both",
            "pct_b_given_a",
            "pct_a_given_b",
            "lift",
            "chi_square_statistic",
            "p_value",
            "phi_coefficient",
        ],
    )


def flag_segment_overlap_warnings(
    overlaps_df: pd.DataFrame,
    conditional_share_threshold: float = 0.70,
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Return only overlap warnings for pairs with strong conditional sharing and statistical significance."""
    required_columns = {
        "dimension_a",
        "segment_a",
        "dimension_b",
        "segment_b",
        "pct_b_given_a",
        "pct_a_given_b",
        "p_value",
    }

    if overlaps_df is None or overlaps_df.empty:
        return pd.DataFrame(
            columns=[
                "dimension_a",
                "segment_a",
                "dimension_b",
                "segment_b",
                "pct_b_given_a",
                "pct_a_given_b",
                "p_value",
                "warning_text",
            ]
        )
    if not required_columns.issubset(overlaps_df.columns):
        raise ValueError(
            "overlaps_df must include 'dimension_a', 'segment_a', 'dimension_b', 'segment_b', 'pct_b_given_a', 'pct_a_given_b', and 'p_value'."
        )
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1.")
    if not 0 <= conditional_share_threshold <= 1:
        raise ValueError("conditional_share_threshold must be between 0 and 1.")

    warnings = overlaps_df.loc[
        overlaps_df["p_value"].notna()
        & (overlaps_df["p_value"] < alpha)
        & (
            (overlaps_df["pct_b_given_a"] >= conditional_share_threshold)
            | (overlaps_df["pct_a_given_b"] >= conditional_share_threshold)
        )
    ].copy()

    if warnings.empty:
        return pd.DataFrame(
            columns=[
                "dimension_a",
                "segment_a",
                "dimension_b",
                "segment_b",
                "pct_b_given_a",
                "pct_a_given_b",
                "p_value",
                "warning_text",
            ]
        )

    warnings["warning_text"] = warnings.apply(
        lambda row: (
            f"Overlapping ranked contributor signals: {row['segment_a']} in {row['dimension_a']} and {row['segment_b']} in {row['dimension_b']} "
            f"share {max(float(row['pct_b_given_a']), float(row['pct_a_given_b'])):.2%} of the signal in the paired group. "
            "These signals overlap and should not be presented as independent causes."
        ),
        axis=1,
    )

    return warnings[[
        "dimension_a",
        "segment_a",
        "dimension_b",
        "segment_b",
        "pct_b_given_a",
        "pct_a_given_b",
        "p_value",
        "warning_text",
    ]].reset_index(drop=True)
