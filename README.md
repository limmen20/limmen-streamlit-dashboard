# limmen-streamlit-dashboard

Project work for IND320 *Data to Decision*: Norwegian hydropower reservoir data
in a Jupyter Notebook and a Streamlit app.

- Streamlit app: https://limmen-streamlit-dashboard.streamlit.app/
- Notebook: [IND320_part1.ipynb](IND320_part1.ipynb)

## Structure

| File | Content |
|---|---|
| `Home.py` | Front page of the app (entry point, sidebar menu) |
| `pages/1_Data_table.py` | Table with one row per data column and a line chart of the first month |
| `pages/2_Plot.py` | Plot with column drop-down and month range slider |
| `pages/3_Coming_soon.py` | Placeholder page |
| `utils.py` | Cached data loading and shared settings |
| `data/reservoirs.csv` | Weekly reservoir data (from the course material) |

## Run locally

```bash
pip install -r requirements.txt
streamlit run Home.py
```
