"""Reservoirs - trends and seasons. Tab 1: STL decomposition, tab 2: spectrogram.

The area comes from the sidebar (shared with the other pages). STL and the spectrogram need many
years of data, so this page uses the whole history since 1995 instead of the download interval slider.
"""

import streamlit as st

from analysis import spectrogram_figure, stl_figure, weekly_series
from utils import area_controls, area_label, fetch_reservoirs, month_options

st.title("Trends and seasons")

area_type, number = area_controls()          # sidebar: area type + one area
months = month_options()
df = fetch_reservoirs(months[0], months[-1])  # whole history (cached)
series = weekly_series(df, area_type, number)
st.caption(f"Weekly filling ratio for **{area_label(area_type, number)}**, "
           f"{series.index[0]:%Y} to {series.index[-1]:%Y}. The whole history is used, since both methods "
           "need many years of data.")

tab_stl, tab_spec = st.tabs(["STL decomposition", "Spectrogram"])

with tab_stl:
    c1, c2, c3 = st.columns(3)
    # STL needs odd smoother lengths, so the sliders go in steps of 2
    seasonal = c1.slider("Seasonal smoother (weeks)", 7, 51, 13, step=2)
    trend = c2.slider("Trend smoother (weeks)", 53, 209, 89, step=2, help="Must be longer than the period (52)")
    robust = c3.toggle("Robust", value=True, help="Down-weights unusual weeks")
    st.plotly_chart(stl_figure(series, seasonal=seasonal, trend=trend, robust=robust), width="stretch")
    st.caption("Trend = slow changes over the years, Seasonal = the yearly pattern, Residual = what is left.")

with tab_spec:
    c1, c2, c3 = st.columns(3)
    window = c1.slider("Window length (weeks)", 26, 260, 104, step=2)
    overlap_pct = c2.slider("Window overlap (%)", 0, 95, 75, step=5)
    max_freq = c3.slider("Highest frequency shown (cycles per year)", 2, 26, 6)
    overlap = int(window * overlap_pct / 100)   # spectrogram wants the overlap in weeks
    st.plotly_chart(spectrogram_figure(series, window_length=window, overlap=overlap, max_freq=max_freq),
                    width="stretch")
    st.caption("1 cycle per year is the yearly filling and emptying of the reservoirs. Longer windows give "
               "sharper frequencies but less detail in time.")
