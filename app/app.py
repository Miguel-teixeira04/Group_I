from __future__ import annotations

import os
from typing import Dict, Tuple

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from app.data_manager import OkavangoData
from app.merger import merge_dataframes


DATASET_FILES = {
    "Annual Change in Forest Area": "annual_change_forest_area.csv",
    "Annual Deforestation": "annual_deforestation.csv",
    "Share of Protected Land": "share_protected_land.csv",
    "Share of Degraded Land": "share_degraded_land.csv",
    "Share of Forest-Covered Land": "share_covered_forest_land.csv",
}


@st.cache_resource
def get_app_data_manager():
    return OkavangoData()


@st.cache_data
def _load_raw_dataset(download_dir: str, filename: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(download_dir, filename))


def _dataset_options() -> Dict[str, str]:
    return DATASET_FILES.copy()


def _available_years(df: pd.DataFrame, metric_column: str | None) -> list[int]:
    if "Year" not in df.columns:
        return []

    work_df = df.copy()
    if metric_column and metric_column in work_df.columns:
        work_df[metric_column] = pd.to_numeric(work_df[metric_column], errors="coerce")
        work_df = work_df[work_df[metric_column].notna()]

    years = pd.to_numeric(work_df["Year"], errors="coerce").dropna().astype(int)
    return sorted(years.unique().tolist(), reverse=True)


def _choose_dataset_metric(raw_df: pd.DataFrame) -> str | None:
    numeric_columns = [
        column
        for column in raw_df.columns
        if pd.api.types.is_numeric_dtype(raw_df[column]) and column != "Year"
    ]
    if numeric_columns:
        return numeric_columns[-1]

    fallback_numeric = [
        column for column in raw_df.columns if pd.api.types.is_numeric_dtype(raw_df[column])
    ]
    return fallback_numeric[0] if fallback_numeric else None


def _build_map_dataframe(
    world: gpd.GeoDataFrame,
    raw_df: pd.DataFrame,
    selected_year: int | None,
) -> gpd.GeoDataFrame:
    filtered_df = raw_df.copy()
    if selected_year is not None and "Year" in filtered_df.columns:
        years = pd.to_numeric(filtered_df["Year"], errors="coerce")
        filtered_df = filtered_df[years == selected_year].copy()
    return merge_dataframes(world, filtered_df)


def _country_column(df: pd.DataFrame) -> str:
    candidates = ["ADMIN", "Name", "NAME", "Entity", "Country", "ISO_A3"]
    for column in candidates:
        if column in df.columns:
            return column
    return "ISO_A3" if "ISO_A3" in df.columns else df.columns[0]


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return [
        column
        for column in df.columns
        if pd.api.types.is_numeric_dtype(df[column]) and column != "geometry"
    ]


def _series_for_insights(
    df: pd.DataFrame,
    country_column: str,
    metric_column: str,
) -> Tuple[pd.Series, str]:
    work_df = df[
        [country_column, metric_column] + (["Year"] if "Year" in df.columns else [])
    ].copy()
    work_df[metric_column] = pd.to_numeric(work_df[metric_column], errors="coerce")

    if "Year" in work_df.columns:
        work_df["Year"] = pd.to_numeric(work_df["Year"], errors="coerce")
        valid_years = sorted(work_df["Year"].dropna().unique())
        if len(valid_years) >= 2:
            previous_year = valid_years[-2]
            latest_year = valid_years[-1]
            pivot = (
                work_df[work_df["Year"].isin([previous_year, latest_year])]
                .dropna(subset=[country_column, metric_column])
                .pivot_table(
                    index=country_column,
                    columns="Year",
                    values=metric_column,
                    aggfunc="mean",
                )
            )
            if previous_year in pivot.columns and latest_year in pivot.columns:
                series = (pivot[latest_year] - pivot[previous_year]).dropna()
                if not series.empty:
                    label = (
                        f"Annual Change in {metric_column} "
                        f"({int(previous_year)} to {int(latest_year)})"
                    )
                    return series, label

    series = (
        work_df.dropna(subset=[country_column, metric_column])
        .groupby(country_column)[metric_column]
        .mean()
        .dropna()
    )
    return series, metric_column


def _format_number(value: float) -> str:
    return f"{value:,.2f}"


def _plot_map(df: gpd.GeoDataFrame, metric_column: str | None) -> None:
    fig, axis = plt.subplots(figsize=(11, 6))
    if metric_column and metric_column in df.columns and df[metric_column].notna().any():
        df.plot(
            column=metric_column,
            cmap="YlGn",
            legend=True,
            ax=axis,
            edgecolor="#6b7280",
            linewidth=0.25,
            missing_kwds={"color": "#d9d9d9", "label": "No data"},
        )
    else:
        df.plot(ax=axis, edgecolor="#666666", linewidth=0.2, color="#d9d9d9")
    axis.set_axis_off()
    st.pyplot(fig, width="stretch")


def _plot_top_bottom_chart(series: pd.Series, metric_label: str) -> None:
    top_5 = series.nlargest(5).sort_values(ascending=True)
    bottom_5 = series.nsmallest(5)

    fig, (axis_left, axis_right) = plt.subplots(1, 2, figsize=(14, 5))

    top_colors = plt.cm.Greens([0.55, 0.62, 0.70, 0.78, 0.86])[-len(top_5):]
    bottom_colors = plt.cm.Greens([0.28, 0.34, 0.40, 0.46, 0.52])[-len(bottom_5):]

    top_5.plot(kind="barh", ax=axis_left, title="Top 5 Countries", color=top_colors)
    bottom_5.plot(
        kind="barh",
        ax=axis_right,
        title="Bottom 5 Countries",
        color=bottom_colors,
    )

    axis_left.set_xlabel(metric_label)
    axis_left.set_ylabel("Country")
    axis_right.set_xlabel(metric_label)
    axis_right.set_ylabel("Country")

    plt.tight_layout()
    st.pyplot(fig, width="stretch")


def run() -> None:
    st.set_page_config(
        page_title="Okavango Forest Dashboard", page_icon="🌍", layout="wide"
    )

    st.title("🌍 Global Forest & Land Dashboard")
    st.caption(
        "Interactive view of forest and land indicators by country using OWID and Natural Earth data."
    )

    with st.spinner("Loading datasets and map layers..."):
        data_manager = get_app_data_manager()

    dataset_map = _dataset_options()

    st.sidebar.header("Controls")
    selected_name = st.sidebar.selectbox("Choose dataset/map", list(dataset_map.keys()))
    selected_file = dataset_map[selected_name]
    raw_df = _load_raw_dataset(data_manager.download_dir, selected_file)

    metric_column = _choose_dataset_metric(raw_df)
    if metric_column is not None:
        st.sidebar.caption(f"Metric in use: {metric_column}")

    available_years = _available_years(raw_df, metric_column)
    selected_year = None
    if available_years:
        selected_year = st.sidebar.selectbox("Choose year", available_years, index=0)

    selected_df = _build_map_dataframe(data_manager.world, raw_df, selected_year)

    left_col, right_col = st.columns([3, 1])

    with left_col:
        st.subheader("Map")
        st.caption("Displaying one selected map layer at a time.")
        _plot_map(selected_df, metric_column)

    with right_col:
        st.subheader("Dataset Stats")
        st.metric("Rows", f"{len(selected_df):,}")
        st.metric("Columns", f"{selected_df.shape[1]:,}")
        if metric_column and metric_column in selected_df.columns:
            metric_series = pd.to_numeric(selected_df[metric_column], errors="coerce")
            valid_count = metric_series.notna().sum()
            st.metric("Countries with data", f"{int(valid_count):,}")
            if valid_count:
                st.metric(
                    "Mean", _format_number(float(metric_series.mean(skipna=True)))
                )

        if available_years:
            st.caption(f"Data freshness: latest year in selected dataset is {available_years[0]}.")
        st.caption("Source: Our World in Data + Natural Earth")

    st.subheader("Insights")
    st.caption(
        "Top and bottom countries by the selected metric (or computed annual change when possible)."
    )

    if metric_column is None:
        st.dataframe(selected_df.describe(include="all"), width="stretch")
        return

    country_column = _country_column(selected_df)

    try:
        insight_series, insight_label = _series_for_insights(
            selected_df, country_column, metric_column
        )
        if insight_series.empty:
            st.warning("No valid values available for insights after handling missing data.")
            st.dataframe(
                selected_df[[country_column, metric_column]].dropna().head(20),
                width="stretch",
            )
            return
        _plot_top_bottom_chart(insight_series, insight_label)
    except KeyError:
        st.warning(
            "Required columns are missing for charting. Showing summary statistics instead."
        )
        st.dataframe(selected_df.describe(include="all"), width="stretch")
