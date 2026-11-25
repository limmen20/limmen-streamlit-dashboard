"""Predict - sliding window correlation (SWC) between weather and the reservoir filling.

Streamlit version of the book's sliding window correlation (pandas rolling().corr() with a lag):
- Area: global choice. Weather property, reservoir variable, lag and window length: local choices.
- The weather series is shifted by the lag (weather leads), like shifting the index in the book.
- Weekly weather comes from MongoDB (prepared in the part 4 notebook), the filling from the NVE API.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from utils import (WEEKLY_WEATHER, area_label, current_area, fetch_reservoirs, load_weather_weekly, month_options,
                   page_header, region_code, weekly_filling)

page_header("Predict", "Correlation between weather and reservoirs",
            "Sliding window correlation: how strongly a weather property and the reservoir filling move together, "
            "and how this changes over time.")

area_type, number = current_area()
c1, c2, c3, c4 = st.columns(4)
prop = c1.selectbox("Weather property", list(WEEKLY_WEATHER), format_func=WEEKLY_WEATHER.get)
target_name = c2.radio("Reservoir variable", ["Weekly change in filling", "Filling ratio"],
                       help="The weekly change reacts to inflow (rain, snowmelt) more directly than the level")
lag = c3.slider("Lag (weeks the weather leads)", 0, 26, 0)
window = c4.slider("Window length (weeks)", 8, 156, 52, step=4)

try:
    months = month_options()
    filling = weekly_filling(fetch_reservoirs(months[0], months[-1]), area_type, number)
    weather = load_weather_weekly()
except Exception as error:
    st.error(f"Could not load the data ({type(error).__name__}). Check the NVE API and the MongoDB connection.")
    st.stop()

region = region_code(area_type, number)
if weather.empty or region not in set(weather["region"]):
    st.warning(f"There is no weekly weather for {area_label(area_type, number)} in MongoDB yet. "
               "Run the part 4 notebook to fill it, or choose another area.")
    st.stop()
w = weather[weather["region"] == region].set_index("week")[prop].asfreq("W-SUN")
y = filling.diff() if target_name.startswith("Weekly") else filling
y = y[y.index >= w.index[0]].rename(target_name)

# Lag: move the weather `lag` weeks forward in time, so this week's reservoir is compared with the
# weather `lag` weeks earlier (as shifting the index in the book)
x = w.copy()
x.index = x.index + pd.Timedelta(weeks=lag)
data = pd.concat([y, x.rename(WEEKLY_WEATHER[prop])], axis=1).dropna()
if len(data) < window:
    st.warning("Not enough overlapping weeks for this window length.")
    st.stop()

swc = data.iloc[:, 0].rolling(window, center=True).corr(data.iloc[:, 1])
overall = data.iloc[:, 0].corr(data.iloc[:, 1])

# Correlation for every lag 0-26 weeks, to help choosing the lag
lags = range(0, 27)
lag_corr = [y.corr(pd.Series(w.to_numpy(), index=w.index + pd.Timedelta(weeks=k)).reindex(y.index)) for k in lags]
best = int(np.nanargmax(np.abs(lag_corr)))

m1, m2, m3 = st.columns(3)
m1.metric(f"Correlation with lag {lag}", f"{overall:+.2f}")
m2.metric("Strongest lag (0-26 weeks)", f"{best} weeks", f"{lag_corr[best]:+.2f}", delta_color="off")
m3.metric("Weeks used", len(data))

# Position of the highlighted window (like the book's plot_SWC(center=...))
dates = data.index[window // 2: len(data) - window // 2]
center = st.select_slider("Highlighted window (centre)", options=list(dates), value=dates[len(dates) // 2],
                          format_func=lambda d: d.strftime("%Y-%m-%d"))
lo, hi = center - pd.Timedelta(weeks=window // 2), center + pd.Timedelta(weeks=window // 2)

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                    subplot_titles=[f"{target_name} - {area_label(area_type, number)}",
                                    f"{WEEKLY_WEATHER[prop]}, shifted {lag} weeks",
                                    f"Sliding window correlation (window {window} weeks)"])
fig.add_trace(go.Scatter(x=data.index, y=data.iloc[:, 0], name=target_name, line=dict(color="#3987e5", width=1.5)), 1, 1)
fig.add_trace(go.Scatter(x=data.index, y=data.iloc[:, 1], name=WEEKLY_WEATHER[prop].split(" (")[0],
                         line=dict(color="#d95926", width=1.5)), 2, 1)
fig.add_trace(go.Scatter(x=swc.index, y=swc, name="Correlation", line=dict(color="#199e70", width=2)), 3, 1)
fig.add_hline(y=0, line=dict(color="grey", width=1), row=3, col=1)
for row in (1, 2, 3):
    fig.add_vrect(x0=lo, x1=hi, fillcolor="#ffd60a", opacity=0.15, line_width=0, row=row, col=1)
fig.update_yaxes(range=[-1, 1], row=3, col=1)
fig.update_layout(height=720, showlegend=False, hovermode="x unified")
st.plotly_chart(fig, width="stretch")
st.caption(f"Correlation inside the highlighted window: **{swc.get(center, np.nan):+.2f}**. "
           "Positive = the two move up and down together, negative = opposite directions.")

with st.expander("Correlation for each lag"):
    lag_fig = go.Figure(go.Bar(x=list(lags), y=lag_corr, marker_color=["#ffd60a" if k == lag else "#3987e5" for k in lags]))
    lag_fig.update_layout(height=300, xaxis_title="Lag (weeks the weather leads)", yaxis_title="Correlation",
                          yaxis_range=[-1, 1])
    st.plotly_chart(lag_fig, width="stretch")
    st.caption("Correlation does not mean causation, but a strong and stable correlation at some lag is a hint "
               "that the weather property can help forecasting the reservoir.")
