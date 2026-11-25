"""Explore - Map: interactive map of the areas in Magasinstatistikk (GeoJSON outlines on a folium map).

- "Colour the areas by": reservoir filling in the price areas, reservoir filling in the water areas,
  or a weather property (aggregated over the chosen month).
- The month slider chooses the time. It is stored in st.session_state["map_month"] and used by the
  Forecast page as the end of the training data.
- Clicking an area outlines it (thicker, yellow) and stores it as the global area for the other pages.
"""

import copy

import branca.colormap as cm
import folium
import pandas as pd
import streamlit as st
from shapely.geometry import Point, shape
from streamlit_folium import st_folium

from utils import (WEEKLY_WEATHER, area_label, current_area, current_month, fetch_reservoirs, load_geojson,
                   load_weather_weekly, month_options, page_header, region_code)

@st.cache_resource
def area_shapes(layer: str):
    """The area polygons as shapely shapes, to find which area a click is in."""
    return [(f["properties"], shape(f["geometry"])) for f in load_geojson(layer)["features"]]


page_header("Explore", "Map","Click an area to select it for all analysis pages (the selection is shown "
            "with a thick yellow outline and in the sidebar).")

# --- Controls --------------------------------------------------------------------------------------
c1, c2, c3 = st.columns([1.2, 1.2, 1.6])
colour_by = c1.radio("Colour the areas by", ["Price areas (filling)", "Water areas (filling)", "Weather property"])
if colour_by == "Weather property":
    prop = c2.selectbox("Weather property", list(WEEKLY_WEATHER), format_func=WEEKLY_WEATHER.get)
    layer = c2.radio("Areas", ["EL", "VASS"], horizontal=True, format_func={"EL": "Price areas", "VASS": "Water areas"}.get)
else:
    layer = "EL" if colour_by.startswith("Price") else "VASS"

months = [m for m in month_options() if m >= "2010-01"][:-1]   # weather from 2010, last complete month
saved = current_month()
month = c3.select_slider("Month", options=months, value=saved if saved in months else months[-1])
st.session_state["map_month"] = month   # shared with the Forecast page
in_month = lambda dates: dates.dt.strftime("%Y-%m") == month

# --- Values per area for the chosen month ----------------------------------------------------------
try:
    if colour_by == "Weather property":
        weather = load_weather_weekly()
        if weather.empty:
            st.warning("The weekly weather is not in MongoDB yet. Run the part 4 notebook to fill it.")
            st.stop()
        w = weather[in_month(weather["week"])]
        # Temperature and wind are averaged over the month, precipitation/rain/snow are summed
        agg = "mean" if prop in ("temperature", "wind_speed") else "sum"
        values = w.groupby("region")[prop].agg(agg).to_dict()
        label = WEEKLY_WEATHER[prop].split(" (")[0] + (" (monthly mean)" if agg == "mean" else " (monthly total)")
        unit = {"temperature": " °C", "wind_speed": " km/h", "snowfall": " cm"}.get(prop, " mm")
        fmt = lambda v: f"{v:.1f}{unit}"
        colors = (["#3987e5", "#f2f2f2", "#d95926"] if prop == "temperature" else
                  ["#f2f2f2", "#d95926"] if prop == "wind_speed" else ["#f2f2f2", "#3987e5"])
    else:
        res = fetch_reservoirs(month, month)
        r = res[res["area_type"] == layer]
        values = {region_code(layer, n): v for n, v in r.groupby("area_number")["filling_ratio"].mean().items()}
        label, fmt, colors = "Mean filling ratio", (lambda v: f"{v:.1%}"), ["#f2f2f2", "#3987e5"]   # light = low, blue = high
except Exception as error:
    st.error(f"Could not load the values for the map ({type(error).__name__}). Check the NVE API and MongoDB.")
    st.stop()

if not values:
    st.warning(f"No data for {month} yet.")
    st.stop()

# --- Map -------------------------------------------------------------------------------------------
geo = copy.deepcopy(load_geojson(layer))   # copy: the cached GeoJSON must not be changed
for feature in geo["features"]:
    v = values.get(feature["properties"]["region"])
    feature["properties"]["value"] = v
    feature["properties"]["value_text"] = fmt(v) if v is not None else "no data"

vmin, vmax = min(values.values()), max(values.values())
colormap = cm.LinearColormap(colors, vmin=vmin, vmax=vmax if vmax > vmin else vmin + 1e-6,
                             caption=f"{label}, {month}")
selected = region_code(*current_area())


def style(feature):
    """Transparent fill by value; the selected area gets a thick yellow outline."""
    is_selected = feature["properties"]["region"] == selected
    v = feature["properties"]["value"]
    return {"fillColor": colormap(v) if v is not None else "#777777", "fillOpacity": 0.55,
            "color": "#ffd60a" if is_selected else "#e6edf3", "weight": 4 if is_selected else 1}


# Dark grey basemap from Esri (no API key needed), to match the dark app theme
m = folium.Map(location=[65, 15], zoom_start=4, tiles=None)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    attr="Esri, HERE, Garmin, © OpenStreetMap contributors", name="Dark grey").add_to(m)
folium.GeoJson(geo, style_function=style, highlight_function=lambda f: {"weight": 3, "color": "#ffffff"},
               tooltip=folium.GeoJsonTooltip(fields=["name", "value_text"], aliases=["Area", label])).add_to(m)
colormap.add_to(m)

left, right = st.columns([3, 1])
with left:
    # Only clicks make the app rerun (not panning/zooming)
    out = st_folium(m, height=560, use_container_width=True, returned_objects=["last_clicked"], key=f"map_{layer}")

# A new click: find the area that contains the clicked point (point-in-polygon with shapely) and store
# it as the global area. It is applied in Home.py before the sidebar widgets are drawn.
clicked = (out or {}).get("last_clicked")
if clicked:
    point = Point(clicked["lng"], clicked["lat"])
    hit = next((props for props, geom in area_shapes(layer) if geom.contains(point)), None)
    click_id = (round(clicked["lat"], 5), round(clicked["lng"], 5))
    last_clicks = st.session_state.setdefault("last_map_click", {})
    if hit and last_clicks.get(layer) != click_id:   # only react to new clicks inside an area
        last_clicks[layer] = click_id
        st.session_state["pending_area"] = (hit["area_type"], int(hit["area_number"]))
        st.rerun()

with right:
    st.markdown(f"**Selected area:** {area_label(*current_area())}")
    table = pd.DataFrame({"Area": [area_label(layer, int(f["properties"]["area_number"])) for f in geo["features"]],
                          label: [f["properties"]["value_text"] for f in geo["features"]]})
    st.dataframe(table, hide_index=True, width="stretch")
    st.caption("The month is also used by the Forecast page as the end of the training data.")
