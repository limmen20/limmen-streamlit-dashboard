# limmen-streamlit-dashboard

Project work for IND320 *Data to Decision*: Norwegian hydropower reservoirs, weather and cross-border
electricity flows, in Jupyter Notebooks and a Streamlit app.

- Streamlit app: https://limmen-app-dashboard.streamlit.app/
- Notebooks: [notebooks/](notebooks/)

## Structure

| File | Content |
|---|---|
| `Home.py` | Entry point: page settings and the grouped sidebar menu (`st.navigation`) |
| `pages/home.py` | Front page |
| `pages/data_table.py` | Reservoirs: table with one row and line charts per area (NVE API) |
| `pages/plot.py` | Reservoirs: plot with one line per area (NVE API) |
| `pages/reservoir_analysis.py` | Reservoirs: STL decomposition and spectrogram (tabs) |
| `pages/weather_outliers.py` | Weather: precipitation outliers (SPC) and temperature anomalies (LOF) (tabs) |
| `pages/cross_border_flows.py` | Power exchange: cross-border flows from MongoDB |
| `pages/coming_soon.py` | Placeholder page |
| `utils.py` | Cached API, MongoDB and open-meteo access, shared sidebar controls |
| `analysis.py` | SPC/DCT, LOF, STL and spectrogram functions used by the app |
| `data/shapefiles/` | NVE price areas and NVE regions (downloaded in the part 3 notebook) |
| `notebooks/` | Jupyter Notebooks for each part of the project |

## Run locally

```bash
pip install -r requirements.txt
streamlit run Home.py
```

The app expects a MongoDB connection string in `.streamlit/secrets.toml` (not included in the repository):

```toml
[mongo]
uri = "mongodb+srv://..."
```
