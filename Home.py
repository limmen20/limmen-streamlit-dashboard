"""IND320 - entry point of the Streamlit app.

Run locally with:  streamlit run Home.py

Structure (see the sketch in the part 4 notebook): a front page and three groups of pages,
- Explore: what the data looks like (map, reservoirs, cross-border flows, exchange rates)
- Patterns & anomalies: what repeats and what is unusual (STL/spectrogram, weather outliers)
- Predict: what comes next (sliding window correlation, forecast)
The area is a global choice (sidebar or map click) kept in st.session_state for all pages.
"""

import streamlit as st

from utils import global_area_controls

# Has to come before anything else is drawn
st.set_page_config(page_title="IND320 Energy dashboard", page_icon=":material/water_drop:", layout="wide")

# Streamlit forgets widget values on pages where the widget is not drawn. Saving them again here
# keeps the global choices when you visit a page without the area controls (e.g. Home).
for key in ("area_type", "area_number", "map_month"):
    if key in st.session_state:
        st.session_state[key] = st.session_state[key]

pages = {
    "": [st.Page("pages/home.py", title="Home", icon=":material/home:", default=True)],
    "Explore": [
        st.Page("pages/map.py", title="Map", icon=":material/map:"),
        st.Page("pages/reservoirs.py", title="Reservoirs", icon=":material/water:"),
        st.Page("pages/cross_border_flows.py", title="Cross-border flows", icon=":material/swap_horiz:"),
        st.Page("pages/currency.py", title="Exchange rates", icon=":material/currency_exchange:"),
    ],
    "Patterns & anomalies": [
        st.Page("pages/reservoir_analysis.py", title="Trends and seasons", icon=":material/insights:"),
        st.Page("pages/weather_outliers.py", title="Weather outliers", icon=":material/thunderstorm:"),
    ],
    "Predict": [
        st.Page("pages/correlation.py", title="Correlation", icon=":material/compare_arrows:"),
        st.Page("pages/forecast.py", title="Forecast", icon=":material/trending_up:"),
    ],
}
page = st.navigation(pages)

# The area controls are only shown on pages that use an area
if page.url_path in {"map", "reservoirs", "reservoir_analysis", "weather_outliers", "correlation", "forecast"}:
    global_area_controls()

page.run()
