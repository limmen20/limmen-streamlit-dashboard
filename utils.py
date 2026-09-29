"""Shared helpers for the Streamlit app.

All pages import the data from here, so the CSV file is only read once
(thanks to Streamlit's cache) and the column names are the same everywhere.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

# Path to the local CSV file (in part 2 this will be replaced by MongoDB)
DATA_PATH = Path(__file__).parent / "data" / "reservoirs.csv"

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

# The measurement columns (the ones that make sense to plot) and readable labels.
# The remaining columns (date, area, ISO year/week, publication date) are keys/metadata.
VALUE_COLUMNS = {
    "filling_ratio": "Filling ratio",
    "filling_ratio_prev_week": "Filling ratio previous week",
    "filling_ratio_change": "Change in filling ratio since previous week",
    "filling_TWh": "Stored energy (TWh)",
    "capacity_TWh": "Reservoir capacity (TWh)",
}

# Columns that are fractions (0-1) and should be shown as percentages in plots
RATIO_COLUMNS = ["filling_ratio", "filling_ratio_prev_week", "filling_ratio_change"]

# One fixed colour per column, so a column keeps its colour on every plot
COLUMN_COLORS = {
    "filling_ratio": "#2a78d6",
    "filling_ratio_prev_week": "#eb6834",
    "filling_ratio_change": "#1baf7a",
    "filling_TWh": "#eda100",
    "capacity_TWh": "#e87ba4",
}


def area_label(area_type: str, area_number: int) -> str:
    """Turn the area code into a readable name.

    NO = all of Norway, EL = electricity price area (NO1-NO5),
    VASS = watercourse region (vassdragsområde).
    """
    if area_type == "NO":
        return "Norway (total)"
    if area_type == "EL":
        return f"Price area NO{area_number}"
    return f"Watercourse region {area_number}"


@st.cache_data  # cache the result so the CSV is not re-read on every interaction
def load_data() -> pd.DataFrame:
    """Read the reservoir CSV, rename columns to English and add helper columns."""
    df = pd.read_csv(DATA_PATH, parse_dates=["dato_Id"])
    df = df.rename(columns=COLUMN_NAMES)

    # Readable area name and a year-month string used by the month slider
    df["area"] = [area_label(t, n) for t, n in zip(df["area_type"], df["area_number"])]
    df["month"] = df["date"].dt.strftime("%Y-%m")

    # The rows in the file are not in date order, so sort them
    return df.sort_values(["area", "date"]).reset_index(drop=True)


def area_selector(df: pd.DataFrame) -> str:
    """Sidebar drop-down for choosing which area to look at (default: all of Norway)."""
    areas = sorted(df["area"].unique(), key=lambda a: (a != "Norway (total)", a))
    return st.sidebar.selectbox("Area", areas, index=0)
