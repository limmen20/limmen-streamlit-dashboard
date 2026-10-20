# limmen-streamlit-dashboard

Project work for IND320 *Data to Decision*: Norwegian hydropower reservoirs and cross-border
electricity flows, in Jupyter Notebooks and a Streamlit app.

- Streamlit app: https://limmen-app-dashboard.streamlit.app/
- Notebooks: [notebooks/](notebooks/)

## Structure

| File | Content |
|---|---|
| `Home.py` | Front page of the app (entry point, sidebar menu) |
| `pages/1_Data_table.py` | Reservoir table with one row and line charts per area (NVE API) |
| `pages/2_Plot.py` | Reservoir plot with one line per area (NVE API) |
| `pages/3_Cross_border_flows.py` | Cross-border flows from MongoDB: pie chart and line plot |
| `pages/4_Coming_soon.py` | Placeholder page |
| `utils.py` | Cached API and MongoDB access, shared settings |
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
