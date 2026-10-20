# limmen-streamlit-dashboard

Project work for IND320 *Data to Decision*: Norwegian hydropower reservoirs and cross-border
electricity flows, in Jupyter Notebooks and a Streamlit app.

- Streamlit app (part 1): https://limmen-app-dashboard.streamlit.app/
- Streamlit app (part 2): https://limmen-app-dashboard-part2.streamlit.app/
- Notebooks: [notebooks/](notebooks/)

## Structure

| File | Content |
|---|---|
| `Home.py` | Front page of the app (entry point, sidebar menu) |
| `pages/1_Reservoirs.py` | Reservoir plot and table from the NVE Magasinstatistikk API |
| `pages/2_Cross_border_flows.py` | Cross-border flows from MongoDB: pie chart and line plot |
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
