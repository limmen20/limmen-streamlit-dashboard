"""Patterns & anomalies - weather outliers. Tab 1: outliers with SPC (DCT/SATV), tab 2: anomalies with LOF.

- Area: global choice (sidebar/map). Year and weather property: local choices on this page.
- The hourly weather is downloaded directly from open-meteo in the background and cached for a day.
"""

import pandas as pd
import requests
import streamlit as st

from analysis import lof_anomalies, spc_outliers
from utils import (HOURLY_VARIABLES, N_LOCATIONS, area_label, current_area, download_weather, page_header,
                   region_code)

HOURLY_LABELS = {"temperature_2m": "Temperature (°C)", "precipitation": "Precipitation (mm per hour)",
                 "rain": "Rain (mm per hour)", "snowfall": "Snowfall (cm per hour)",
                 "relative_humidity_2m": "Relative humidity (%)", "wind_speed_10m": "Wind speed (km/h)",
                 "wind_gusts_10m": "Wind gusts (km/h)", "cloud_cover": "Cloud cover (%)",
                 "surface_pressure": "Surface pressure (hPa)"}

page_header("Patterns & anomalies", "Weather outliers and anomalies",
            "Hourly ERA5 weather from open-meteo, downloaded for the area chosen in the sidebar or on the map.")

area_type, number = current_area()
region = region_code(area_type, number)
years = list(range(pd.Timestamp.today().year - 1, 1999, -1))   # full years only
year = st.selectbox("Year", years, index=years.index(2024))

try:
    hourly = download_weather(region, f"{year}-01-01", f"{year}-12-31")
except requests.HTTPError as error:
    st.error(f"open-meteo did not answer (HTTP {error.response.status_code}). "
             "The free API has a limit per minute and per day, so try again a bit later.")
    st.stop()
except Exception as error:
    # The locations come from MongoDB, so a connection problem there also ends up here
    st.error(f"Could not get the weather data ({type(error).__name__}). The locations are read from MongoDB, "
             "so check the connection string in the app's secrets and the IP access list in MongoDB Atlas.")
    st.stop()

weather = hourly.groupby("time")[HOURLY_VARIABLES].mean()   # region average per hour
if weather.isna().any().any():
    st.info(f"{int(weather.isna().sum().sum())} missing values were filled from the neighbouring hours.")
    weather = weather.interpolate(limit_direction="both")
st.caption(f"Hourly ERA5 data for **{area_label(area_type, number)}** in {year}, "
           f"average of {N_LOCATIONS} random locations in the area.")

tab_spc, tab_lof = st.tabs(["Outliers (SPC / SATV)", "Anomalies (LOF)"])

with tab_spc:
    c1, c2, c3 = st.columns(3)
    prop = c1.selectbox("Weather property", list(HOURLY_LABELS), format_func=HOURLY_LABELS.get, key="spc_prop")
    cutoff_days = c2.slider("DCT cut-off: remove variations slower than (days)", 2, 120, 30)
    n_std = c3.slider("SPC limits: robust standard deviations", 1.0, 8.0, 3.0, step=0.5)
    fig, summary, outliers = spc_outliers(weather[prop], HOURLY_LABELS[prop], freq_cutoff=1 / cutoff_days, n_std=n_std)
    st.plotly_chart(fig, width="stretch")

    m1, m2, m3 = st.columns(3)
    m1.metric("Outliers", summary["outliers"])
    m2.metric("Share of hours", f"{summary['share']:.1%}")
    m3.metric("Above / below limits", f"{summary['above']} / {summary['below']}")
    st.caption("The DCT high-pass removes the slow seasonal part (the SATV is what is left); the limits are "
               "median ± n robust standard deviations of the SATV, added back to the seasonal part.")
    st.dataframe(outliers.head(50), hide_index=True, column_config={
        "value": st.column_config.NumberColumn(HOURLY_LABELS[prop], format="%.2f"),
        "lower_limit": st.column_config.NumberColumn("Lower limit", format="%.2f"),
        "upper_limit": st.column_config.NumberColumn("Upper limit", format="%.2f")})

with tab_lof:
    c1, c2, c3 = st.columns(3)
    prop = c1.selectbox("Weather property", list(HOURLY_LABELS), format_func=HOURLY_LABELS.get, key="lof_prop")
    proportion = c2.slider("Proportion of outliers (%)", 0.1, 5.0, 1.0, step=0.1)
    n_neighbors = c3.slider("Number of neighbours", 10, 500, 100, step=10,
                            help="With few neighbours, LOF also marks ordinary values lying in small gaps")
    fig, summary, anomalies = lof_anomalies(weather[prop], HOURLY_LABELS[prop], contamination=proportion / 100,
                                            n_neighbors=n_neighbors)
    st.plotly_chart(fig, width="stretch")

    m1, m2, m3 = st.columns(3)
    m1.metric("Anomalies", summary["anomalies"])
    m2.metric("Higher / lower than usual", f"{summary['higher']} / {summary['lower']}")
    m3.metric("Largest deviation from the 30-day mean",
              f"{summary['largest_deviation']:.1f}" if summary["largest_deviation"] is not None else "-")
    st.caption("LOF looks at the deviation from the 30-day mean, so an anomaly is an hour that is unusual "
               "for the time of year.")
    st.dataframe(anomalies.head(50), hide_index=True, column_config={
        "value": st.column_config.NumberColumn(HOURLY_LABELS[prop], format="%.2f"),
        "deviation": st.column_config.NumberColumn("From 30-day mean", format="%+.2f"),
        "lof_score": st.column_config.NumberColumn("LOF score", format="%.2f")})

with st.expander("About the weather data"):
    st.markdown(
        f"""
- **Source:** open-meteo's historical weather API with the ERA5 reanalysis model, hourly values in UTC.
- **Locations:** 1000 random locations per area were sampled inside NVE's map layers in the part 3 notebook
  and stored in MongoDB. This page downloads {N_LOCATIONS} of them (shown on the map) and uses the average.
- **Download:** happens in the background when you change area or year, and is cached for a day.
"""
    )
    st.map(hourly[["latitude", "longitude"]].drop_duplicates(), size=3000)
