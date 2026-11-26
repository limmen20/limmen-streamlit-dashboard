"""Explore - exchange rates (EUR and USD in NOK), downloaded directly from Norges Bank's API.

The period and the time resolution are local choices on this page. The rates are also available
as extra inputs (exogenous variables) on the Forecast page.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import fetch_exchange_rates, page_header

page_header("Explore", "Exchange rates", "Euro and US dollar in Norwegian kroner, from Norges Bank.")

c1, c2 = st.columns(2)
years = list(range(2010, pd.Timestamp.today().year + 1))
start_year, end_year = c1.select_slider("Period (years)", options=years, value=(years[-5], years[-1]))
resolution = c2.radio("Time resolution", ["Daily", "Weekly", "Monthly"], horizontal=True,
                      help="Weekly = mean per week ending on Sunday, the same weeks as Magasinstatistikk")

try:
    rates = fetch_exchange_rates(f"{start_year}-01-01", f"{end_year}-12-31")
except Exception as error:
    st.error(f"Could not download the exchange rates from Norges Bank ({type(error).__name__}). Try again later.")
    st.stop()
if rates.empty:
    st.warning("Norges Bank returned no rates for this period.")
    st.stop()

# Norges Bank only publishes on business days; weekly/monthly values are means of those days
if resolution == "Weekly":
    rates = rates.resample("W-SUN").mean()
elif resolution == "Monthly":
    rates = rates.resample("MS").mean()

latest = rates.dropna().iloc[-1]
first = rates.dropna().iloc[0]
m1, m2 = st.columns(2)
m1.metric("EUR (NOK)", f"{latest['EUR']:.3f}", f"{latest['EUR'] - first['EUR']:+.3f} over the period", delta_color="off")
m2.metric("USD (NOK)", f"{latest['USD']:.3f}", f"{latest['USD'] - first['USD']:+.3f} over the period", delta_color="off")

fig = go.Figure()
for cur, color in [("EUR", "#3987e5"), ("USD", "#d95926")]:
    fig.add_trace(go.Scatter(x=rates.index, y=rates[cur], name=cur, line=dict(color=color, width=2)))
fig.update_layout(title=f"Exchange rates, {resolution.lower()} ({start_year}-{end_year})",
                  xaxis_title="Date", yaxis_title="NOK per unit", hovermode="x unified",
                  legend=dict(orientation="h", y=-0.2))
st.plotly_chart(fig, width="stretch")

with st.expander("About the data on this page"):
    st.markdown(
        """
- **Source:** Norges Bank's open data API (SDMX), series `EXR/B.EUR+USD.NOK.SP`, no key needed.
- **Time:** one value per business day, set at 14:15 Norwegian time (ECB concertation). There are no
  values on weekends and holidays; they are left out in the daily view and averaged over in the weekly
  and monthly views.
- **Download:** cached for six hours.
"""
    )
