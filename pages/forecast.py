"""Predict - forecast of the weekly reservoir filling with River's SNARIMAX (dynamic forecasting).

- Area: global choice (sidebar/map). Training data ends at the month chosen on the Map page (synced
  both ways through st.session_state["map_month"]).
- All model parameters, the extra inputs (exogenous variables), the history length and the horizon are
  local choices. The defaults are the best settings from the tests in the part 4 notebook.
- The forecast is animated week by week with Plotly. A 90% interval comes from two extra models
  trained with quantile loss (bonus task).
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from forecasting import CURRENCY_INPUTS, DEFAULTS, WEATHER_INPUTS, forecast_filling
from utils import (WEEKLY_WEATHER, area_label, current_area, current_month, fetch_exchange_rates, fetch_reservoirs,
                   load_weather_weekly, month_options, page_header, region_code, weekly_filling)

page_header("Predict", "Forecast of the reservoir filling",
            "SNARIMAX (River) on weekly data. Choose the training period, the horizon, the model and the extra inputs.")

area_type, number = current_area()
INPUT_LABELS = {"season": "Season (time of year)", **{k: v.split(" (")[0] for k, v in WEEKLY_WEATHER.items()},
                "EUR": "EUR exchange rate", "USD": "USD exchange rate"}

# --- Controls --------------------------------------------------------------------------------------
months = [m for m in month_options() if m >= "2000-01"][:-1]
saved = current_month()
c1, c2, c3 = st.columns([1.6, 1, 1])
train_month = c1.select_slider("Training data ends (synced with the map month)", options=months,
                               value=saved if saved in months else months[-1])
st.session_state["map_month"] = train_month   # keep the map in sync
history_years = c2.slider("Years of history", 2, 25, DEFAULTS["history_years"])
horizon = c3.slider("Forecast horizon (weeks)", 4, 104, DEFAULTS["horizon"], step=2)

with st.expander("Model parameters (SNARIMAX)", expanded=False):
    cols = st.columns(7)
    p = cols[0].number_input("p (AR)", 0, 6, DEFAULTS["p"])
    d = cols[1].number_input("d (diff.)", 0, 2, DEFAULTS["d"])
    q = cols[2].number_input("q (MA)", 0, 6, DEFAULTS["q"])
    sp = cols[3].number_input("sp (seasonal AR)", 0, 3, DEFAULTS["sp"])
    sd = cols[4].number_input("sd (seasonal diff.)", 0, 1, DEFAULTS["sd"])
    sq = cols[5].number_input("sq (seasonal MA)", 0, 3, DEFAULTS["sq"])
    learning_rate = cols[6].selectbox("Learning rate", [0.001, 0.005, 0.01, 0.02, 0.05],
                                      index=[0.001, 0.005, 0.01, 0.02, 0.05].index(DEFAULTS["learning_rate"]))
    st.caption("Season length m = 52 weeks. p/d/q are the regular and sp/sd/sq the seasonal orders.")

c1, c2 = st.columns([3, 1])
inputs = c1.multiselect("Extra inputs (exogenous variables)", list(INPUT_LABELS), default=DEFAULTS["inputs"],
                        format_func=INPUT_LABELS.get)
interval = c2.toggle("90% interval", value=False,
                     help="Two extra models with quantile loss (5% and 95%). In the notebook tests they covered "
                          "about 92% of the actual values, but the band is wide because the errors add up week by week.")

# --- Data and forecast -----------------------------------------------------------------------------
train_end = (pd.Timestamp(train_month) + pd.offsets.MonthEnd(0)).normalize()
external = [i for i in inputs if i != "season"]
if external and train_end - pd.DateOffset(years=history_years) < pd.Timestamp("2010-01-01"):
    history_years = max(2, int((train_end - pd.Timestamp("2010-01-01")).days // 365))
    st.info(f"Weather and exchange rates start in 2010, so the history is shortened to {history_years} years.")


def load_inputs(area_type, number, inputs):
    """Weekly filling (target) and the chosen extra inputs for the area. The downloads are cached in utils."""
    months_all = month_options()
    target = weekly_filling(fetch_reservoirs(months_all[0], months_all[-1]), area_type, number)
    exog = pd.DataFrame(index=target.index)
    weather_inputs = [i for i in inputs if i in WEATHER_INPUTS]
    if weather_inputs:
        weather = load_weather_weekly()
        w = weather[weather["region"] == region_code(area_type, number)].set_index("week")
        if w.empty:
            raise ValueError(f"No weekly weather in MongoDB for {region_code(area_type, number)} yet")
        exog = exog.join(w[weather_inputs])
    currency_inputs = [i for i in inputs if i in CURRENCY_INPUTS]
    if currency_inputs:
        rates = fetch_exchange_rates("2010-01-01").resample("W-SUN").mean()   # same weeks as the reservoirs
        exog = exog.join(rates[currency_inputs])
    return target, (exog if len(exog.columns) else None)


@st.cache_resource
def finished_forecasts() -> dict:
    """Forecasts that are already computed, shared between reruns and users (the training is the slow part).
    Not st.cache_data, because the progress bar is updated while the model trains."""
    return {}


key = (area_type, number, train_end, history_years, horizon, p, d, q, sp, sd, sq, learning_rate, tuple(inputs), interval)
store = finished_forecasts()
bar = st.empty()                             # place for the progress bar
try:
    target, exog = load_inputs(area_type, number, inputs)
    if key not in store:
        store[key] = forecast_filling(target, exog, train_end=train_end, history_years=history_years, horizon=horizon,
                                      p=p, d=d, q=q, sp=sp, sd=sd, sq=sq, use_season="season" in inputs,
                                      learning_rate=learning_rate, interval=interval,
                                      progress=lambda f: bar.progress(f, text=f"Training the model ... {f:.0%}"))
        if len(store) > 100:                 # keep the memory use small: forget the oldest forecast
            store.pop(next(iter(store)))
except Exception as error:
    bar.empty()
    st.error(f"The forecast could not be made: {error}")
    st.stop()
bar.empty()
result = store[key]

# --- Results ---------------------------------------------------------------------------------------
known = result["actual"].notna()
m1, m2, m3 = st.columns(3)
m1.metric(f"Forecast in {horizon} weeks", f"{result['forecast'].iloc[-1]:.1%}",
          f"{result['forecast'].iloc[-1] - target[target.index <= train_end].iloc[-1]:+.1%} from last known week")
m2.metric("Mean absolute error", f"{(result['forecast'] - result['actual'])[known].abs().mean():.3f}" if known.any()
          else "no actuals yet", help="Compared with the actual filling, when it is known")
m3.metric("Weeks with actual values", f"{int(known.sum())} of {horizon}")

history = target[(target.index > train_end - pd.DateOffset(years=2)) & (target.index <= train_end)]
fc = result["forecast"]
fig = go.Figure(
    data=[
        go.Scatter(x=history.index, y=history, name="History", line=dict(color="#3987e5", width=2)),
        go.Scatter(x=result.index[known], y=result["actual"][known], name="Actual", line=dict(color="#9aa4ad", width=2, dash="dot")),
        # The page opens with the whole forecast; Play replays it from week 1
        go.Scatter(x=fc.index, y=result["upper"] if interval else [], mode="lines", line=dict(width=0),
                   showlegend=False, hoverinfo="skip"),
        go.Scatter(x=fc.index, y=result["lower"] if interval else [], mode="lines", name="90% interval",
                   fill="tonexty", fillcolor="rgba(25,158,112,0.25)", line=dict(width=0)),
        go.Scatter(x=fc.index, y=fc, mode="lines", name="Forecast", line=dict(color="#199e70", width=3)),
    ],
    # One frame per forecast week: the forecast (and the interval) grows one week at a time
    frames=[go.Frame(name=str(k), traces=[2, 3, 4], data=[
        go.Scatter(x=fc.index[:k], y=result["upper"][:k] if interval else []),
        go.Scatter(x=fc.index[:k], y=result["lower"][:k] if interval else []),
        go.Scatter(x=fc.index[:k], y=fc[:k])]) for k in range(1, horizon + 1)],
)
values = pd.concat([history, fc, result["actual"].dropna()] + ([result["upper"], result["lower"]] if interval else []))
fig.update_layout(
    title=f"Forecast of the filling ratio - {area_label(area_type, number)} (training ends {train_end:%Y-%m-%d})",
    xaxis=dict(title="Week", range=[history.index[0], fc.index[-1]]),
    yaxis=dict(title="Filling ratio", tickformat=".0%", range=[max(0, values.min() - 0.05), min(1, values.max() + 0.05)]),
    height=520, hovermode="x unified", legend=dict(orientation="h", y=-0.25),
    updatemenus=[dict(type="buttons", x=0, y=1.12, xanchor="left", direction="right", buttons=[
        dict(label="▶ Play", method="animate", args=[[str(k) for k in range(1, horizon + 1)],
                                                      {"frame": {"duration": 120, "redraw": True}, "mode": "immediate"}]),
        dict(label="⏸ Pause", method="animate", args=[[None], {"frame": {"duration": 0}, "mode": "immediate"}])])],
    sliders=[dict(active=horizon - 1, currentvalue={"prefix": "Weeks ahead: "}, pad={"t": 40}, steps=[
        dict(label=str(k), method="animate", args=[[str(k)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}])
        for k in range(1, horizon + 1)])],
)
st.plotly_chart(fig, width="stretch")
st.caption("Press ▶ Play to see the forecast grow one week at a time. Each week builds on the forecasts for the "
           "weeks before (dynamic forecasting). Future weather is unknown, so the model uses the average for the "
           "same week in earlier years; exchange rates keep their last known value.")

with st.expander("Forecast values"):
    st.dataframe(result.style.format("{:.1%}", na_rep="-"), width="stretch")
