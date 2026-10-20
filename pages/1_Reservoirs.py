"""Reservoirs: plot and table of NVE's weekly reservoir statistics.

The table and the plot from part 1 (previously pages two and three) are combined on one page,
so the same controls work for both:
- st.radio chooses the area type (NO, EL or VASS); plot and table show one line per area number.
- st.select_slider chooses the months that are downloaded from the NVE API.
"""

import plotly.express as px
import streamlit as st

from utils import (AREA_COLORS, AREA_TYPES, RATIO_COLUMNS, VALUE_COLUMNS,
                   fetch_reservoirs, month_options)

st.set_page_config(page_title="Reservoirs", layout="wide")
st.title("Reservoirs")

# --- Controls -------------------------------------------------------------------------------
left, right = st.columns([1, 2])
area_type = left.radio("Area type", list(AREA_TYPES), format_func=AREA_TYPES.get)

# Range slider over all months since 1995. The chosen range decides what is downloaded;
# the default is the last two years.
months = month_options()
start, end = right.select_slider(
    "Download interval (months)", options=months, value=(months[-24], months[-1])
)
column = right.selectbox("Column to plot", list(VALUE_COLUMNS), format_func=VALUE_COLUMNS.get)

# --- Data ----------------------------------------------------------------------------------
df = fetch_reservoirs(start, end)          # cached API download for the chosen interval
data = df[df["area_type"] == area_type]    # only the chosen area type
if data.empty:
    st.warning("No data published for the chosen interval yet.")
    st.stop()
period = start if start == end else f"{start} to {end}"

# --- Plot: one line per area number --------------------------------------------------------
fig = px.line(
    data,
    x="date",
    y=column,
    color="area",
    markers=len(data["date"].unique()) <= 30,   # markers only when there are few points
    color_discrete_sequence=AREA_COLORS,
    title=f"{VALUE_COLUMNS[column]} - {AREA_TYPES[area_type]}, {period}",
    labels={"date": "Date", column: VALUE_COLUMNS[column], "area": "Area"},
)
if column in RATIO_COLUMNS:
    fig.update_yaxes(tickformat=".0%")   # show fractions as percentages
fig.update_layout(hovermode="x unified")
fig.update_traces(line_width=2)
st.plotly_chart(fig, width="stretch")

# --- Table: one row per area number, with row-wise line charts ------------------------------
st.subheader("Table")
st.caption(f"One row per area. The small charts show the weekly values for {period}.")
table = (
    data.groupby("area", sort=False)
    .agg(
        capacity=("capacity_TWh", "first"),
        latest=("filling_ratio", "last"),
        filling=("filling_ratio", list),          # lists are drawn by LineChartColumn
        stored=("filling_TWh", list),
        change=("filling_ratio_change", list),
    )
    .reset_index()
)
st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    column_config={
        "area": "Area",
        "capacity": st.column_config.NumberColumn("Capacity (TWh)", format="%.1f"),
        "latest": st.column_config.NumberColumn("Latest filling ratio", format="percent"),
        "filling": st.column_config.LineChartColumn("Filling ratio", y_min=0, y_max=1),
        "stored": st.column_config.LineChartColumn("Stored energy (TWh)"),
        "change": st.column_config.LineChartColumn("Weekly change"),
    },
)
st.caption("Source: NVE Magasinstatistikk API (biapi.nve.no/magasinstatistikk).")
