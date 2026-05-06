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
"""CLI entry point for the dashboard.

    python -m qf_lib.dashboard --output-dir ./output/backtesting --port 8765
"""
import argparse
from pathlib import Path

from qf_lib.dashboard.server import run_dashboard


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="qf_lib.dashboard",
        description="Browse qf-lib backtest output as an interactive web dashboard.",
    )
    parser.add_argument(
        "--output-dir", required=True, type=Path,
        help="Directory containing one folder per backtest run "
             "(usually the 'backtesting' folder under the project's output_directory).",
    )
    parser.add_argument("--port", type=int, default=8765, help="Listening port (default: 8765)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--company-name", default="QF-Lib",
                        help="Header label shown above each strategy name")
    parser.add_argument("--title", default="QF-Lib Backtest Dashboard",
                        help="Browser tab title and home heading")
    parser.add_argument("--show", action="store_true",
                        help="Open a browser window automatically on startup")
    args = parser.parse_args()

    run_dashboard(
        output_dir=args.output_dir,
        port=args.port,
        host=args.host,
        company_name=args.company_name,
        title=args.title,
        show=args.show,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
