"""IND320 - Data to Decision: Streamlit app (home page).

Run locally with:  streamlit run Home.py

This is the entry point of a multipage app. Streamlit automatically finds the
files in the `pages/` folder and lists them in the sidebar menu.
"""

import streamlit as st

from utils import fetch_latest_week

# Page settings (browser tab title, wide layout). Must be the first Streamlit call.
st.set_page_config(page_title="IND320 Energy dashboard", layout="wide")

st.title("Norwegian hydropower and power exchange")
st.write(
    "This app is part of the IND320 *Data to Decision* project work. It shows weekly reservoir "
    "statistics from NVE's Magasinstatistikk API and Norway's cross-border electricity flows, "
    "stored in a MongoDB database."
)

# Key numbers from the latest published week (small API call, cached in utils.py)
latest = fetch_latest_week()
norway = latest[latest["area_type"] == "NO"].iloc[0]
col1, col2, col3 = st.columns(3)
col1.metric("Filling ratio Norway", f"{norway['filling_ratio']:.1%}",
            f"{norway['filling_ratio_change']:+.1%} since previous week")
col2.metric("Stored energy", f"{norway['filling_TWh']:.1f} TWh")
col3.metric("Week", f"{norway['iso_week']} / {norway['iso_year']}")

st.subheader("Pages")
st.markdown(
    "- **Reservoirs** - choose area type and period; plot and table with one line per area.\n"
    "- **Cross-border flows** - flows into and out of Norway per connection (from MongoDB)."
)
st.info("Use the menu in the sidebar to navigate between the pages.")
