"""Page 3: reservoir plot.

Area type and period are picked in the sidebar (shared with the Data table page).
The selectbox picks one column or all columns. One line per area.
"""

import plotly.express as px
import streamlit as st

from utils import (AREA_COLORS, AREA_TYPES, COLUMN_COLORS, RATIO_COLUMNS, VALUE_COLUMNS,
                   fetch_reservoirs, reservoir_controls)

st.set_page_config(page_title="Plot", layout="wide")
st.title("Plot of reservoir data")

area_type, start, end = reservoir_controls()   # radio + slider in the sidebar
df = fetch_reservoirs(start, end)
data = df[df["area_type"] == area_type]
if data.empty:
    st.warning("No data published for the chosen interval yet.")
    st.stop()
period = start if start == end else f"{start} to {end}"

ALL = "All columns"
choice = st.selectbox(
    "Column",
    [ALL] + list(VALUE_COLUMNS.keys()),
    index=1,   # start with the filling ratio
    format_func=lambda c: c if c == ALL else VALUE_COLUMNS[c],
)
few_points = data["date"].nunique() <= 30   # only show markers when there are few weeks

if choice == ALL:
    # Ratios (0-1) and TWh don't fit on the same axis, so each column is divided by
    # its max (like in part 1). One small plot per area.
    scaled = data[["date", "area"]].copy()
    for col, label in VALUE_COLUMNS.items():
        scaled[label] = data[col] / data.groupby("area")[col].transform(lambda s: s.abs().max())
    long_df = scaled.melt(id_vars=["date", "area"], var_name="Column", value_name="Scaled value")
    n_areas = data["area"].nunique()
    fig = px.line(
        long_df, x="date", y="Scaled value", color="Column", facet_row="area",
        markers=few_points,
        color_discrete_map={VALUE_COLUMNS[c]: COLUMN_COLORS[c] for c in VALUE_COLUMNS},
        title=f"All columns, scaled to their maximum - {AREA_TYPES[area_type]}, {period}",
        labels={"date": "Date", "Scaled value": "Value / max"},
        height=250 + 220 * n_areas,
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))   # "area=NO1" -> "NO1"
    # Stored energy = filling ratio x capacity, so the lines overlap. Dashed so both show
    fig.update_traces(line_dash="dash", selector={"name": VALUE_COLUMNS["filling_TWh"]})
    st.caption("Each column is divided by its maximum, so columns with different units share one axis. "
               "Stored energy (dashed) lies on top of the filling ratio.")
else:
    fig = px.line(
        data, x="date", y=choice, color="area",
        markers=few_points,
        color_discrete_sequence=AREA_COLORS,
        title=f"{VALUE_COLUMNS[choice]} - {AREA_TYPES[area_type]}, {period}",
        labels={"date": "Date", choice: VALUE_COLUMNS[choice], "area": "Area"},
    )
    if choice in RATIO_COLUMNS:
        fig.update_yaxes(tickformat=".0%")

fig.update_layout(hovermode="x unified")   # one tooltip for all lines at a date
fig.update_traces(line_width=2)
st.plotly_chart(fig, width="stretch")
st.caption("Source: NVE Magasinstatistikk API (biapi.nve.no/magasinstatistikk).")
