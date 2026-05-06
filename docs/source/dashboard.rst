dashboard
**********

Web-based viewer that browses every backtest run produced by
:class:`~qf_lib.backtesting.monitoring.backtest_monitor.BacktestMonitor` and renders
the same charts and statistics as the auto-generated PDF tearsheet, interactively.

Installation
------------

The dashboard is shipped under an optional extra:

.. code-block:: bash

    pip install qf-lib[dashboard]

This pulls in ``nicegui``, ``plotly``, and ``scipy``.

Quick start
-----------

After running one or more backtests, point the dashboard at the directory that
contains the per-run folders:

.. code-block:: bash

    python -m qf_lib.dashboard --output-dir ./output/backtesting

Open the URL printed on stdout (default ``http://127.0.0.1:8765``).

The home page lists every run with sortable columns (Sharpe, Total Return, Max DD,
Skewness, etc.) and a name filter. Clicking a row opens a detail page that renders
ten Plotly charts mirroring the PDF tearsheet:

- Strategy Performance (cumulative value)
- Monthly Returns heatmap
- Annual Returns horizontal bars
- Distribution of Monthly Returns histogram
- Normal Distribution Q-Q plot
- Rolling Stats (rolling return + rolling volatility)
- Performance vs. Expectation (Cone)
- Return Quantiles (daily / weekly / monthly boxplots)
- Drawdown (underwater)
- Skewness (chronological vs magnitude-sorted)

A "Sanity check" panel at the top of the detail page recomputes a few headline
numbers from the chart-side series and shows the absolute difference against
:class:`~qf_lib.analysis.timeseries_analysis.timeseries_analysis.TimeseriesAnalysis`
so the user can see at a glance that interactive charts and statistics are
operating on consistent data. The full statistics table (23 fields) is rendered
below in PDF-tearsheet order.

CLI
---

.. code-block:: text

    python -m qf_lib.dashboard [-h] --output-dir OUTPUT_DIR
                               [--port PORT] [--host HOST]
                               [--company-name COMPANY_NAME]
                               [--title TITLE] [--show]

Programmatic
------------

.. code-block:: python

    from qf_lib.dashboard import run_dashboard

    run_dashboard(
        output_dir="output/backtesting",
        port=8765,
        company_name="My Research Group",
    )

API Reference
-------------

.. currentmodule:: qf_lib.dashboard
.. autosummary::
    :nosignatures:
    :toctree: _autosummary

    server.run_dashboard
    runs.scan_runs
    runs.load_strategy_series
    runs.stats_rows
    runs.double_check
