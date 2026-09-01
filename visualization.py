"""
Visualization module for Bank Data AI.

Provides intelligent chart selection heuristics and rendering functions
based on DataFrame dimensions, data types, and distribution properties.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st


def get_chart_recommendation(df: Optional[pd.DataFrame]) -> Optional[Dict[str, Any]]:
    """
    Analyzes DataFrame structure and determines the best visualization strategy:
    - Single row KPI metrics -> 'metric'
    - Categorical comparison -> 'bar'
    - Time-series trend -> 'line'
    - Two numeric dimensions -> 'scatter'
    - Single continuous numeric distribution (>20 rows) -> 'histogram'
    - Complex/unsuitable structures -> None (Table only)
    """
    if df is None or df.empty:
        return None

    num_rows, num_cols = df.shape

    # Find numeric columns with at least one non-null value
    valid_numeric_cols = [
        col for col in df.select_dtypes(include=["number"]).columns
        if df[col].notna().any() and not (df[col].dropna() == 0).all()
    ]

    # Exclude primary keys and ID columns from being primary chart dimensions if other numeric cols exist
    non_id_numeric_cols = [
        c for c in valid_numeric_cols if not c.lower().endswith("_id") and c.lower() != "id"
    ]
    primary_numeric_cols = non_id_numeric_cols if non_id_numeric_cols else valid_numeric_cols

    # Case 1: Single-row KPI metric summary
    if num_rows == 1:
        if 1 <= len(primary_numeric_cols) <= 4:
            return {"type": "metric", "columns": primary_numeric_cols}
        return None

    # Identify date / temporal columns
    date_cols = [
        c for c in df.columns
        if "date" in c.lower()
        or "time" in c.lower()
        or pd.api.types.is_datetime64_any_dtype(df[c])
    ]

    # Identify categorical columns
    categorical_cols = [
        c for c in df.columns
        if c not in valid_numeric_cols and c not in date_cols
    ]

    # Case 2: Time-series / Date Trend (Date col + Numeric col)
    if date_cols and primary_numeric_cols and num_rows > 1:
        date_col = date_cols[0]
        num_col = primary_numeric_cols[0]
        valid_df = df[[date_col, num_col]].dropna()
        if len(valid_df) > 1:
            return {"type": "line", "x": date_col, "y": num_col}

    # Case 3: Categorical Comparison Bar Chart (Category + Numeric, 2 to 30 categories)
    if categorical_cols and primary_numeric_cols and 1 < num_rows <= 30:
        cat_col = categorical_cols[0]
        num_col = primary_numeric_cols[0]
        valid_df = df[[cat_col, num_col]].dropna()
        if len(valid_df) > 1:
            return {"type": "bar", "x": cat_col, "y": num_col}

    # Case 4: Scatter Plot (2+ Numeric Columns, multi-row, non-categorical)
    if len(primary_numeric_cols) >= 2 and num_rows > 5 and not categorical_cols:
        x_col = primary_numeric_cols[0]
        y_col = primary_numeric_cols[1]
        valid_df = df[[x_col, y_col]].dropna()
        if len(valid_df) > 3:
            return {"type": "scatter", "x": x_col, "y": y_col}

    # Case 5: Single Numeric Distribution Histogram (>20 rows, single numeric column)
    if len(primary_numeric_cols) == 1 and num_rows > 20 and not categorical_cols:
        num_col = primary_numeric_cols[0]
        valid_df = df[[num_col]].dropna()
        if len(valid_df) > 20:
            return {"type": "histogram", "column": num_col}

    # No suitable chart — render table only
    return None


def render_visualization(df: pd.DataFrame) -> None:
    """Renders the recommended visualization cleanly in Streamlit."""
    recommendation = get_chart_recommendation(df)
    if not recommendation:
        return

    chart_type = recommendation.get("type")

    if chart_type == "metric":
        cols_to_show = recommendation.get("columns", [])
        st.markdown("**📈 Key Metric Summary**")
        metric_cols = st.columns(len(cols_to_show))
        for i, col_name in enumerate(cols_to_show):
            val = df[col_name].iloc[0]
            if pd.notna(val):
                formatted = (
                    f"{val:,.2f}"
                    if isinstance(val, (float, int)) and not float(val).is_integer()
                    else f"{val:,}" if isinstance(val, int) else str(val)
                )
            else:
                formatted = "NULL"
            label = col_name.replace("_", " ").title()
            metric_cols[i].metric(label=label, value=formatted)

    elif chart_type == "line":
        x_col = recommendation["x"]
        y_col = recommendation["y"]
        chart_df = df[[x_col, y_col]].dropna().sort_values(by=x_col).set_index(x_col)
        if not chart_df.empty:
            st.markdown(f"**📈 Trend Analysis ({y_col.replace('_', ' ')} over {x_col.replace('_', ' ')})**")
            st.line_chart(chart_df)

    elif chart_type == "bar":
        x_col = recommendation["x"]
        y_col = recommendation["y"]
        chart_df = (
            df[[x_col, y_col]]
            .dropna()
            .sort_values(by=y_col, ascending=False)
            .set_index(x_col)
        )
        if not chart_df.empty:
            st.markdown(f"**📊 Category Breakdown ({y_col.replace('_', ' ')} by {x_col.replace('_', ' ')})**")
            st.bar_chart(chart_df)

    elif chart_type == "scatter":
        x_col = recommendation["x"]
        y_col = recommendation["y"]
        chart_df = df[[x_col, y_col]].dropna()
        if not chart_df.empty:
            st.markdown(f"**🔍 Correlation ({y_col.replace('_', ' ')} vs {x_col.replace('_', ' ')})**")
            st.scatter_chart(chart_df, x=x_col, y=y_col)

    elif chart_type == "histogram":
        num_col = recommendation["column"]
        try:
            import altair as alt
            hist_chart = (
                alt.Chart(df)
                .mark_bar(color="#0284C7")
                .encode(
                    alt.X(f"{num_col}:Q", bin=alt.Bin(maxbins=20), title=num_col.replace("_", " ")),
                    alt.Y("count()", title="Frequency"),
                )
                .properties(height=280)
            )
            st.markdown(f"**📊 Distribution of {num_col.replace('_', ' ')}**")
            st.altair_chart(hist_chart, use_container_width=True)
        except Exception:
            chart_df = df[[num_col]].dropna()
            st.markdown(f"**📊 Distribution of {num_col.replace('_', ' ')}**")
            st.line_chart(chart_df)
