#     Copyright 2016-present CERN – European Organization for Nuclear Research
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
"""Plotly figure builders mirroring the PDF tearsheet charts.

Each ``fig_*`` function accepts the strategy ``PricesSeries`` (EOD portfolio
value indexed by date) and returns a ``plotly.graph_objects.Figure`` that
reproduces the corresponding chart from
:class:`~qf_lib.analysis.tearsheets.tearsheet_without_benchmark.TearsheetWithoutBenchmark`.

Computations match the PDF: the source series and the underlying derivations
(monthly resampling, log-return rolling, drawdown, etc.) are identical.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import scipy.stats as stats

from qf_lib.containers.series.prices_series import PricesSeries

# Style — tuned to match the PDF tearsheet look
C_PRIMARY = "#1f3a8a"
C_GREY = "#6b7280"
C_TEXT = "#0f172a"
AXIS = dict(showgrid=True, gridcolor="#e5e7eb", linecolor="#9ca3af",
            zerolinecolor="#cbd5e1", zerolinewidth=1, ticks="outside",
            tickcolor="#9ca3af")
TITLE_STYLE = dict(font=dict(size=14, color=C_TEXT), x=0.02, xanchor="left")
H_HERO, H_FULL, H_HALF, H_DD = 340, 300, 320, 240


def _make_fig(title: str, height: int = H_FULL) -> go.Figure:
    """Return a Figure pre-configured with the dashboard's standard layout."""
    fig = go.Figure()
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter,system-ui,-apple-system,sans-serif", size=12, color=C_TEXT),
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(l=55, r=20, t=40, b=40),
        title=dict(text=title, **TITLE_STYLE),
        xaxis=AXIS, yaxis=AXIS,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(255,255,255,0.8)"),
        hoverlabel=dict(bgcolor="white", bordercolor="#cbd5e1", font_size=12),
        height=height,
    )
    return fig


def _monthly_simple_returns(series: PricesSeries) -> pd.Series:
    return series.resample("ME").last().pct_change().dropna()


def fig_strategy_performance(series: PricesSeries) -> go.Figure:
    """Cumulative strategy value normalised to 1.0 at start (linear y-axis)."""
    norm = series / series.iloc[0]
    fig = _make_fig("Strategy Performance", height=H_HERO)
    fig.update_layout(yaxis=dict(title=None))
    fig.add_trace(go.Scatter(x=norm.index, y=norm.values, name=str(series.name),
                             line=dict(color=C_PRIMARY, width=1.6),
                             hovertemplate="%{x|%Y-%m-%d}<br>×%{y:.3f}<extra></extra>"))
    fig.add_hline(y=1.0, line_color="black", line_width=0.7)
    return fig


def fig_monthly_heatmap(series: PricesSeries) -> go.Figure:
    """Year × month grid of simple monthly returns, diverging colour scale."""
    monthly = _monthly_simple_returns(series) * 100
    df = pd.DataFrame({"year": monthly.index.year, "month": monthly.index.month, "ret": monthly.values})
    grid = df.pivot(index="year", columns="month", values="ret").reindex(columns=range(1, 13)).sort_index()
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    abs_max = float(np.nanmax(np.abs(grid.values))) if grid.size else 1.0
    text = [[f"{v:.1f}" if pd.notna(v) else "" for v in row] for row in grid.values]

    fig = _make_fig(f"Monthly Returns - {series.name}", height=H_HALF)
    fig.update_layout(
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False, autorange="reversed", tickmode="linear", dtick=1),
    )
    fig.add_trace(go.Heatmap(
        z=np.where(np.isnan(grid.values), 0, grid.values),
        x=months, y=grid.index.astype(int), text=text, texttemplate="%{text}",
        colorscale=[[0, "#b91c1c"], [0.5, "#ffffff"], [1, "#1f3a8a"]],
        zmid=0, zmin=-abs_max, zmax=abs_max,
        textfont=dict(size=10),
        hovertemplate="%{y} %{x}: %{z:.2f}%<extra></extra>",
        colorbar=dict(thickness=10, len=0.7, ticksuffix="%"),
    ))
    return fig


def fig_annual_returns(series: PricesSeries) -> go.Figure:
    """Calendar-year returns as horizontal bars with a mean reference line."""
    annual = series.resample("YE").last().pct_change().dropna() * 100
    mean_ret = float(annual.mean())
    fig = _make_fig(f"Annual Returns - {series.name}", height=H_HALF)
    fig.update_layout(xaxis=dict(ticksuffix="%"), yaxis=dict(autorange="reversed"),
                      showlegend=False)
    fig.add_trace(go.Bar(
        x=annual.values, y=annual.index.year.astype(str), orientation="h",
        marker_color=C_PRIMARY, text=[f"{v:.0f}%" for v in annual.values],
        textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
    ))
    fig.add_vline(x=mean_ret, line_dash="dash", line_color=C_GREY,
                  annotation_text=f"Mean {mean_ret:.1f}%", annotation_position="top right")
    return fig


def fig_returns_distribution(series: PricesSeries) -> go.Figure:
    """Histogram of monthly simple returns with a mean reference line."""
    monthly = _monthly_simple_returns(series) * 100
    fig = _make_fig("Distribution of Monthly Returns", height=H_HALF)
    fig.update_layout(xaxis=dict(ticksuffix="%", title=None),
                      yaxis=dict(title="Occurrences"),
                      bargap=0.04, showlegend=False)
    fig.add_trace(go.Histogram(x=monthly.values, nbinsx=22,
                               marker_color=C_PRIMARY,
                               marker_line=dict(color="white", width=0.5),
                               hovertemplate="%{x:.1f}%: %{y}<extra></extra>"))
    fig.add_vline(x=float(monthly.mean()), line_dash="dash", line_color=C_GREY,
                  annotation_text="Mean", annotation_position="top right")
    return fig


def fig_qq(series: PricesSeries) -> go.Figure:
    """Q-Q plot of daily returns against a fitted normal distribution."""
    rets = series.pct_change().dropna() * 100
    osm, osr = stats.probplot(rets.values, dist="norm", fit=False)
    slope, intercept, *_ = stats.linregress(osm, osr)
    fig = _make_fig("Normal Distribution Q-Q", height=H_HALF)
    fig.update_layout(xaxis=dict(title="Normal Distribution Quantile"),
                      yaxis=dict(title="Observed Quantile"))
    fig.add_trace(go.Scatter(x=osm, y=osr, mode="markers", name="Observed",
                             marker=dict(color=C_PRIMARY, size=4, opacity=0.7),
                             hovertemplate="N=%{x:.2f}<br>Obs=%{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[osm.min(), osm.max()],
                             y=[slope * osm.min() + intercept, slope * osm.max() + intercept],
                             mode="lines", name="Normal", hoverinfo="skip",
                             line=dict(color=C_GREY, width=1.5)))
    return fig


def fig_rolling_stats(series: PricesSeries, window: int = 126, step: int = 42) -> go.Figure:
    """Rolling cumulative return and annualised volatility (default 6m / 2m step)."""
    rets = series.pct_change().dropna()
    points = []
    for i in range(window, len(rets) + 1, step):
        w = rets.iloc[i - window:i]
        cum = float((1 + w).prod() - 1) * 100
        vol = float(w.std() * np.sqrt(252)) * 100
        points.append((rets.index[i - 1], cum, vol))
    df = pd.DataFrame(points, columns=["date", "ret", "vol"])
    fig = _make_fig(f"Rolling Stats [{window} daily samples]", height=H_FULL)
    fig.update_layout(yaxis=dict(ticksuffix="%"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["ret"], name="Rolling Return",
                             line=dict(color=C_PRIMARY, width=1.6),
                             hovertemplate="%{x|%Y-%m-%d}<br>Return %{y:.2f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["vol"], name="Rolling Volatility",
                             line=dict(color=C_GREY, width=1.4),
                             hovertemplate="%{x|%Y-%m-%d}<br>Vol %{y:.2f}%<extra></extra>"))
    fig.add_hline(y=0, line_color="black", line_width=0.7)
    return fig


def fig_cone(series: PricesSeries, nr_of_data_points: int = 252) -> go.Figure:
    """Project the in-sample log-return distribution onto the OOS window with
    ±1σ / ±2σ bands, matching :class:`~qf_lib.plotting.charts.cone_chart.ConeChart`."""
    is_end = max(2, len(series) - nr_of_data_points)
    log_rets = np.log(1 + series.iloc[:is_end].pct_change().dropna())
    mu, sigma = float(log_rets.mean()), float(log_rets.std())

    oos = series.iloc[is_end - 1:].copy()
    oos = oos / oos.iloc[0]
    days = np.arange(len(oos))
    expected = np.exp(mu * days)
    upper1 = np.exp(mu * days + sigma * np.sqrt(days))
    lower1 = np.exp(mu * days - sigma * np.sqrt(days))
    upper2 = np.exp(mu * days + 2 * sigma * np.sqrt(days))
    lower2 = np.exp(mu * days - 2 * sigma * np.sqrt(days))

    fig = _make_fig("Performance vs. Expectation", height=H_HALF)
    fig.update_layout(xaxis=dict(title="Observations in the past"),
                      yaxis=dict(title="Current valuation"))
    blank = dict(line=dict(width=0), showlegend=False, hoverinfo="skip")
    fig.add_trace(go.Scatter(x=days, y=upper2, **blank))
    fig.add_trace(go.Scatter(x=days, y=lower2, fill="tonexty",
                             fillcolor="rgba(148,163,184,0.18)", **blank))
    fig.add_trace(go.Scatter(x=days, y=upper1, **blank))
    fig.add_trace(go.Scatter(x=days, y=lower1, fill="tonexty",
                             fillcolor="rgba(148,163,184,0.30)", **blank))
    fig.add_trace(go.Scatter(x=days, y=expected, name="Expected",
                             line=dict(color=C_GREY, width=1.5)))
    fig.add_trace(go.Scatter(x=days, y=oos.values, name="Current valuation",
                             line=dict(color=C_PRIMARY, width=1.7),
                             hovertemplate="t=%{x}<br>×%{y:.3f}<extra></extra>"))
    return fig


def fig_quantiles(series: PricesSeries) -> go.Figure:
    """Daily / weekly / monthly return distributions side-by-side as boxplots."""
    daily = series.pct_change().dropna()
    weekly = series.resample("W").last().pct_change().dropna()
    monthly = _monthly_simple_returns(series)
    fig = _make_fig("Return Quantiles", height=H_HALF)
    fig.update_layout(yaxis=dict(title="returns", tickformat=".2f"))
    for name, data in [("daily", daily), ("weekly", weekly), ("monthly", monthly)]:
        fig.add_trace(go.Box(y=data.values, name=name, marker_color=C_PRIMARY,
                             line=dict(color=C_PRIMARY), boxmean=False,
                             boxpoints="outliers", showlegend=False))
    return fig


def fig_underwater(series: PricesSeries) -> go.Figure:
    """Underwater (drawdown) chart filled to zero."""
    norm = series / series.iloc[0]
    dd = (norm / norm.cummax() - 1) * 100
    fig = _make_fig("Drawdown", height=H_DD)
    fig.update_layout(yaxis=dict(ticksuffix="%"), showlegend=False)
    fig.add_trace(go.Scatter(x=dd.index, y=dd.values, fill="tozeroy",
                             line=dict(color=C_PRIMARY, width=1),
                             fillcolor="rgba(31, 58, 138, 0.45)",
                             name="Drawdown",
                             hovertemplate="%{x|%Y-%m-%d}<br>DD %{y:.2f}%<extra></extra>"))
    return fig


def fig_skewness(series: PricesSeries) -> go.Figure:
    """Cumulative chronological vs magnitude-sorted returns; the gap visualises skew."""
    rets = series.pct_change().dropna()
    chrono = (1 + rets).cumprod()
    sorted_cum = (1 + rets.sort_values().reset_index(drop=True)).cumprod()
    sorted_cum.index = chrono.index
    fig = _make_fig("Skewness", height=H_HALF)
    fig.update_layout(yaxis=dict(title="Profit/Loss"))
    fig.add_trace(go.Scatter(x=chrono.index, y=chrono.values, name="Chronological returns",
                             line=dict(color=C_PRIMARY, width=1.6),
                             hovertemplate="%{x|%Y-%m-%d}<br>×%{y:.3f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=sorted_cum.index, y=sorted_cum.values,
                             name="Returns sorted by magnitude",
                             line=dict(color=C_GREY, width=1.4),
                             hovertemplate="t=%{x|%Y-%m-%d}<br>×%{y:.3f}<extra></extra>"))
    return fig
