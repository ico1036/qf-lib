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

import numpy as np
import pandas as pd

from qf_lib.containers.series.prices_series import PricesSeries


def _series(n: int = 504) -> PricesSeries:
    rng = np.random.default_rng(7)
    prices = 1_000_000.0 * np.cumprod(1.0 + rng.normal(0.0005, 0.012, n))
    idx = pd.bdate_range("2022-01-03", periods=n)
    s = PricesSeries(prices, index=idx)
    s.name = "TestStrategy"
    return s


class TestFigureBuilders(unittest.TestCase):
    """Smoke tests: every chart function must return a non-empty Plotly Figure."""

    def test_all_figure_builders_return_figures(self):
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

        builders = [
            fig_strategy_performance, fig_monthly_heatmap, fig_annual_returns,
            fig_returns_distribution, fig_qq, fig_rolling_stats,
            fig_cone, fig_quantiles, fig_underwater, fig_skewness,
        ]
        s = _series()
        for build in builders:
            with self.subTest(builder=build.__name__):
                fig = build(s)
                self.assertIsInstance(fig, Figure)
                self.assertTrue(fig.data, f"{build.__name__} produced no traces")
                self.assertTrue(fig.layout.title.text)


if __name__ == "__main__":
    unittest.main()
