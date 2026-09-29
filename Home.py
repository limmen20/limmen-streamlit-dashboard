"""IND320 - Data to Decision: Streamlit app (home page).

Run locally with:  streamlit run Home.py

This is the entry point of a multipage app. Streamlit automatically finds the
files in the `pages/` folder and lists them in the sidebar menu, so the user
can navigate from this front page to the other pages.
"""

import streamlit as st

from utils import load_data

# Page settings (browser tab title, wide layout). Must be the first Streamlit call.
st.set_page_config(page_title="IND320 Reservoir dashboard", layout="wide")

st.title("Norwegian hydropower reservoirs")
st.write(
    "This app is part of the IND320 *Data to Decision* project work. "
    "It shows weekly reservoir filling data for Norway, read from a local CSV file "
    "(`data/reservoirs.csv`)."
)

# Load the data (cached in utils.load_data) to show a few key facts on the front page
df = load_data()

col1, col2, col3 = st.columns(3)
col1.metric("Rows", f"{len(df):,}")
col2.metric("Areas", df["area"].nunique())
col3.metric("Period", f"{df['date'].min():%Y} - {df['date'].max():%Y}")

st.subheader("Pages")
st.markdown(
    "- **Data table** - one row per data column, with a small line chart of the first month.\n"
    "- **Plot** - choose a column (or all columns) and a range of months to plot.\n"
    "- **Coming soon** - placeholder page for later parts of the project."
)
st.info("Use the menu in the sidebar to navigate between the pages.")
