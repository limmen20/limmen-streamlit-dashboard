"""Page 5: placeholder page with dummy content (moved from page 4 in part 2).

This page will be filled in later parts of the project
(e.g. further analysis of the data).
"""

import streamlit as st

st.set_page_config(page_title="Coming soon", layout="wide")
st.title("Coming soon")

st.write("This page is a placeholder for later parts of the IND320 project.")

# Dummy test content to check that the page works
st.subheader("Test content")
st.write("Planned for the next parts:")
st.markdown(
    "- More analysis and visualisation of the data\n"
    "- Combining reservoir levels with the cross-border flows"
)
if st.button("Test button"):
    st.success("The button works!")
