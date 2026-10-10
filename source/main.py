"""CLI entry point.

    python main.py --bills test/bills --csv test/csv --out output
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from bill_decoder.config import Config
from bill_decoder.pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Utility Bill Decoder: generate level1.csv and level2.csv")
    parser.add_argument("--bills", type=Path, required=True, help="folder with bill images (<bill_id>.png/.jpg)")
    parser.add_argument("--csv", type=Path, required=True, help="folder with the level1.csv / level2.csv templates")
    parser.add_argument("--out", type=Path, default=Path("output"), help="where to write the completed CSV files")
    parser.add_argument("--no-cache", action="store_true", help="ignore and do not write the per-bill cache")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    run(args.bills, args.csv, args.out, Config.from_env(), use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
