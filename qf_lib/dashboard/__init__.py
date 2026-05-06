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
"""Web dashboard for browsing backtest runs.

Renders the same charts and statistics as the auto-generated PDF tearsheet
(:class:`~qf_lib.analysis.tearsheets.tearsheet_without_benchmark.TearsheetWithoutBenchmark`)
but as an interactive Plotly + NiceGUI page, with a list view across all
runs in a directory.

Quick start::

    python -m qf_lib.dashboard --output-dir ./output/backtesting

Optional dependencies must be installed first::

    pip install qf-lib[dashboard]

The dashboard does not produce any new artifacts. It reads the ``Timeseries.xlsx``
emitted by :class:`~qf_lib.backtesting.monitoring.backtest_monitor.BacktestMonitor`
under each ``output/backtesting/<timestamp> <name>/`` folder, and serves
PDF/CSV/Excel files that already exist in those folders as static downloads.
"""
from qf_lib.dashboard.server import run_dashboard

__all__ = ["run_dashboard"]
