"""Analysis functions for the app (same methods as in the part 3 notebook, but with Plotly plots).

- spc_precipitation: outliers in precipitation with DCT high-pass + SPC limits (robust statistics)
- lof_temperature:   anomalies in temperature with Local Outlier Factor
- stl_figure:        STL decomposition of the reservoir filling ratio
- spectrogram_figure: spectrogram of the reservoir filling ratio
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.fft import dct, idct
from scipy.signal import spectrogram
from sklearn.neighbors import LocalOutlierFactor
from statsmodels.tsa.seasonal import STL

LINE, LIMIT, OUTLIER = "#2a78d6", "#eb6834", "#e34948"


def spc_precipitation(precip: pd.Series, freq_cutoff: float = 1 / 30, n_std: float = 3.0):
    """Outliers in precipitation with Statistical Process Control.

    The DCT high-pass removes variations slower than freq_cutoff (cycles per day), which gives the
    seasonally adjusted variations (SATV). Limits = median(SATV) +- n_std * robust std (from MAD),
    put back on the slow part so they follow the season. SATV itself is not plotted.
    """
    x = precip.to_numpy(dtype=float)
    n = len(x)
    step_days = (precip.index[1] - precip.index[0]) / pd.Timedelta(days=1)   # 1/24 for hourly data

    coeffs = dct(x, norm="ortho")
    freq = np.arange(n) / (2 * n * step_days)    # frequency of each DCT component, cycles per day
    coeffs[freq < freq_cutoff] = 0               # high-pass: drop the slow components
    satv = idct(coeffs, norm="ortho")
    slow = x - satv                              # the part that was removed

    center = np.median(satv)
    sigma = 1.4826 * np.median(np.abs(satv - center))   # MAD scaled to a std for normal data
    upper = slow + center + n_std * sigma
    lower = slow + center - n_std * sigma
    is_out = (satv > center + n_std * sigma) | (satv < center - n_std * sigma)

    fig = go.Figure()
    fig.add_trace(go.Scattergl(x=precip.index, y=x, name="Precipitation", line=dict(color=LINE, width=1)))
    fig.add_trace(go.Scattergl(x=precip.index, y=upper, name="Upper SPC limit", line=dict(color=LIMIT, width=1.5, dash="dash")))
    fig.add_trace(go.Scattergl(x=precip.index, y=lower, name="Lower SPC limit", line=dict(color=LIMIT, width=1.5, dash="dot")))
    fig.add_trace(go.Scattergl(x=precip.index[is_out], y=x[is_out], name="Outliers", mode="markers",
                               marker=dict(color=OUTLIER, size=5)))
    fig.update_layout(title=f"Precipitation with SPC limits ({is_out.sum()} outliers)",
                      xaxis_title="Time (UTC)", yaxis_title="Precipitation (mm per hour)",
                      hovermode="x unified", legend=dict(orientation="h", y=-0.2))

    outliers = pd.DataFrame({"time": precip.index[is_out], "precipitation_mm": x[is_out],
                             "upper_limit_mm": upper[is_out],
                             "side": np.where(satv[is_out] > center, "above", "below")})
    summary = {"hours": n, "outliers": int(is_out.sum()), "share": float(is_out.mean()),
               "above": int((satv > center + n_std * sigma).sum()), "below": int((satv < center - n_std * sigma).sum()),
               "robust_std": float(sigma), "largest_mm": float(x[is_out].max()) if is_out.any() else None}
    return fig, summary, outliers


def lof_temperature(temp: pd.Series, contamination: float = 0.01, n_neighbors: int = 100, window_days: int = 30):
    """Temperature anomalies with Local Outlier Factor (contamination = share of outliers).

    LOF is run on the deviation from a moving average over window_days, so an anomaly is an hour
    that is unusually warm or cold for the time of year. With only 20 neighbours LOF also marked
    ordinary values in small gaps, so the default is 100.
    """
    x = temp.to_numpy(dtype=float)
    seasonal = temp.rolling(f"{window_days}D", center=True, min_periods=1).mean().to_numpy()
    deviation = x - seasonal
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
    is_out = lof.fit_predict(deviation.reshape(-1, 1)) == -1   # -1 = outlier
    scores = -lof.negative_outlier_factor_                     # higher = more unusual

    fig = go.Figure()
    fig.add_trace(go.Scattergl(x=temp.index, y=x, name="Temperature", line=dict(color=LINE, width=1)))
    fig.add_trace(go.Scattergl(x=temp.index, y=seasonal, name=f"{window_days}-day mean", line=dict(color="grey", width=1.5)))
    fig.add_trace(go.Scattergl(x=temp.index[is_out], y=x[is_out], name="Anomalies (LOF)", mode="markers",
                               marker=dict(color=OUTLIER, size=5)))
    fig.update_layout(title=f"Temperature with LOF anomalies ({is_out.sum()} anomalies)",
                      xaxis_title="Time (UTC)", yaxis_title="Temperature (°C)",
                      hovermode="x unified", legend=dict(orientation="h", y=-0.2))

    outliers = pd.DataFrame({"time": temp.index[is_out], "temperature_C": x[is_out],
                             "deviation_C": deviation[is_out].round(1), "lof_score": scores[is_out]})
    summary = {"hours": len(x), "anomalies": int(is_out.sum()), "share": float(is_out.mean()),
               "warmer": int((deviation[is_out] > 0).sum()), "colder": int((deviation[is_out] < 0).sum()),
               "largest_deviation_C": float(np.abs(deviation[is_out]).max()) if is_out.any() else None}
    return fig, summary, outliers.sort_values("lof_score", ascending=False)


def weekly_series(df: pd.DataFrame, area_type: str, area_number: int) -> pd.Series:
    """Filling ratio for one area as a regular weekly series (the dates are Sundays)."""
    area = df[(df["area_type"] == area_type) & (df["area_number"] == area_number)]
    return area.set_index("date")["filling_ratio"].asfreq("W-SUN").interpolate()


def stl_figure(series: pd.Series, period: int = 52, seasonal: int = 13, trend: int = 89, robust: bool = True):
    """STL decomposition (LOESS) of a weekly series: trend + seasonal + residual."""
    res = STL(series, period=period, seasonal=seasonal, trend=trend, robust=robust).fit()
    parts = {"Observed": series, "Trend": res.trend, "Seasonal": res.seasonal, "Residual": res.resid}
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04, subplot_titles=list(parts))
    for i, (name, values) in enumerate(parts.items(), start=1):
        fig.add_trace(go.Scatter(x=values.index, y=values, name=name, line=dict(color=LINE, width=1.5)), row=i, col=1)
    fig.update_layout(height=750, showlegend=False,
                      title=f"STL decomposition (seasonal={seasonal}, trend={trend}, robust={robust})")
    fig.update_xaxes(title_text="Date", row=4, col=1)
    return fig


def spectrogram_figure(series: pd.Series, window_length: int = 104, overlap: int = 78, max_freq: float = 6):
    """Spectrogram of a weekly series. fs = 52 samples per year, so frequencies are in cycles per year."""
    f, t, power = spectrogram(series.to_numpy(), fs=52, nperseg=window_length, noverlap=overlap,
                              detrend="linear", scaling="density")
    times = series.index[0] + pd.to_timedelta(t * 365.25, unit="D")   # middle of each window
    keep = f <= max_freq
    fig = go.Figure(go.Heatmap(x=times, y=f[keep], z=10 * np.log10(power[keep] + 1e-12),
                               colorscale="Viridis", colorbar=dict(title="Power (dB)")))
    fig.update_layout(height=500, title=f"Spectrogram (window {window_length} weeks, overlap {overlap} weeks)",
                      xaxis_title="Date (middle of window)", yaxis_title="Frequency (cycles per year)")
    return fig
