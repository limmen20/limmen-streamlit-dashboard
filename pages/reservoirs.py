"""Explore - Reservoirs: the old Data table and Plot pages joined on one overview page (tabs).

- Area type: global choice from the sidebar/map. The selected area is drawn thicker in the plot.
- Download interval: a local slider; it decides which months are downloaded from the NVE API.
"""

import plotly.express as px
import streamlit as st

from utils import (AREA_COLORS, AREA_TYPES, COLUMN_COLORS, RATIO_COLUMNS, VALUE_COLUMNS, area_label,
                   current_area, fetch_reservoirs, month_options, page_header)

page_header("Explore", "Reservoirs", "Weekly reservoir statistics from NVE's Magasinstatistikk API.")

area_type, number = current_area()
months = month_options()
start, end = st.select_slider("Download interval (months)", options=months, value=(months[-24], months[-1]))

try:
    df = fetch_reservoirs(start, end)   # cached API download for the chosen interval
except Exception as error:
    st.error(f"Could not download the reservoir data from NVE ({type(error).__name__}). Try again later.")
    st.stop()
data = df[df["area_type"] == area_type]
if data.empty:
    st.warning("No data published for the chosen interval yet.")
    st.stop()
period = start if start == end else f"{start} to {end}"
selected = area_label(area_type, number)

tab_plot, tab_table = st.tabs(["Plot", "Table"])

with tab_plot:
    ALL = "All columns"
    choice = st.selectbox("Column", [ALL] + list(VALUE_COLUMNS.keys()), index=1,
                          format_func=lambda c: c if c == ALL else VALUE_COLUMNS[c])
    few_points = data["date"].nunique() <= 30   # only show markers when there are few weeks

    if choice == ALL:
        # Ratios (0-1) and TWh don't fit on the same axis, so each column is divided by its max (as in part 1)
        scaled = data[["date", "area"]].copy()
        for col, label in VALUE_COLUMNS.items():
            scaled[label] = data[col] / data.groupby("area")[col].transform(lambda s: s.abs().max())
        long_df = scaled.melt(id_vars=["date", "area"], var_name="Column", value_name="Scaled value")
        fig = px.line(long_df, x="date", y="Scaled value", color="Column", facet_row="area", markers=few_points,
                      color_discrete_map={VALUE_COLUMNS[c]: COLUMN_COLORS[c] for c in VALUE_COLUMNS},
                      title=f"All columns, scaled to their maximum - {AREA_TYPES[area_type]}, {period}",
                      labels={"date": "Date", "Scaled value": "Value / max"},
                      height=250 + 220 * data["area"].nunique())
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))   # "area=NO1" -> "NO1"
        fig.update_traces(line_width=2)
        fig.update_traces(line_dash="dash", selector={"name": VALUE_COLUMNS["filling_TWh"]})
        st.caption("Each column is divided by its maximum, so columns with different units share one axis. "
                   "Stored energy (dashed) lies on top of the filling ratio.")
    else:
        fig = px.line(data, x="date", y=choice, color="area", markers=few_points,
                      color_discrete_sequence=AREA_COLORS,
                      title=f"{VALUE_COLUMNS[choice]} - {AREA_TYPES[area_type]}, {period}",
                      labels={"date": "Date", choice: VALUE_COLUMNS[choice], "area": "Area"})
        if choice in RATIO_COLUMNS:
            fig.update_yaxes(tickformat=".0%")
        # The globally selected area is drawn thicker
        fig.update_traces(line_width=1.5)
        fig.update_traces(line_width=4, selector={"name": selected})
        st.caption(f"The selected area (**{selected}**) is drawn thicker. Change it in the sidebar or on the map.")
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, width="stretch")

with tab_table:
    # One row per area. The weekly values are put in lists, which LineChartColumn draws as small charts
    table = (data.groupby("area", sort=False)
             .agg(capacity=("capacity_TWh", "first"), latest=("filling_ratio", "last"),
                  filling=("filling_ratio", list), stored=("filling_TWh", list), change=("filling_ratio_change", list))
             .reset_index())
    st.dataframe(table, hide_index=True, width="stretch", column_config={
        "area": "Area",
        "capacity": st.column_config.NumberColumn("Capacity (TWh)", format="%.1f"),
        "latest": st.column_config.NumberColumn("Latest filling ratio", format="percent"),
        "filling": st.column_config.LineChartColumn("Filling ratio", y_min=0, y_max=1),
        "stored": st.column_config.LineChartColumn("Stored energy (TWh)"),
        "change": st.column_config.LineChartColumn("Weekly change in filling ratio"),
    })
    with st.expander("Show the downloaded rows"):
        st.dataframe(data, hide_index=True, width="stretch")

st.caption("Source: NVE Magasinstatistikk API (biapi.nve.no/magasinstatistikk).")
