"""Continuously replay the March 2018 Olist cohort for the local dashboard.

Only the isolated Demo* tables are reset at the start of each cycle.
The Streamlit dashboard reads MySQL manually or every fifteen seconds when
the user enables auto-refresh.
"""

from __future__ import annotations

import argparse
import time
from datetime import date

from replay_olist_mysql import (
    connect,
    initialize,
    load_source,
    prepare_events,
    replay,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--schema", default="olist_bi_group08")
    parser.add_argument("--from-date", type=date.fromisoformat, default=date(2018, 3, 1))
    parser.add_argument("--to-date", type=date.fromisoformat, default=date(2018, 3, 31))
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--interval-seconds", type=float, default=5)
    parser.add_argument("--pause-seconds", type=float, default=20)
    parser.add_argument("--cycles", type=int, default=0,
                        help="0 repeats until stopped; positive number limits full cycles")
    args = parser.parse_args()
    if (args.from_date > args.to_date or args.batch_size < 1 or
            args.interval_seconds < 0 or args.pause_seconds < 0 or args.cycles < 0):
        parser.error("Invalid date, interval, pause, batch size, or cycle count")

    cycle = 0
    try:
        while args.cycles == 0 or cycle < args.cycles:
            cycle += 1
            connection = connect(args)
            try:
                with connection.cursor() as cursor:
                    initialize(cursor)
                    connection.commit()
                    rows = load_source(cursor, args.from_date, args.to_date)
                if not rows:
                    raise ValueError("No source orders in the selected date window")
                events, signature, skipped, order_count = prepare_events(
                    rows, args.from_date, args.to_date,
                )
                print(f"cycle {cycle}: {order_count} eligible orders, {len(events)} events, "
                      f"skipped={dict(skipped)}", flush=True)
                offset = replay(connection, events, signature, args.batch_size,
                                args.interval_seconds, None, reset=True)
                print(f"cycle {cycle} complete: {offset}/{len(events)} events", flush=True)
            finally:
                connection.close()
            if args.cycles == 0 or cycle < args.cycles:
                time.sleep(args.pause_seconds)
    except KeyboardInterrupt:
        print("Cycle runner stopped", flush=True)


if __name__ == "__main__":
    main()
