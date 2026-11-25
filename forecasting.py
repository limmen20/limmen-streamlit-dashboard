"""Forecasting of the weekly reservoir filling with River's SNARIMAX (same function as in the part 4 notebook).

- Time resolution: weekly (the resolution of Magasinstatistikk). Weather and currency are aggregated
  to the same weeks (ending on Sunday).
- Exogenous inputs: weather properties for the region, EUR/USD exchange rates and season features.
  Future values are not known when forecasting, so weather uses the average for the same week of the
  year in the training period (climatology), and the exchange rates keep their last known value.
- Dynamic forecasting: each forecast step builds on the previous forecast steps (model.forecast).
- Confidence interval: two extra models with quantile loss (5% and 95%) give a 90% interval.
"""

import math

import numpy as np
import pandas as pd
from river import linear_model, optim, preprocessing, time_series

WEATHER_INPUTS = ["temperature", "precipitation", "rain", "snowfall", "wind_speed"]
CURRENCY_INPUTS = ["EUR", "USD"]

# The best settings from the tests in the part 4 notebook (9 areas x 4 forecast origins, 26 weeks ahead):
# mean absolute error 0.086 vs. 0.118 for "same week last year". Used as defaults in the app.
DEFAULTS = dict(p=2, d=1, q=0, sp=1, sd=1, sq=0, history_years=10, horizon=26,
                inputs=["season"], learning_rate=0.01)


def season_features(date: pd.Timestamp) -> dict:
    """Smooth 'distance' from the date to each month of the year (like the book's SNARIMAX example)."""
    month = date.month + (date.day - 1) / 31
    return {f"season_m{m}": math.exp(-((month - m) ** 2)) for m in range(1, 13)}


def future_inputs(exog: pd.DataFrame, train_index: pd.DatetimeIndex, future_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Inputs for the forecast weeks: weather = average for the same week of the year in the training
    period, currency = last known value."""
    future = pd.DataFrame(index=future_index)
    train = exog.loc[exog.index.isin(train_index)]
    week_of_year = train.index.isocalendar().week.to_numpy()
    for col in exog.columns:
        if col in CURRENCY_INPUTS:
            future[col] = train[col].dropna().iloc[-1]
        else:
            climatology = train[col].groupby(week_of_year).mean()
            weeks = future_index.isocalendar().week.to_numpy()
            future[col] = climatology.reindex(weeks).fillna(train[col].mean()).to_numpy()
    return future


def _make_model(p, d, q, m, sp, sd, sq, learning_rate, quantile=None):
    loss = optim.losses.Quantile(quantile) if quantile is not None else optim.losses.Squared()
    regressor = preprocessing.StandardScaler() | linear_model.LinearRegression(
        optimizer=optim.SGD(learning_rate), intercept_lr=0.1, loss=loss)
    return time_series.SNARIMAX(p=p, d=d, q=q, m=m, sp=sp, sd=sd, sq=sq, regressor=regressor)


def forecast_filling(target: pd.Series, exog: pd.DataFrame | None = None, train_end=None, history_years: int = 10,
                     horizon: int = 26, p: int = 2, d: int = 1, q: int = 0, sp: int = 1, sd: int = 1, sq: int = 0,
                     use_season: bool = True, learning_rate: float = 0.01, interval: bool = False,
                     progress=None) -> pd.DataFrame:
    """Forecast the weekly filling ratio `horizon` weeks after `train_end`.

    target: weekly filling ratio (index = Sundays). exog: weekly inputs with the same index (or None).
    Returns a DataFrame with forecast (and lower/upper if interval=True) and the actual values if known.
    progress: optional function called with a number 0-1 while training (for a progress bar).
    """
    train_end = pd.Timestamp(train_end) if train_end is not None else target.index[-1]
    train = target[(target.index > train_end - pd.DateOffset(years=history_years)) & (target.index <= train_end)].dropna()
    future_index = pd.date_range(train.index[-1] + pd.Timedelta(weeks=1), periods=horizon, freq="W-SUN")

    exog = exog.reindex(train.index.union(future_index)) if exog is not None and len(exog.columns) else None
    if exog is not None:
        exog = exog.loc[train.index].ffill().bfill().combine_first(exog)   # fill small gaps in the training inputs
        future = future_inputs(exog, train.index, future_index)

    def x_for(date, row):
        x = season_features(date) if use_season else {}
        if row is not None:
            x.update({k: float(v) for k, v in row.items()})
        return x or None

    quantiles = [None, 0.05, 0.95] if interval else [None]
    models = [_make_model(p, d, q, 52, sp, sd, sq, learning_rate, qt) for qt in quantiles]
    for i, (date, y) in enumerate(train.items()):
        x = x_for(date, exog.loc[date] if exog is not None else None)
        for model in models:
            model.learn_one(y, x=x)
        if progress is not None and i % 50 == 0:
            progress(i / len(train))

    xs = [x_for(date, future.loc[date] if exog is not None else None) for date in future_index]
    xs = None if all(x is None for x in xs) else xs
    result = pd.DataFrame(index=future_index)
    for name, model in zip(["forecast", "lower", "upper"], models):
        result[name] = np.clip(model.forecast(horizon=horizon, xs=xs), 0, 1)   # filling is between 0 and 1
    result["actual"] = target.reindex(future_index)
    if progress is not None:
        progress(1.0)
    return result
