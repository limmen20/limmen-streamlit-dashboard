"""Helper functions shared by the pages.

Reservoir data comes from the NVE API (no more CSV file), the cross-border flows and
the weather locations come from MongoDB (saved there by the notebooks), and the weather
itself is downloaded from open-meteo.
"""

import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import streamlit as st
from pymongo import MongoClient

NVE_API = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk"

# Norwegian column names -> English (same as in the notebook)
COLUMN_NAMES = {
    "dato_Id": "date",
    "omrType": "area_type",
    "omrnr": "area_number",
    "iso_aar": "iso_year",
    "iso_uke": "iso_week",
    "fyllingsgrad": "filling_ratio",
    "kapasitet_TWh": "capacity_TWh",
    "fylling_TWh": "filling_TWh",
    "neste_Publiseringsdato": "next_publication_date",
    "fyllingsgrad_forrige_uke": "filling_ratio_prev_week",
    "endring_fyllingsgrad": "filling_ratio_change",
}

# The columns that are actual measurements (the rest are dates and ids)
VALUE_COLUMNS = {
    "filling_ratio": "Filling ratio",
    "filling_ratio_prev_week": "Filling ratio previous week",
    "filling_ratio_change": "Change in filling ratio since previous week",
    "filling_TWh": "Stored energy (TWh)",
    "capacity_TWh": "Reservoir capacity (TWh)",
}
RATIO_COLUMNS = ["filling_ratio", "filling_ratio_prev_week", "filling_ratio_change"]  # 0-1, shown as %

# Same colour for a column on every plot
COLUMN_COLORS = {
    "filling_ratio": "#2a78d6",
    "filling_ratio_prev_week": "#eb6834",
    "filling_ratio_change": "#1baf7a",
    "filling_TWh": "#eda100",
    "capacity_TWh": "#e87ba4",
}

AREA_TYPES = {
    "NO": "NO - whole country",
    "EL": "EL - price areas",
    "VASS": "VASS - watercourse regions",
}

# Colours for the area numbers, the connections and the two directions
AREA_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
CONNECTION_COLORS = {
    "Sweden": "#2a78d6", "Denmark": "#eb6834", "Finland": "#1baf7a",
    "Germany": "#eda100", "Netherlands": "#e87ba4", "Great Britain": "#008300",
}
IMPORT, EXPORT = "Import to Norway", "Export from Norway"
DIRECTION_COLORS = {IMPORT: "#2a78d6", EXPORT: "#eb6834"}


def area_label(area_type: str, area_number: int) -> str:
    """NO = whole country, EL = price area (NO1-NO5), VASS = watercourse region."""
    if area_type == "NO":
        return "Norway (total)"
    if area_type == "EL":
        return f"NO{area_number}"
    return f"Watercourse region {area_number}"


def month_options() -> list[str]:
    """Every month from January 1995 (start of the data) until now, as "YYYY-MM"."""
    return pd.period_range("1995-01", pd.Timestamp.today(), freq="M").astype(str).tolist()


AREA_NUMBERS = {"NO": [0], "EL": [1, 2, 3, 4, 5], "VASS": [1, 2, 3]}

# --- Global selections (session state) -------------------------------------------------------
# The area is chosen once (in the sidebar or by clicking on the map) and used by all analysis pages.


def _reset_area_number():
    """When the area type changes, start with its first area."""
    st.session_state["area_number"] = AREA_NUMBERS[st.session_state["area_type"]][0]


def global_area_controls():
    """Sidebar controls for the area, drawn by Home.py for every page that uses an area."""
    # A click on the map stores a 'pending' area; it has to be applied before the widgets are drawn
    pending = st.session_state.pop("pending_area", None)
    if pending:
        st.session_state["area_type"], st.session_state["area_number"] = pending
    st.session_state.setdefault("area_type", "NO")
    if st.session_state.get("area_number") not in AREA_NUMBERS[st.session_state["area_type"]]:
        _reset_area_number()

    st.sidebar.header("Area")
    st.sidebar.radio("Area type", list(AREA_TYPES), format_func=AREA_TYPES.get, key="area_type",
                     on_change=_reset_area_number)
    st.sidebar.selectbox("Area", AREA_NUMBERS[st.session_state["area_type"]], key="area_number",
                         format_func=lambda n: area_label(st.session_state["area_type"], n))
    st.sidebar.caption("Tip: click an area on the Map page to select it.")


def current_area() -> tuple[str, int]:
    """The area chosen in the sidebar or on the map (defaults to the whole country)."""
    return st.session_state.get("area_type", "NO"), st.session_state.get("area_number", 0)


def current_month() -> str:
    """The month chosen on the map ("YYYY-MM"). The forecast page uses it as the end of the training data."""
    return st.session_state.get("map_month", (pd.Timestamp.today() - pd.DateOffset(months=1)).strftime("%Y-%m"))


# --- Page groups and headers -------------------------------------------------------------------
GROUPS = {
    "Explore": {"color": "blue", "hex": "#3987e5", "icon": ":material/explore:"},
    "Patterns & anomalies": {"color": "orange", "hex": "#d95926", "icon": ":material/query_stats:"},
    "Predict": {"color": "green", "hex": "#199e70", "icon": ":material/trending_up:"},
}


def page_header(group: str, title: str, intro: str | None = None):
    """Coloured group badge + stripe and title, so it is easy to see which group is active."""
    g = GROUPS[group]
    st.markdown(f'<div style="height:4px;background:{g["hex"]};border-radius:2px;margin-bottom:0.6rem"></div>',
                unsafe_allow_html=True)
    st.markdown(f":{g['color']}-badge[{g['icon']} {group}]")
    st.title(title)
    if intro:
        st.caption(intro)


def region_code(area_type: str, area_number: int) -> str:
    """Region name used for the weather locations in MongoDB: NO, NO1-NO5 or VASS1-VASS3."""
    if area_type == "NO":
        return "NO"
    return f"NO{area_number}" if area_type == "EL" else f"VASS{area_number}"


@st.cache_data(ttl=3600, show_spinner="Downloading reservoir data from NVE ...")
def fetch_reservoirs(start_month: str, end_month: str) -> pd.DataFrame:
    """Download the reservoir data for the chosen months.

    The API has no date filter, so everything is downloaded and only the chosen
    months are kept. Cached for an hour, so moving the slider back is quick.
    """
    response = requests.get(f"{NVE_API}/HentOffentligData", timeout=60)
    response.raise_for_status()
    df = pd.DataFrame(response.json()).rename(columns=COLUMN_NAMES)

    # Dates come as text and the rows are not sorted (same as the CSV in part 1)
    df["date"] = pd.to_datetime(df["date"])
    month = df["date"].dt.strftime("%Y-%m")
    df = df[(month >= start_month) & (month <= end_month)].copy()
    df["area"] = [area_label(t, n) for t, n in zip(df["area_type"], df["area_number"])]
    return df.sort_values(["area_type", "area_number", "date"]).reset_index(drop=True)


@st.cache_data(ttl=3600)
def fetch_latest_week() -> pd.DataFrame:
    """Only the newest week - a small download for the home page."""
    response = requests.get(f"{NVE_API}/HentOffentligDataSisteUke", timeout=60)
    response.raise_for_status()
    return pd.DataFrame(response.json()).rename(columns=COLUMN_NAMES)


@st.cache_resource  # one connection, reused across reruns and users
def mongo_client() -> MongoClient:
    # The connection string is in the secrets (secrets.toml / Streamlit Cloud), not on GitHub
    return MongoClient(st.secrets["mongo"]["uri"], serverSelectionTimeoutMS=10000)


@st.cache_data(ttl=600, show_spinner="Reading cross-border flows from MongoDB ...")
def load_flows() -> pd.DataFrame:
    """Daily flows (GWh) per connection and direction, saved there by the notebook."""
    collection = mongo_client()["ind320"]["cross_border_flows_daily"]
    df = pd.DataFrame(list(collection.find({}, {"_id": 0})))   # _id is MongoDB's own id, not needed
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


# --- Weather (open-meteo, ERA5) ---------------------------------------------------------------
ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARIABLES = ["temperature_2m", "precipitation", "rain", "snowfall", "relative_humidity_2m",
                    "wind_speed_10m", "wind_gusts_10m", "cloud_cover", "surface_pressure"]
N_LOCATIONS = 5   # random locations per download (the free API limits how much we can download)


@st.cache_data(ttl=24 * 3600)
def load_locations() -> dict[str, list]:
    """The 1000 random [lon, lat] locations per region, sampled in the part 3 notebook."""
    docs = mongo_client()["ind320"]["region_locations"].find({}, {"_id": 0})
    return {doc["region"]: doc["locations"] for doc in docs}


@st.cache_data(ttl=24 * 3600, show_spinner="Downloading weather data from open-meteo ...")
def download_weather(region: str, start: str, end: str, n_locations: int = N_LOCATIONS, seed: int = 1):
    """Hourly ERA5 weather for random locations in a region (same function as in the notebook).

    The download happens in the background when a page needs it, and is cached for a day,
    so there is no separate download page.
    """
    pairs = load_locations()[region]
    rng = np.random.default_rng(seed)
    chosen = [pairs[i] for i in rng.choice(len(pairs), size=n_locations, replace=False)]
    params = {
        "latitude": ",".join(str(lat) for lon, lat in chosen),
        "longitude": ",".join(str(lon) for lon, lat in chosen),
        "start_date": start, "end_date": end,
        "hourly": ",".join(HOURLY_VARIABLES), "models": "era5", "timezone": "GMT",
    }
    response = requests.get(ARCHIVE_API, params=params, timeout=120)
    response.raise_for_status()
    results = response.json()
    if isinstance(results, dict):   # one location -> a dict, several -> a list
        results = [results]

    frames = []
    for i, (result, (lon, lat)) in enumerate(zip(results, chosen)):
        frame = pd.DataFrame(result["hourly"])
        frame["location"], frame["longitude"], frame["latitude"] = i, lon, lat
        frames.append(frame)
    weather = pd.concat(frames, ignore_index=True)
    weather["time"] = pd.to_datetime(weather["time"])
    return weather


WEEKLY_WEATHER = {"temperature": "Temperature (°C, weekly mean)", "precipitation": "Precipitation (mm per week)",
                  "rain": "Rain (mm per week)", "snowfall": "Snowfall (cm per week)",
                  "wind_speed": "Wind speed (km/h, mean of daily max)"}


@st.cache_data(ttl=24 * 3600, show_spinner="Reading weekly weather from MongoDB ...")
def load_weather_weekly() -> pd.DataFrame:
    """Weekly weather per region since 2010, prepared in the part 4 notebook (weeks end on Sunday,
    like Magasinstatistikk). Long histories like this are too slow to download live."""
    docs = mongo_client()["ind320"]["weather_weekly"].find({}, {"_id": 0})
    df = pd.DataFrame(list(docs))
    if not df.empty:
        df["week"] = pd.to_datetime(df["week"])
    return df


# --- Norges Bank exchange rates ------------------------------------------------------------------
NB_API = "https://data.norges-bank.no/api/data/EXR/B.{currencies}.NOK.SP"


@st.cache_data(ttl=6 * 3600, show_spinner="Downloading exchange rates from Norges Bank ...")
def fetch_exchange_rates(start: str = "2010-01-01", end: str | None = None, currencies=("EUR", "USD")) -> pd.DataFrame:
    """Daily exchange rates (NOK per unit) from Norges Bank, one column per currency.

    Business days only (no weekends/holidays), dates in Norwegian time (fixed at 14:15 CET).
    """
    params = {"format": "csv", "startPeriod": start, "locale": "en"}
    if end:
        params["endPeriod"] = end
    response = requests.get(NB_API.format(currencies="+".join(currencies)), params=params, timeout=60)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text), sep=";")
    rates = df.pivot(index="TIME_PERIOD", columns="BASE_CUR", values="OBS_VALUE")
    rates.index = pd.to_datetime(rates.index)
    return rates.sort_index()


# --- Map shapes ----------------------------------------------------------------------------------
GEOJSON_FILES = {"NO": "country.geojson", "EL": "price_areas.geojson", "VASS": "water_areas.geojson"}


@st.cache_data
def load_geojson(area_type: str) -> dict:
    """Area outlines as GeoJSON (converted from the NVE shapefiles in the part 4 notebook)."""
    with open(Path(__file__).parent / "data" / "geojson" / GEOJSON_FILES[area_type], encoding="utf-8") as f:
        return json.load(f)


def weekly_filling(df: pd.DataFrame, area_type: str, area_number: int) -> pd.Series:
    """Filling ratio for one area as a regular weekly series (the dates are Sundays)."""
    area = df[(df["area_type"] == area_type) & (df["area_number"] == area_number)]
    return area.set_index("date")["filling_ratio"].asfreq("W-SUN").interpolate()
