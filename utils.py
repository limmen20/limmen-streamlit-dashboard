"""Shared helpers for the Streamlit app.

- Reservoir data are downloaded from NVE's Magasinstatistikk API (replaces the CSV file from part 1).
- Cross-border flows are read from MongoDB, where the Jupyter Notebook stored them after
  processing them with Spark and Cassandra.
Downloads are cached, so the APIs/database are not called again on every widget change.
"""

import pandas as pd
import requests
import streamlit as st
from pymongo import MongoClient

NVE_API = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk"

# Norwegian -> English column names (same mapping as in the Jupyter Notebook)
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

# The measurement columns (the ones that make sense to plot) and readable labels
VALUE_COLUMNS = {
    "filling_ratio": "Filling ratio",
    "filling_ratio_prev_week": "Filling ratio previous week",
    "filling_ratio_change": "Change in filling ratio since previous week",
    "filling_TWh": "Stored energy (TWh)",
    "capacity_TWh": "Reservoir capacity (TWh)",
}
RATIO_COLUMNS = ["filling_ratio", "filling_ratio_prev_week", "filling_ratio_change"]

# One fixed colour per column, so a column keeps its colour on every plot
COLUMN_COLORS = {
    "filling_ratio": "#2a78d6",
    "filling_ratio_prev_week": "#eb6834",
    "filling_ratio_change": "#1baf7a",
    "filling_TWh": "#eda100",
    "capacity_TWh": "#e87ba4",
}

# Area types in the NVE data
AREA_TYPES = {
    "NO": "NO - whole country",
    "EL": "EL - price areas",
    "VASS": "VASS - watercourse regions",
}

# Fixed colours: one per area number, one per connection, one per direction
AREA_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
CONNECTION_COLORS = {
    "Sweden": "#2a78d6", "Denmark": "#eb6834", "Finland": "#1baf7a",
    "Germany": "#eda100", "Netherlands": "#e87ba4", "Great Britain": "#008300",
}
IMPORT, EXPORT = "Import to Norway", "Export from Norway"
DIRECTION_COLORS = {IMPORT: "#2a78d6", EXPORT: "#eb6834"}


def area_label(area_type: str, area_number: int) -> str:
    """Readable area name: NO = whole country, EL = price area, VASS = watercourse region."""
    if area_type == "NO":
        return "Norway (total)"
    if area_type == "EL":
        return f"NO{area_number}"
    return f"Watercourse region {area_number}"


def month_options() -> list[str]:
    """All months from the start of the statistics (January 1995) to the current month."""
    return pd.period_range("1995-01", pd.Timestamp.today(), freq="M").astype(str).tolist()


def reservoir_controls() -> tuple[str, str, str]:
    """Sidebar controls shared by the Data table and Plot pages.

    - st.radio chooses the area type (NO, EL or VASS).
    - st.select_slider chooses the months to download (default: the last two years).
    The choices are kept when the user switches between the two pages.
    """
    months = month_options()
    # Last choices (stored in session state, which is kept when the user changes page)
    saved_type = st.session_state.get("saved_area_type", "NO")
    saved_interval = st.session_state.get("saved_interval", (months[-24], months[-1]))

    st.sidebar.header("Reservoir data")
    area_type = st.sidebar.radio("Area type", list(AREA_TYPES), index=list(AREA_TYPES).index(saved_type),
                                 format_func=AREA_TYPES.get)
    # A tuple as value makes it a range slider (from, to)
    start, end = st.sidebar.select_slider("Download interval (months)", options=months, value=saved_interval)

    st.session_state["saved_area_type"] = area_type
    st.session_state["saved_interval"] = (start, end)
    return area_type, start, end


@st.cache_data(ttl=3600, show_spinner="Downloading reservoir data from NVE ...")
def fetch_reservoirs(start_month: str, end_month: str) -> pd.DataFrame:
    """Download the reservoir data for the months start_month to end_month ("YYYY-MM").

    The NVE endpoint has no date parameters, so the response is cut to the chosen interval right
    after the download. Each interval is cached for an hour.
    """
    response = requests.get(f"{NVE_API}/HentOffentligData", timeout=60)
    response.raise_for_status()
    df = pd.DataFrame(response.json()).rename(columns=COLUMN_NAMES)

    # The date comes as text and the rows are not sorted (same as in part 1)
    df["date"] = pd.to_datetime(df["date"])
    month = df["date"].dt.strftime("%Y-%m")
    df = df[(month >= start_month) & (month <= end_month)].copy()
    df["area"] = [area_label(t, n) for t, n in zip(df["area_type"], df["area_number"])]
    return df.sort_values(["area_type", "area_number", "date"]).reset_index(drop=True)


@st.cache_data(ttl=3600)
def fetch_latest_week() -> pd.DataFrame:
    """Only the latest published week (a small download, used on the home page)."""
    response = requests.get(f"{NVE_API}/HentOffentligDataSisteUke", timeout=60)
    response.raise_for_status()
    return pd.DataFrame(response.json()).rename(columns=COLUMN_NAMES)


@st.cache_resource  # one database connection shared by all users and reruns
def mongo_client() -> MongoClient:
    """Connect to MongoDB. The connection string is stored in Streamlit secrets, not on GitHub."""
    return MongoClient(st.secrets["mongo"]["uri"], serverSelectionTimeoutMS=10000)


@st.cache_data(ttl=600, show_spinner="Reading cross-border flows from MongoDB ...")
def load_flows() -> pd.DataFrame:
    """Daily cross-border flows (GWh) per connection and direction, as stored by the notebook."""
    collection = mongo_client()["ind320"]["cross_border_flows_daily"]
    df = pd.DataFrame(list(collection.find({}, {"_id": 0})))
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df
