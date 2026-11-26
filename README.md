# limmen-streamlit-dashboard

Project work for IND320 *Data to Decision*: Norwegian hydropower reservoirs, weather, exchange rates
and cross-border electricity flows, in Jupyter Notebooks and a Streamlit app.

- Streamlit app: https://limmen-app-dashboard.streamlit.app/
- Notebooks: [notebooks/](notebooks/)

## Structure

| File | Content |
|---|---|
| `Home.py` | Entry point: grouped menu (`st.navigation`) and the global area selection in the sidebar |
| `pages/home.py` | Front page with the latest week and links to the three groups |
| `pages/map.py` | Explore: map of the areas (GeoJSON), coloured by filling or weather; click to select an area |
| `pages/reservoirs.py` | Explore: reservoir filling as plot and table (NVE API) |
| `pages/cross_border_flows.py` | Explore: cross-border flows from MongoDB |
| `pages/currency.py` | Explore: EUR and USD exchange rates (Norges Bank) |
| `pages/reservoir_analysis.py` | Patterns & anomalies: STL decomposition and spectrogram |
| `pages/weather_outliers.py` | Patterns & anomalies: weather outliers (SPC) and anomalies (LOF) |
| `pages/correlation.py` | Predict: sliding window correlation between weather and the reservoirs |
| `pages/forecast.py` | Predict: forecast of the reservoir filling (River SNARIMAX) |
| `utils.py` | Cached access to the APIs and MongoDB, global controls and page headers |
| `analysis.py` | SPC/DCT, LOF, STL and spectrogram functions |
| `forecasting.py` | Forecasting function used by the Forecast page |
| `data/` | Shapefiles (part 3) and GeoJSON outlines for the map (part 4) |
| `.streamlit/config.toml` | App theme |
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
