"""Page 3: interactive plot of the imported data.

- st.selectbox chooses a single column or all columns together.
- st.select_slider chooses a range of months (default: the first month).
The plot is made with Plotly, which gives hover tooltips and zoom for free.
"""

import plotly.express as px
import streamlit as st

from utils import COLUMN_COLORS, RATIO_COLUMNS, VALUE_COLUMNS, area_selector, load_data

st.set_page_config(page_title="Plot", layout="wide")
st.title("Plot of reservoir data")

df = load_data()  # cached data from utils.py
area = area_selector(df)
area_df = df[df["area"] == area]

ALL = "All columns"

# Drop-down: any single column, or all columns together.
# format_func shows the readable label while the value stays the column name.
choice = st.selectbox(
    "Column",
    [ALL] + list(VALUE_COLUMNS.keys()),
    format_func=lambda c: c if c == ALL else VALUE_COLUMNS[c],
)

# Range slider over the months in the data. Giving a tuple as value makes it a
# range slider; (first, first) means only the first month is selected by default.
months = sorted(area_df["month"].unique())
start, end = st.select_slider(
    "Months", options=months, value=(months[0], months[0])
)

# Keep only the rows inside the chosen month range
mask = (area_df["month"] >= start) & (area_df["month"] <= end)
plot_df = area_df[mask]
period = start if start == end else f"{start} to {end}"

if choice == ALL:
    # The columns have very different scales (fractions vs. TWh), so each column
    # is divided by its largest absolute value for this area. All lines then share
    # one axis between -1 and 1 and can be compared by shape.
    scaled = plot_df[["date"]].copy()
    for col, label in VALUE_COLUMNS.items():
        scaled[label] = plot_df[col] / area_df[col].abs().max()
    long_df = scaled.melt(id_vars="date", var_name="Column", value_name="Scaled value")

    fig = px.line(
        long_df,
        x="date",
        y="Scaled value",
        color="Column",
        markers=True,
        color_discrete_map={VALUE_COLUMNS[c]: COLUMN_COLORS[c] for c in VALUE_COLUMNS},
        title=f"All columns, scaled to their maximum - {area}, {period}",
        labels={"date": "Date", "Scaled value": "Value / max |value|"},
    )
    # Stored energy = filling ratio x constant capacity, so after scaling the two
    # lines are identical. Dashing one of them keeps both visible.
    fig.update_traces(line_dash="dash", selector={"name": VALUE_COLUMNS["filling_TWh"]})
    st.caption(
        "Each column is divided by its maximum absolute value, so columns with "
        "different units can be shown on the same axis. Stored energy (dashed) lies "
        "on top of the filling ratio."
    )
else:
    fig = px.line(
        plot_df,
        x="date",
        y=choice,
        markers=True,
        color_discrete_sequence=[COLUMN_COLORS[choice]],
        title=f"{VALUE_COLUMNS[choice]} - {area}, {period}",
        labels={"date": "Date", choice: VALUE_COLUMNS[choice]},
    )
    if choice in RATIO_COLUMNS:
        fig.update_yaxes(tickformat=".0%")  # show fractions as percentages

# Common formatting: one tooltip for all lines at a date, 2 px lines
fig.update_layout(hovermode="x unified", legend_title_text="")
fig.update_traces(line_width=2)
st.plotly_chart(fig, width="stretch")

st.write(f"{len(plot_df)} weekly observations in the selected period.")
