"""IND320 - entry point of the Streamlit app.

Run locally with:  streamlit run Home.py
st.navigation builds the sidebar menu and groups the pages by topic.
The pages themselves are in the pages/ folder.
"""

import streamlit as st

# Has to come before anything else is drawn
st.set_page_config(page_title="IND320 Energy dashboard", layout="wide")

pages = {
    "": [st.Page("pages/home.py", title="Home", icon=":material/home:", default=True)],
    "Reservoirs": [
        st.Page("pages/data_table.py", title="Data table", icon=":material/table:"),
        st.Page("pages/plot.py", title="Plot", icon=":material/show_chart:"),
        st.Page("pages/reservoir_analysis.py", title="Trends and seasons", icon=":material/insights:"),
    ],
    "Weather": [
        st.Page("pages/weather_outliers.py", title="Outliers and anomalies", icon=":material/thunderstorm:"),
    ],
    "Power exchange": [
        st.Page("pages/cross_border_flows.py", title="Cross-border flows", icon=":material/swap_horiz:"),
    ],
    "Later": [st.Page("pages/coming_soon.py", title="Coming soon", icon=":material/schedule:")],
}
st.navigation(pages).run()
