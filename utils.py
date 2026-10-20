"""Helper functions shared by the pages.

Reservoir data comes from the NVE API (no more CSV file), and the cross-border
flows come from MongoDB, where the notebook saved them.
"""

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


def reservoir_controls() -> tuple[str, str, str]:
    """Sidebar controls used on both the Data table page and the Plot page."""
    months = month_options()
    # Remember the last choice, so it stays the same when you switch page
    saved_type = st.session_state.get("saved_area_type", "NO")
    saved_interval = st.session_state.get("saved_interval", (months[-24], months[-1]))

    st.sidebar.header("Reservoir data")
    area_type = st.sidebar.radio("Area type", list(AREA_TYPES), index=list(AREA_TYPES).index(saved_type),
                                 format_func=AREA_TYPES.get)
    # value is a tuple -> range slider (from, to). Default is the last two years
    start, end = st.sidebar.select_slider("Download interval (months)", options=months, value=saved_interval)

    st.session_state["saved_area_type"] = area_type
    st.session_state["saved_interval"] = (start, end)
    return area_type, start, end


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
