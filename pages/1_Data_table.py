"""Page 2: table of the imported data.

One row per data column. The last table column uses Streamlit's row-wise
LineChartColumn to draw a small line chart of the first month of each series.
"""

import pandas as pd
import streamlit as st

from utils import VALUE_COLUMNS, area_selector, load_data

st.set_page_config(page_title="Data table", layout="wide")
st.title("Data table")

df = load_data()  # cached, so switching pages does not re-read the CSV

# The CSV holds several areas; pick one so each column is a single time series
area = area_selector(df)
area_df = df[df["area"] == area]

# First month of the data series (the earliest year-month in the data)
first_month = area_df["month"].min()
first_df = area_df[area_df["month"] == first_month]

st.write(
    f"Weekly values for **{area}** in the first month of the data (**{first_month}**, "
    f"{len(first_df)} weeks). One row per column in the imported data."
)

# Build the table: one row per data column, with the first-month values as a list.
# LineChartColumn draws a list of numbers in a cell as a small line chart.
table = pd.DataFrame(
    {
        "Column": list(VALUE_COLUMNS.keys()),
        "Description": list(VALUE_COLUMNS.values()),
        "Mean (first month)": [first_df[c].mean() for c in VALUE_COLUMNS],
        "First month": [first_df[c].tolist() for c in VALUE_COLUMNS],
    }
)

st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    column_config={
        "Mean (first month)": st.column_config.NumberColumn(format="%.3f"),
        "First month": st.column_config.LineChartColumn(
            "First month",
            help="Weekly values in the first month (each row has its own y-scale)",
        ),
    },
)

# Also show the raw rows for the chosen area, so the imported data itself is visible
with st.expander("Show the imported rows for this area"):
    st.dataframe(area_df.drop(columns=["month"]), hide_index=True, width="stretch")
