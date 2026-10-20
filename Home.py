"""IND320 - home page of the Streamlit app.

Run locally with:  streamlit run Home.py
Streamlit finds the files in pages/ by itself and puts them in the sidebar menu.
"""

import streamlit as st

from utils import fetch_latest_week

# Has to be the first Streamlit command on the page
st.set_page_config(page_title="IND320 Energy dashboard", layout="wide")

st.title("Norwegian hydropower and power exchange")
st.write(
    "This app is part of the IND320 *Data to Decision* project work. It shows weekly reservoir "
    "statistics from NVE's Magasinstatistikk API and Norway's cross-border electricity flows, "
    "stored in a MongoDB database."
)

# A few numbers from the newest week
latest = fetch_latest_week()
norway = latest[latest["area_type"] == "NO"].iloc[0]
col1, col2, col3 = st.columns(3)
col1.metric("Filling ratio Norway", f"{norway['filling_ratio']:.1%}",
            f"{norway['filling_ratio_change']:+.1%} since previous week")
col2.metric("Stored energy", f"{norway['filling_TWh']:.1f} TWh")
col3.metric("Week", f"{norway['iso_week']} / {norway['iso_year']}")

st.subheader("Pages")
st.markdown(
    "- **Data table** - one row per area, with small line charts of the weekly values.\n"
    "- **Plot** - one line per area for a chosen column (or all columns).\n"
    "- **Cross-border flows** - flows into and out of Norway per connection (from MongoDB).\n"
    "- **Coming soon** - placeholder page for later parts of the project.\n\n"
    "On the Data table and Plot pages, the area type and the download interval are chosen in "
    "the sidebar and shared between the two pages."
)
st.info("Use the menu in the sidebar to navigate between the pages.")
