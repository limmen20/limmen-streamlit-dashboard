"""Page 4: cross-border flows - electricity flowing into and out of Norway, read from MongoDB.

The page is split in two columns with st.columns:
- left: st.radio chooses the connection and st.selectbox the year -> pie chart (in vs. out)
- right: st.pills chooses the months -> line plot with one line per connection and direction
An st.expander below the columns documents where the data come from.
"""

import calendar

import plotly.express as px
import streamlit as st

from utils import CONNECTION_COLORS, DIRECTION_COLORS, EXPORT, IMPORT, load_flows

st.set_page_config(page_title="Cross-border flows", layout="wide")
st.title("Cross-border flows")

try:
    flows = load_flows()   # daily totals per connection and direction (cached MongoDB query)
except Exception:
    st.error("Could not read the data from MongoDB. Check the connection string in the app's secrets.")
    st.stop()
if flows.empty:
    st.warning("The MongoDB collection is empty. Run the part 2 notebook to fill it.")
    st.stop()
connections = [c for c in CONNECTION_COLORS if c in set(flows["connection"])]
years = sorted(flows["year"].unique())

left, right = st.columns(2)

# --- Left: pie chart for one connection and one year ---------------------------------------
with left:
    connection = st.radio("Connection", connections, horizontal=True)
    year = st.selectbox("Year", years, index=years.index(2025) if 2025 in years else 0)

    totals = (flows[(flows["connection"] == connection) & (flows["year"] == year)]
              .groupby("direction", as_index=False)["gwh"].sum())
    fig = px.pie(
        totals, names="direction", values="gwh",
        color="direction", color_discrete_map=DIRECTION_COLORS,
        title=f"Norway - {connection}, total flow {year}",
    )
    fig.update_traces(
        texttemplate="%{label}<br>%{value:,.0f} GWh (%{percent})",
        marker_line_color="white", marker_line_width=2, sort=False,
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")

# --- Right: line plot for any set of months in the chosen year -----------------------------
with right:
    year_flows = flows[flows["year"] == year]
    available = sorted(year_flows["month"].unique())
    chosen = st.pills(
        "Months", available, selection_mode="multi",
        default=[available[0]], format_func=lambda m: calendar.month_abbr[m],
    )
    if not chosen:
        st.info("Choose at least one month.")
    else:
        data = year_flows[year_flows["month"].isin(chosen)].sort_values("date")
        fig = px.line(
            data, x="date", y="gwh",
            color="connection", line_dash="direction",
            color_discrete_map=CONNECTION_COLORS,
            line_dash_map={IMPORT: "solid", EXPORT: "dash"},
            title=f"Daily flows per connection and direction, {year}",
            labels={"date": "Date", "gwh": "Energy per day (GWh)",
                    "connection": "Connection", "direction": "Direction"},
        )
        fig.update_traces(line_width=2)
        st.plotly_chart(fig, width="stretch")
        st.caption("Solid = into Norway, dashed = out of Norway. "
                   "Click a legend entry to hide a line, double-click to show only that line.")

# --- Documentation of the data source -------------------------------------------------------
with st.expander("About the data on this page"):
    st.markdown(
        f"""
- **What:** cross-border physical electricity flows between Norway and its six neighbouring
  countries, in both directions, summed to daily totals in GWh.
- **Original source:** ENTSO-E Transparency Platform, *Cross-Border Physical Flows* (document
  type A11). Retrieved via: {flows['source'].iloc[0]}.
- **Period:** {flows['date'].min():%d %B %Y} to {flows['date'].max():%d %B %Y} (the last two years).
- **Processing:** downloaded in the Jupyter Notebook, stored hourly in a local Cassandra database
  with Spark, summed to daily values with Spark and inserted into MongoDB, which this page reads.
"""
    )
