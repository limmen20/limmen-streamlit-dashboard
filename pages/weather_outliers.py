"""Weather - outliers and anomalies. Tab 1: precipitation outliers (SPC), tab 2: temperature anomalies (LOF).

The region follows the area chosen in the sidebar (shared with the reservoir pages), and the year is
picked on this page. The weather is downloaded from open-meteo in the background and cached, so no
separate download page is needed.
"""

import pandas as pd
import requests
import streamlit as st

from analysis import lof_temperature, spc_precipitation
from utils import HOURLY_VARIABLES, N_LOCATIONS, area_controls, area_label, download_weather, region_code

st.title("Weather outliers and anomalies")

area_type, number = area_controls()          # sidebar: area type + one area
region = region_code(area_type, number)
years = list(range(pd.Timestamp.today().year - 1, 1999, -1))   # full years only
year = st.selectbox("Year", years, index=years.index(2024))

try:
    hourly = download_weather(region, f"{year}-01-01", f"{year}-12-31")
except requests.HTTPError as error:
    st.error(f"open-meteo did not answer (HTTP {error.response.status_code}). "
             "The free API has a daily limit, so try again later.")
    st.stop()
except Exception as error:
    # The locations come from MongoDB, so a connection problem there also ends up here
    st.error(f"Could not get the weather data ({type(error).__name__}). The locations are read from MongoDB, "
             "so check the connection string in the app's secrets and the IP access list in MongoDB Atlas.")
    st.stop()

weather = hourly.groupby("time")[HOURLY_VARIABLES].mean()   # region average per hour
st.caption(f"Hourly ERA5 data for **{area_label(area_type, number)}** in {year}, "
           f"average of {N_LOCATIONS} random locations in the region.")

tab_spc, tab_lof = st.tabs(["Outliers: precipitation (SPC)", "Anomalies: temperature (LOF)"])

with tab_spc:
    c1, c2 = st.columns(2)
    cutoff_days = c1.slider("DCT cut-off: remove variations slower than (days)", 2, 120, 30)
    n_std = c2.slider("SPC limits: robust standard deviations", 1.0, 8.0, 3.0, step=0.5)
    fig, summary, outliers = spc_precipitation(weather["precipitation"], freq_cutoff=1 / cutoff_days, n_std=n_std)
    st.plotly_chart(fig, width="stretch")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Outliers", summary["outliers"])
    m2.metric("Share of hours", f"{summary['share']:.1%}")
    m3.metric("Above / below limits", f"{summary['above']} / {summary['below']}")
    m4.metric("Largest outlier", f"{summary['largest_mm']:.2f} mm/h" if summary["largest_mm"] else "-")
    st.caption("Rain comes in short heavy bursts, so nearly all outliers are above the upper limit.")
    st.dataframe(outliers.sort_values("precipitation_mm", ascending=False).head(20), hide_index=True,
                 column_config={"precipitation_mm": st.column_config.NumberColumn("Precipitation (mm/h)", format="%.2f"),
                                "upper_limit_mm": st.column_config.NumberColumn("Upper limit (mm/h)", format="%.2f")})

with tab_lof:
    c1, c2 = st.columns(2)
    proportion = c1.slider("Proportion of outliers (%)", 0.1, 5.0, 1.0, step=0.1)
    n_neighbors = c2.slider("Number of neighbours", 10, 500, 100, step=10,
                            help="With few neighbours, LOF also marks ordinary values lying in small gaps")
    fig, summary, anomalies = lof_temperature(weather["temperature_2m"], contamination=proportion / 100,
                                              n_neighbors=n_neighbors)
    st.plotly_chart(fig, width="stretch")

    m1, m2, m3 = st.columns(3)
    m1.metric("Anomalies", summary["anomalies"])
    m2.metric("Warmer / colder than usual", f"{summary['warmer']} / {summary['colder']}")
    m3.metric("Largest deviation", f"{summary['largest_deviation_C']:.1f} °C" if summary["largest_deviation_C"] else "-")
    st.caption("LOF looks at the deviation from the 30-day mean, so an anomaly is an hour that is unusually "
               "warm or cold for the time of year.")
    st.dataframe(anomalies.head(20), hide_index=True,
                 column_config={"temperature_C": st.column_config.NumberColumn("Temperature (°C)", format="%.1f"),
                                "deviation_C": st.column_config.NumberColumn("From 30-day mean (°C)", format="%+.1f"),
                                "lof_score": st.column_config.NumberColumn("LOF score", format="%.2f")})

with st.expander("About the weather data"):
    st.markdown(
        f"""
- **Source:** open-meteo's historical weather API with the ERA5 reanalysis model, hourly values in UTC.
- **Locations:** 1000 random locations per region were sampled inside NVE's map layers (price areas and
  NVE regions) in the part 3 notebook and stored in MongoDB. This page downloads {N_LOCATIONS} of them
  (shown on the map) and uses the average.
- **Download:** happens in the background when you change area or year, and is cached for a day.
"""
    )
    st.map(hourly[["latitude", "longitude"]].drop_duplicates(), size=3000)
