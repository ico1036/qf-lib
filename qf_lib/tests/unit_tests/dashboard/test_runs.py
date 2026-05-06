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
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from qf_lib.containers.series.prices_series import PricesSeries


def _make_series(n: int = 504, name: str = "TestStrategy") -> PricesSeries:
    """Build a deterministic 2-year synthetic equity series for testing."""
    rng = np.random.default_rng(42)
    rets = rng.normal(loc=0.0005, scale=0.012, size=n)
    prices = 1_000_000.0 * np.cumprod(1.0 + rets)
    idx = pd.bdate_range("2022-01-03", periods=n)
    series = PricesSeries(prices, index=idx)
    series.name = name
    return series


def _write_timeseries(folder: Path, series: PricesSeries, ts_file: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    ts_path = folder / ts_file
    df = pd.DataFrame({series.name: series.values}, index=series.index)
    df.index.name = "Index"
    with pd.ExcelWriter(ts_path, engine="openpyxl") as writer:
        df.reset_index().to_excel(writer, sheet_name="Sheet", index=False)
    return ts_path


class TestScanRuns(unittest.TestCase):

    def test_returns_empty_for_missing_directory(self):
        from qf_lib.dashboard.runs import scan_runs
        self.assertEqual(scan_runs(Path("/nonexistent/path/xyz")), [])

    def test_returns_empty_for_empty_directory(self):
        from qf_lib.dashboard.runs import scan_runs
        with TemporaryDirectory() as tmp:
            self.assertEqual(scan_runs(Path(tmp)), [])

    def test_skips_directory_without_timeseries(self):
        from qf_lib.dashboard.runs import scan_runs
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "2024_01_01-1200 NoData").mkdir()
            self.assertEqual(scan_runs(Path(tmp)), [])

    def test_discovers_run_with_timeseries(self):
        from qf_lib.dashboard.runs import scan_runs
        with TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "2024_01_01-1200 MyStrategy"
            _write_timeseries(run_dir, _make_series(50), "TS Timeseries.xlsx")

            runs = scan_runs(Path(tmp))
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["id"], "2024_01_01-1200 MyStrategy")
            self.assertEqual(runs[0]["name"], "MyStrategy")
            self.assertEqual(runs[0]["ts_str"], "2024_01_01-1200")

    def test_returns_runs_newest_first(self):
        from qf_lib.dashboard.runs import scan_runs
        with TemporaryDirectory() as tmp:
            for ts in ("2023_06_01-0900 Old", "2024_06_01-0900 New"):
                _write_timeseries(Path(tmp) / ts, _make_series(20), f"{ts} Timeseries.xlsx")

            runs = scan_runs(Path(tmp))
            self.assertEqual(runs[0]["name"], "New")
            self.assertEqual(runs[1]["name"], "Old")


class TestStatsRows(unittest.TestCase):

    def test_returns_23_rows_in_pdf_order(self):
        from qf_lib.dashboard.runs import stats_rows
        rows = stats_rows(_make_series())
        self.assertEqual(len(rows), 23)

        labels = [label for label, _, _ in rows]
        self.assertEqual(labels[0], "Start Date")
        self.assertEqual(labels[1], "End Date")
        self.assertEqual(labels[2], "Total Return")
        self.assertEqual(labels[7], "Sharpe Ratio")
        self.assertEqual(labels[14], "Max Drawdown")
        self.assertEqual(labels[-1], "No. of daily samples")

    def test_units_present_for_percentage_metrics(self):
        from qf_lib.dashboard.runs import stats_rows
        units = {label: unit for label, _, unit in stats_rows(_make_series())}
        self.assertEqual(units["Total Return"], "%")
        self.assertEqual(units["Sharpe Ratio"], "")
        self.assertEqual(units["Avg Drawdown Duration"], "days")
        self.assertEqual(units["No. of daily samples"], "")


class TestDoubleCheck(unittest.TestCase):

    def test_six_metrics_agree_with_timeseries_analysis(self):
        from qf_lib.dashboard.runs import double_check
        result = double_check(_make_series())
        self.assertEqual(len(result), 6)
        for row in result:
            with self.subTest(label=row["label"]):
                self.assertTrue(row["ok"], msg=f"diff={row['diff']} for {row['label']}")


class TestLoadStrategySeries(unittest.TestCase):

    def test_round_trip_through_excel(self):
        from qf_lib.dashboard.runs import load_strategy_series
        original = _make_series(120, name="RoundTrip")
        with TemporaryDirectory() as tmp:
            ts_path = _write_timeseries(Path(tmp) / "run", original, "ts.xlsx")
            loaded = load_strategy_series(str(ts_path), "RoundTrip")

            self.assertEqual(loaded.name, "RoundTrip")
            self.assertEqual(len(loaded), len(original))
            np.testing.assert_allclose(loaded.values, original.values, rtol=1e-9)


if __name__ == "__main__":
    unittest.main()
