from __future__ import annotations

import os
from typing import Dict, Tuple

import matplotlib
matplotlib.use("Agg")  # to run on mac
import matplotlib.pyplot as plt
import geopandas as gpd
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

_CSS = """
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 1rem; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #f0fdf4;
        border-left: 4px solid #16a34a;
        border-radius: 8px;
        padding: 0.75rem 1rem;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #f0fdf4;
        border-right: 1px solid #bbf7d0;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #14532d;
    }

    /* Page title */
    h1 { color: #14532d; letter-spacing: -0.5px; }
    h2, h3 { color: #166534; }

    /* Divider */
    hr { border-color: #d1fae5; margin: 1rem 0; }
</style>
"""


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
        c for c in raw_df.columns
        if pd.api.types.is_numeric_dtype(raw_df[c]) and c != "Year"
    ]
    if numeric_columns:
        return numeric_columns[-1]
    fallback = [c for c in raw_df.columns if pd.api.types.is_numeric_dtype(raw_df[c])]
    return fallback[0] if fallback else None


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
    for c in candidates:
        if c in df.columns:
            return c
    return "ISO_A3" if "ISO_A3" in df.columns else df.columns[0]


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
            prev_year = valid_years[-2]
            last_year = valid_years[-1]
            pivot = (
                work_df[work_df["Year"].isin([prev_year, last_year])]
                .dropna(subset=[country_column, metric_column])
                .pivot_table(index=country_column, columns="Year",
                             values=metric_column, aggfunc="mean")
            )
            if prev_year in pivot.columns and last_year in pivot.columns:
                series = (pivot[last_year] - pivot[prev_year]).dropna()
                if not series.empty:
                    label = (f"Annual Change in {metric_column} "
                             f"({int(prev_year)} → {int(last_year)})")
                    return series, label

    series = (
        work_df.dropna(subset=[country_column, metric_column])
        .groupby(country_column)[metric_column].mean().dropna()
    )
    return series, metric_column


def _format_number(value: float) -> str:
    return f"{value:,.2f}"


def _apply_chart_style(fig: plt.Figure, *axes: plt.Axes) -> None:
    """Apply consistent clean styling to matplotlib figures."""
    fig.patch.set_facecolor("white")
    for ax in axes:
        ax.set_facecolor("#f9fafb")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#d1d5db")
        ax.spines["bottom"].set_color("#d1d5db")
        ax.tick_params(colors="#4b5563", labelsize=9)
        ax.xaxis.label.set_color("#374151")
        ax.yaxis.label.set_color("#374151")
        ax.title.set_color("#111827")
        ax.title.set_fontsize(11)
        ax.title.set_fontweight("bold")
        ax.grid(axis="x", color="#e5e7eb", linewidth=0.8, linestyle="--")
        ax.set_axisbelow(True)


def _plot_map(df: gpd.GeoDataFrame, metric_column: str | None) -> None:
    fig, axis = plt.subplots(figsize=(12, 6), facecolor="white")
    axis.set_facecolor("#dbeafe")  # light ocean blue

    if metric_column and metric_column in df.columns and df[metric_column].notna().any():
        df.plot(
            column=metric_column,
            cmap="YlGn",
            legend=True,
            ax=axis,
            edgecolor="#9ca3af",
            linewidth=0.2,
            missing_kwds={"color": "#e5e7eb", "label": "No data"},
            legend_kwds={"shrink": 0.6, "label": metric_column},
        )
    else:
        df.plot(ax=axis, edgecolor="#9ca3af", linewidth=0.2, color="#d1fae5")

    axis.set_axis_off()
    fig.tight_layout(pad=0)
    st.pyplot(fig)
    plt.close(fig)


def _plot_top_bottom_chart(series: pd.Series, metric_label: str) -> None:
    top_5 = series.nlargest(5).sort_values(ascending=True)
    bottom_5 = series.nsmallest(5).sort_values(ascending=True)

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(14, 5))
    _apply_chart_style(fig, ax_left, ax_right)

    green_shades = ["#bbf7d0", "#86efac", "#4ade80", "#22c55e", "#16a34a"]
    red_shades   = ["#fecaca", "#fca5a5", "#f87171", "#ef4444", "#dc2626"]

    top_5.plot(kind="barh", ax=ax_left, color=green_shades[-len(top_5):])
    bottom_5.plot(kind="barh", ax=ax_right, color=red_shades[:len(bottom_5)])

    ax_left.set_title("Top 5 Countries")
    ax_right.set_title("Bottom 5 Countries")
    ax_left.set_xlabel(metric_label, fontsize=9)
    ax_right.set_xlabel(metric_label, fontsize=9)
    ax_left.set_ylabel("")
    ax_right.set_ylabel("")

    # Value labels on bars
    for ax in [ax_left, ax_right]:
        for bar in ax.patches:
            w = bar.get_width()
            ax.text(
                w + abs(w) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{w:,.1f}", va="center", ha="left", fontsize=8, color="#374151",
            )

    fig.suptitle(metric_label, fontsize=10, color="#6b7280", y=1.01)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def run() -> None:
    st.set_page_config(
        page_title="Okavango Forest Dashboard", page_icon="🌍", layout="wide"
    )
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Header ───────────────────────────────────────────────
    st.title("🌍 Global Forest & Land Dashboard")
    st.caption("Interactive view of forest and land indicators using OWID + Natural Earth data.")

    # ── Data loading ─────────────────────────────────────────
    with st.spinner("Loading datasets …"):
        data_manager = get_app_data_manager()

    dataset_map = _dataset_options()

    # ── Sidebar ───────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## Controls")
        selected_name = st.selectbox("Dataset", list(dataset_map.keys()), label_visibility="collapsed")
        selected_file = dataset_map[selected_name]
        raw_df = _load_raw_dataset(data_manager.download_dir, selected_file)

        metric_column = _choose_dataset_metric(raw_df)

        available_years = _available_years(raw_df, metric_column)
        selected_year = None
        if available_years:
            selected_year = st.selectbox("Year", available_years, index=0)

        st.divider()
        if metric_column:
            st.caption(f"Metric: **{metric_column}**")
        if available_years:
            st.caption(f"Latest data: **{available_years[0]}**")
        st.caption("Source: Our World in Data + Natural Earth")

    selected_df = _build_map_dataframe(data_manager.world, raw_df, selected_year)

    # ── Map + Stats ───────────────────────────────────────────
    map_col, stats_col = st.columns([4, 1], gap="medium")

    with map_col:
        st.markdown(f"### {selected_name}")
        _plot_map(selected_df, metric_column)

    with stats_col:
        st.markdown("### Stats")
        st.metric("Countries", f"{len(selected_df):,}")
        if metric_column and metric_column in selected_df.columns:
            metric_series = pd.to_numeric(selected_df[metric_column], errors="coerce")
            valid_count = int(metric_series.notna().sum())
            st.metric("With data", f"{valid_count:,}")
            if valid_count:
                st.metric("Mean", _format_number(float(metric_series.mean(skipna=True))))
                st.metric("Max", _format_number(float(metric_series.max(skipna=True))))
                st.metric("Min", _format_number(float(metric_series.min(skipna=True))))

    st.divider()

    # ── Insights ─────────────────────────────────────────────
    st.markdown("### Insights")
    st.caption("Top and bottom countries by selected metric (or year-on-year change when available).")

    if metric_column is None:
        st.dataframe(selected_df.describe(include="all"), use_container_width=True)
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
                use_container_width=True,
            )
            return
        _plot_top_bottom_chart(insight_series, insight_label)
    except KeyError:
        st.warning("Required columns missing. Showing summary statistics instead.")
        st.dataframe(selected_df.describe(include="all"), use_container_width=True)
