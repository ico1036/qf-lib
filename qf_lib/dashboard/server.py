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
"""NiceGUI server for the dashboard.

Two routes:

- ``/`` — list every backtest run found under ``output_dir``, with
  filterable columns of headline statistics.
- ``/run/<run_id>`` — drill into a single run, showing a CERN-style header,
  a sanity-check panel, ten Plotly charts mirroring the PDF tearsheet, and
  the full statistics table.

Artifact files (PDF, CSV, Excel, YAML) under each run folder are served
from ``/runs/<run_id>/<filename>`` as static downloads.
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

from nicegui import app, ui
from plotly.graph_objects import Figure

from qf_lib.dashboard.figures import (
    fig_annual_returns,
    fig_cone,
    fig_monthly_heatmap,
    fig_qq,
    fig_quantiles,
    fig_returns_distribution,
    fig_rolling_stats,
    fig_skewness,
    fig_strategy_performance,
    fig_underwater,
)
from qf_lib.dashboard.runs import double_check, load_strategy_series, scan_runs, stats_rows


_PAGE_CSS = """
<style>
  body{background:#f7f8fa;color:#0f172a;
       font-family:Inter,-apple-system,system-ui,'Segoe UI',Roboto,sans-serif;}
  .qf-card{background:#ffffff;border:1px solid #e5e7eb;border-radius:6px;padding:14px 18px;}
  .qf-section-h{font-size:11px;letter-spacing:0.10em;text-transform:uppercase;
                color:#475569;font-weight:600;
                border-bottom:1px solid #e5e7eb;padding-bottom:6px;margin-bottom:10px;}
  .qf-mono{font-family:ui-monospace,Menlo,Monaco,Consolas,monospace;font-size:12px;}
  .stats-table{width:100%;border-collapse:collapse;font-size:13px;}
  .stats-table th{text-align:left;padding:8px 14px;background:#f1f5f9;color:#334155;
                  font-weight:600;border-bottom:1px solid #cbd5e1;}
  .stats-table td{padding:7px 14px;border-bottom:1px solid #e5e7eb;}
  .stats-table td.value{text-align:right;font-variant-numeric:tabular-nums;}
  .stats-table tr:nth-child(odd) td{background:#fafbfc;}
  table.q-table thead th{background:#f1f5f9!important;color:#334155!important;font-weight:600;}
  table.q-table tbody tr:hover{background:#eff6ff!important;cursor:pointer;}
  .verify-row, .verify-head{display:grid;grid-template-columns:1fr 120px 120px 110px 70px;
                            gap:8px;padding:6px 0;}
  .verify-head{font-size:11px;letter-spacing:0.06em;text-transform:uppercase;
               color:#64748b;font-weight:600;border-bottom:1px solid #cbd5e1;}
  .verify-row{font-size:13px;border-bottom:1px dashed #e5e7eb;}
  .verify-row .num{text-align:right;font-variant-numeric:tabular-nums;
                   font-family:ui-monospace,Menlo,Monaco,monospace;}
  .verify-ok{color:#15803d;font-weight:600;}
  .verify-bad{color:#b91c1c;font-weight:600;}
</style>
"""


def _section(title: str):
    """Open a card-style section with an uppercase header."""
    container = ui.element("div").classes("qf-card w-full")
    with container:
        ui.label(title).classes("qf-section-h")
    return container


def _full(title: str, fig: Figure) -> None:
    """Render a single chart section that spans the full row."""
    with _section(title):
        ui.plotly(fig).classes("w-full")


def _pair(left_title: str, left_fig: Figure,
          right_title: str, right_fig: Figure) -> None:
    """Render two chart sections side-by-side."""
    with ui.row().classes("w-full gap-3"):
        with _section(left_title).classes("flex-1 min-w-0"):
            ui.plotly(left_fig).classes("w-full")
        with _section(right_title).classes("flex-1 min-w-0"):
            ui.plotly(right_fig).classes("w-full")


def run_dashboard(
    output_dir: Union[Path, str],
    port: int = 8765,
    host: str = "127.0.0.1",
    company_name: str = "QF-Lib",
    title: str = "QF-Lib Backtest Dashboard",
    show: bool = False,
) -> None:
    """Launch the dashboard (blocking).

    Parameters
    ----------
    output_dir
        Directory containing one folder per backtest run (the
        ``backtesting/`` folder produced by ``BacktestMonitor``).
    port
        Listening port.
    host
        Bind address.
    company_name
        Label rendered above each strategy name on the detail page,
        analogous to the PDF tearsheet's ``company_name`` setting.
    title
        Browser tab title and home heading.
    show
        Open the system browser automatically on startup.
    """
    output_dir = Path(output_dir).expanduser().resolve()

    @ui.page("/")
    def home() -> None:
        ui.add_head_html(_PAGE_CSS)
        with ui.column().classes("w-full max-w-screen-2xl mx-auto p-8 gap-4"):
            ui.label(title).classes("text-3xl font-semibold tracking-tight")
            ui.label("Click a row to drill into the same charts and statistics as the auto-generated PDF tearsheet."
                     ).classes("text-sm text-slate-500")

            rows = []
            for r in scan_runs(output_dir):
                row = dict(id=r["id"], name=r["name"], ts=r["ts_str"])
                try:
                    series = load_strategy_series(str(r["ts_xlsx"]), r["name"])
                    m = {label: f"{v} {u}".strip() for label, v, u in stats_rows(series)}
                    row.update(start=m["Start Date"], end=m["End Date"],
                               total=m["Total Return"], ann=m["Annualised Return"],
                               sharpe=m["Sharpe Ratio"], max_dd=m["Max Drawdown"],
                               skew=m["Skewness"])
                except Exception:
                    row.update(start="—", end="—", total="—", ann="—",
                               sharpe="—", max_dd="—", skew="—")
                rows.append(row)

            cols = [
                {"name": "name", "label": "Strategy", "field": "name", "align": "left", "sortable": True},
                {"name": "ts", "label": "Run", "field": "ts", "sortable": True},
                {"name": "start", "label": "Start", "field": "start"},
                {"name": "end", "label": "End", "field": "end"},
                {"name": "total", "label": "Total Return", "field": "total", "sortable": True},
                {"name": "ann", "label": "Annualised", "field": "ann", "sortable": True},
                {"name": "sharpe", "label": "Sharpe", "field": "sharpe", "sortable": True},
                {"name": "max_dd", "label": "Max DD", "field": "max_dd", "sortable": True},
                {"name": "skew", "label": "Skew", "field": "skew"},
            ]

            with ui.element("div").classes("qf-card w-full"):
                with ui.row().classes("w-full items-center gap-3 mb-2"):
                    ui.icon("query_stats").classes("text-slate-500")
                    ui.label(f"{len(rows)} backtest runs").classes("text-sm text-slate-600 font-medium")
                    search = ui.input(placeholder="Filter by strategy name...") \
                        .classes("ml-auto").props("dense outlined clearable")
                table = ui.table(columns=cols, rows=rows, row_key="id").classes("w-full")
                table.props('dense flat separator="horizontal"')
                table.bind_filter_from(search, "value")
                table.on("rowClick", lambda e: ui.navigate.to(f"/run/{e.args[1]['id']}"))

    @ui.page("/run/{run_id}")
    def detail(run_id: str) -> None:
        ui.add_head_html(_PAGE_CSS)
        with ui.column().classes("w-full max-w-screen-2xl mx-auto p-8 gap-3"):
            with ui.row().classes("w-full items-center gap-2"):
                ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props("flat round")
                ui.label("Backtests").classes("text-sm text-slate-500")
                ui.label("/").classes("text-sm text-slate-400")
                ui.label(run_id).classes("qf-mono text-sm text-slate-600")

            run = next((r for r in scan_runs(output_dir) if r["id"] == run_id), None)
            if run is None:
                ui.label("Run not found").classes("text-xl text-red-600")
                return

            series = load_strategy_series(str(run["ts_xlsx"]), run["name"])
            rows = stats_rows(series)
            rows_dict = {label: (value, unit) for label, value, unit in rows}

            # CERN-style header
            with ui.element("div").classes("qf-card w-full"):
                with ui.row().classes("w-full items-baseline justify-between"):
                    with ui.column().classes("gap-0"):
                        ui.label(company_name).classes(
                            "text-sm font-semibold tracking-wide text-slate-700")
                        ui.label(run["name"]).classes("text-2xl font-bold tracking-tight")
                        ui.label(f"{rows_dict['Start Date'][0]} – {rows_dict['End Date'][0]}  "
                                 f"·  {rows_dict['No. of daily samples'][0]} daily samples"
                                 ).classes("text-sm text-slate-500")
                    ui.label(f"Run {run['ts_str']}").classes("qf-mono text-xs text-slate-400")

            # Sanity check
            verify = double_check(series)
            with _section("Sanity check (Plotly chart series vs qf-lib TimeseriesAnalysis)"):
                ui.html(
                    "<div class='verify-head'>"
                    "<div>Metric</div><div class='num'>From qf-lib</div>"
                    "<div class='num'>From chart series</div><div class='num'>|Δ|</div>"
                    "<div class='num'>Match</div></div>"
                )
                for r in verify:
                    cls, tick = ("verify-ok", "✓") if r["ok"] else ("verify-bad", "✗")
                    ui.html(
                        f"<div class='verify-row'>"
                        f"<div>{r['label']}</div>"
                        f"<div class='num'>{r['pdf']}</div>"
                        f"<div class='num'>{r['chart']}</div>"
                        f"<div class='num'>{r['diff']}</div>"
                        f"<div class='num {cls}'>{tick}</div></div>"
                    )
                ok_count = sum(1 for r in verify if r["ok"])
                ui.label(f"{ok_count}/{len(verify)} metrics agree to within 0.01"
                         ).classes("text-xs mt-1 text-slate-500")

            # Charts (PDF order)
            _full("Strategy Performance", fig_strategy_performance(series))
            _pair("Monthly Returns",                fig_monthly_heatmap(series),
                  "Annual Returns",                 fig_annual_returns(series))
            _pair("Distribution of Monthly Returns", fig_returns_distribution(series),
                  "Normal Distribution Q-Q",        fig_qq(series))
            _full("Rolling Stats", fig_rolling_stats(series))
            _pair("Performance vs. Expectation",    fig_cone(series),
                  "Return Quantiles",               fig_quantiles(series))
            _pair("Drawdown",                       fig_underwater(series),
                  "Skewness",                       fig_skewness(series))

            # Statistics table (1:1 with PDF)
            with _section("Statistics"):
                html = ['<table class="stats-table">',
                        f'<thead><tr><th>Statistic</th><th class="value">{run["name"]}</th></tr></thead>',
                        "<tbody>"]
                for label, value, unit in rows:
                    full_label = f"{label} [{unit}]" if unit else label
                    html.append(f"<tr><td>{full_label}</td><td class=\"value\">{value}</td></tr>")
                html.append("</tbody></table>")
                ui.html("".join(html))

            # Artifact files
            with _section("Artifact Files"):
                for f in sorted(p for p in run["path"].iterdir() if p.is_file()):
                    icon = {".pdf": "picture_as_pdf", ".csv": "grid_on",
                            ".xlsx": "table_chart", ".yml": "settings"}.get(
                        f.suffix.lower(), "insert_drive_file")
                    with ui.row().classes("items-center gap-2"):
                        ui.icon(icon).classes("text-slate-500")
                        ui.link(f.name, f"/runs/{run_id}/{f.name}", new_tab=True).classes(
                            "qf-mono text-sm text-blue-700 hover:underline")
                        ui.label(f"{f.stat().st_size / 1024:,.0f} KB"
                                 ).classes("text-xs text-slate-400 ml-auto")

    app.add_static_files("/runs", str(output_dir))
    ui.run(title=title, port=port, host=host, reload=False, show=show)
