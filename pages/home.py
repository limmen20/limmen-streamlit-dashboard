"""Home: short intro, a few key numbers and links to the three groups of pages."""

import streamlit as st

from utils import GROUPS, fetch_latest_week

st.title("Norwegian hydropower, weather and power exchange")
st.write(
    "This app is the IND320 *Data to Decision* project. It combines weekly reservoir statistics from NVE's "
    "Magasinstatistikk API, weather from open-meteo (ERA5), exchange rates from Norges Bank and Norway's "
    "cross-border electricity flows, stored in MongoDB."
)

# A few numbers from the newest week (small API call, cached)
try:
    latest = fetch_latest_week()
    norway = latest[latest["area_type"] == "NO"].iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Filling ratio Norway", f"{norway['filling_ratio']:.1%}",
              f"{norway['filling_ratio_change']:+.1%} since previous week")
    c2.metric("Stored energy", f"{norway['filling_TWh']:.1f} TWh")
    c3.metric("Week", f"{norway['iso_week']} / {norway['iso_year']}")
except Exception as error:
    st.warning(f"The latest reservoir numbers could not be downloaded from NVE ({type(error).__name__}).")

st.subheader("Where to start")
cols = st.columns(3)
cards = [
    ("Explore", "What does the data look like?", "pages/map.py", "Map, reservoirs, cross-border flows, exchange rates"),
    ("Patterns & anomalies", "What repeats and what is unusual?", "pages/reservoir_analysis.py",
     "STL and spectrogram, weather outliers (SPC) and anomalies (LOF)"),
    ("Predict", "What comes next?", "pages/correlation.py", "Sliding window correlation and forecast of the filling"),
]
for col, (group, question, page, content) in zip(cols, cards):
    g = GROUPS[group]
    with col.container(border=True):
        st.markdown(f'<div style="height:4px;background:{g["hex"]};border-radius:2px"></div>', unsafe_allow_html=True)
        st.markdown(f"### :{g['color']}[{group}]")
        st.write(f"**{question}**")
        st.caption(content)
        st.page_link(page, label=f"Go to {group}", icon=g["icon"])

st.info("Choose an area in the sidebar or by clicking on the Map. The choice is kept on all analysis pages.")
