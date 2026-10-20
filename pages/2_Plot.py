"""Page 3: interactive plot of the reservoir data from the NVE API.

- Sidebar (shared with the Data table page): radio buttons for the area type and a slider
  that controls which months are downloaded.
- st.selectbox chooses a single column or all columns together.
The plot shows one line per area number of the chosen area type.
"""

import plotly.express as px
import streamlit as st

from utils import (AREA_COLORS, AREA_TYPES, COLUMN_COLORS, RATIO_COLUMNS, VALUE_COLUMNS,
                   fetch_reservoirs, reservoir_controls)

st.set_page_config(page_title="Plot", layout="wide")
st.title("Plot of reservoir data")

area_type, start, end = reservoir_controls()   # sidebar: radio + download interval slider
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
    index=1,   # filling ratio
    format_func=lambda c: c if c == ALL else VALUE_COLUMNS[c],
)
few_points = data["date"].nunique() <= 30   # markers only when there are few weeks

if choice == ALL:
    # The columns have very different scales (fractions vs. TWh), so each column is divided
    # by its largest absolute value per area. One small plot per area, all columns on one axis.
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
    fig.update_traces(line_dash="dash", selector={"name": VALUE_COLUMNS["filling_TWh"]})
    st.caption("Each column is divided by its maximum, so columns with different units share one axis. "
               "Stored energy (dashed) lies on top of the filling ratio.")
else:
    # One line per area number of the chosen area type
    fig = px.line(
        data, x="date", y=choice, color="area",
        markers=few_points,
        color_discrete_sequence=AREA_COLORS,
        title=f"{VALUE_COLUMNS[choice]} - {AREA_TYPES[area_type]}, {period}",
        labels={"date": "Date", choice: VALUE_COLUMNS[choice], "area": "Area"},
    )
    if choice in RATIO_COLUMNS:
        fig.update_yaxes(tickformat=".0%")   # show fractions as percentages

fig.update_layout(hovermode="x unified")
fig.update_traces(line_width=2)
st.plotly_chart(fig, width="stretch")
st.caption("Source: NVE Magasinstatistikk API (biapi.nve.no/magasinstatistikk).")
