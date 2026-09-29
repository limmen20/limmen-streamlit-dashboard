"""Page 4: placeholder page with dummy content.

This page will be filled in later parts of the project
(e.g. data from MongoDB and further analysis).
"""

import streamlit as st

st.set_page_config(page_title="Coming soon", layout="wide")
st.title("Coming soon")

st.write("This page is a placeholder for later parts of the IND320 project.")

# Dummy test content to check that the page works
st.subheader("Test content")
st.write("Planned for the next parts:")
st.markdown(
    "- Read the data from MongoDB instead of the local CSV file\n"
    "- More analysis and visualisation of the data"
)
if st.button("Test button"):
    st.success("The button works!")
