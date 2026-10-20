"""Page 2: table of the reservoir data from the NVE API.

The area type (radio buttons) and the download interval (slider) are chosen in the sidebar and
shared with the Plot page. The table has one row per area number, and the row-wise
LineChartColumn draws the weekly values of each area as a small line chart.
"""

import streamlit as st

from utils import AREA_TYPES, fetch_reservoirs, reservoir_controls

st.set_page_config(page_title="Data table", layout="wide")
st.title("Data table")

area_type, start, end = reservoir_controls()   # sidebar: radio + download interval slider
df = fetch_reservoirs(start, end)              # cached API download for the chosen interval
data = df[df["area_type"] == area_type]
if data.empty:
    st.warning("No data published for the chosen interval yet.")
    st.stop()
period = start if start == end else f"{start} to {end}"

st.write(f"Weekly values for **{AREA_TYPES[area_type]}**, {period}. One row per area.")

# One row per area number; the weekly values are collected as lists for LineChartColumn
table = (
    data.groupby("area", sort=False)
    .agg(
        capacity=("capacity_TWh", "first"),
        latest=("filling_ratio", "last"),
        filling=("filling_ratio", list),
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
        "change": st.column_config.LineChartColumn("Weekly change in filling ratio"),
    },
)

# The downloaded rows themselves, for the chosen area type
with st.expander("Show the downloaded rows"):
    st.dataframe(data, hide_index=True, width="stretch")
st.caption("Source: NVE Magasinstatistikk API (biapi.nve.no/magasinstatistikk).")
