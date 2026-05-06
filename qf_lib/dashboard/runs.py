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
"""Run discovery and statistics for the dashboard.

All numbers shown by the dashboard come from
:class:`~qf_lib.analysis.timeseries_analysis.timeseries_analysis.TimeseriesAnalysis`,
the same class used by the PDF tearsheet, so the values are guaranteed to
match the corresponding PDF artifact for the same run.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from qf_lib.analysis.timeseries_analysis.timeseries_analysis import TimeseriesAnalysis
from qf_lib.containers.series.prices_series import PricesSeries


def scan_runs(output_dir: Path) -> list[dict[str, Any]]:
    """Discover backtest runs in ``output_dir``.

    Each subdirectory containing a ``*Timeseries.xlsx`` file is considered a
    run. The directory name is parsed as ``"<timestamp> <strategy name>"``
    (the format produced by
    :class:`~qf_lib.backtesting.monitoring.backtest_monitor.BacktestMonitor`).

    Parameters
    ----------
    output_dir
        Path containing one folder per backtest run.

    Returns
    -------
    list of dict
        Newest-first list with keys ``id`` (folder name), ``name`` (strategy
        label), ``ts_str`` (timestamp prefix), ``path`` (folder Path), and
        ``ts_xlsx`` (Path to the Timeseries.xlsx file).
    """
    if not output_dir.exists():
        return []

    runs: list[dict[str, Any]] = []
    for d in sorted(output_dir.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        ts_xlsx = next(d.glob("*Timeseries.xlsx"), None)
        if not ts_xlsx:
            continue
        ts_str, _, name = d.name.partition(" ")
        runs.append(dict(
            id=d.name,
            name=name or d.name,
            ts_str=ts_str,
            path=d,
            ts_xlsx=ts_xlsx,
        ))
    return runs


@lru_cache(maxsize=64)
def load_strategy_series(ts_xlsx_str: str, name: str) -> PricesSeries:
    """Load the EOD portfolio value series from a ``Timeseries.xlsx``.

    Parameters
    ----------
    ts_xlsx_str
        Absolute path (as ``str`` so the result is cacheable) to the
        Timeseries.xlsx file written by ``BacktestMonitor``.
    name
        Strategy label that becomes the ``Series.name``; surfaces in chart
        titles and the statistics table header.
    """
    df = pd.read_excel(ts_xlsx_str, sheet_name="Sheet")
    df = df.rename(columns={df.columns[0]: "date"})
    s = df.set_index("date").iloc[:, 0]
    s.index = pd.to_datetime(s.index)
    series = PricesSeries(s.sort_index())
    series.name = name
    return series


def _fmt(x: Optional[float], places: int = 2) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:.{places}f}"


def stats_rows(series: PricesSeries) -> list[tuple[str, str, str]]:
    """Return ``(label, formatted value, unit)`` triples in PDF-tearsheet order.

    The list mirrors the rows produced by
    :meth:`~qf_lib.analysis.timeseries_analysis.timeseries_analysis.TimeseriesAnalysis.populate_table`
    so the dashboard's statistics table is byte-for-byte identical to the
    PDF version.
    """
    ta = TimeseriesAnalysis(series.to_simple_returns(), series.get_frequency())
    return [
        ("Start Date", ta.start_date.strftime("%Y-%m-%d"), ""),
        ("End Date", ta.end_date.strftime("%Y-%m-%d"), ""),
        ("Total Return", _fmt(ta.total_return * 100), "%"),
        ("Annualised Return", _fmt(ta.cagr * 100), "%"),
        ("Annualised Volatility", _fmt(ta.annualised_vol * 100), "%"),
        ("Annualised Upside Vol.", _fmt(ta.annualised_upside_vol * 100), "%"),
        ("Annualised Downside Vol.", _fmt(ta.annualised_downside_vol * 100), "%"),
        ("Sharpe Ratio", _fmt(ta.sharpe_ratio), ""),
        ("Omega Ratio", _fmt(ta.omega_ratio), ""),
        ("Calmar Ratio", _fmt(ta.calmar_ratio), ""),
        ("Gain to Pain Ratio", _fmt(ta.gain_to_pain_ratio), ""),
        ("Sorino Ratio", _fmt(ta.sorino_ratio), ""),
        ("5% CVaR", _fmt(ta.cvar * 100), "%"),
        ("Annualised 5% CVaR", _fmt(ta.annualised_cvar * 100), "%"),
        ("Max Drawdown", _fmt(ta.max_drawdown * 100), "%"),
        ("Avg Drawdown", _fmt(ta.avg_drawdown * 100), "%"),
        ("Avg Drawdown Duration", _fmt(ta.avg_drawdown_duration), "days"),
        ("Best Return", _fmt(ta.best_return * 100), "%"),
        ("Worst Return", _fmt(ta.worst_return * 100), "%"),
        ("Avg Positive Return", _fmt(ta.avg_positive_return * 100), "%"),
        ("Avg Negative Return", _fmt(ta.avg_negative_return * 100), "%"),
        ("Skewness", _fmt(ta.skewness), ""),
        ("No. of daily samples", str(len(ta.returns_tms)), ""),
    ]


def double_check(series: PricesSeries) -> list[dict[str, Any]]:
    """Recompute a few headline numbers from the chart-side series and report
    agreement with ``TimeseriesAnalysis``.

    Used by the dashboard's "Sanity check" panel so users can see at a glance
    that interactive charts and statistics are operating on consistent data.
    """
    ta = TimeseriesAnalysis(series.to_simple_returns(), series.get_frequency())
    rets = series.pct_change().dropna()
    norm = series / series.iloc[0]
    log_rets = np.log(series / series.shift(1)).dropna()  # qf-lib uses log returns for vol

    pairs = [
        ("Total Return [%]",            ta.total_return * 100,    (norm.iloc[-1] - 1) * 100),
        ("Max Drawdown [%]",            ta.max_drawdown * 100,    abs((norm / norm.cummax() - 1).min()) * 100),
        ("Annualised Volatility [%]",   ta.annualised_vol * 100,  log_rets.std(ddof=1) * np.sqrt(252) * 100),
        ("Skewness",                    ta.skewness,              rets.skew()),
        ("Best daily return [%]",       ta.best_return * 100,     rets.max() * 100),
        ("Worst daily return [%]",      ta.worst_return * 100,    rets.min() * 100),
    ]
    return [
        dict(label=label, pdf=f"{q:.4f}", chart=f"{c:.4f}",
             diff=f"{abs(q - c):.6f}", ok=abs(q - c) < 0.01)
        for label, q, c in pairs
    ]
