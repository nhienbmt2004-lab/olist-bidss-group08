"""Replay historical Olist order milestones into isolated MySQL demo tables.

The source is stg_Orders in the existing warehouse. EventAt remains the 2018
business clock; IngestedAtUtc records this simulation's actual load time.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import os
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pymysql


ROOT = Path(__file__).resolve().parents[1]
MILESTONES = (
    ("purchased", "order_purchase_timestamp"),
    ("approved", "order_approved_at"),
    ("carrier", "order_delivered_carrier_date"),
    ("delivered", "order_delivered_customer_date"),
)
SOURCE_COLUMNS = ("order_id", *(column for _, column in MILESTONES), "order_estimated_delivery_date")
EVENT_RANK = {name: rank for rank, (name, _) in enumerate(MILESTONES)}


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def read_password() -> str:
    password = os.environ.get("OLIST_MYSQL_PASSWORD")
    if password is not None:
        return password
    path = ROOT / ".mysql-password"
    if path.is_file():
        return path.read_text(encoding="utf-8-sig").rstrip("\r\n")
    if not sys.stdin.isatty():
        raise RuntimeError(f"MySQL credential file is missing: {path}")
    return getpass.getpass("MySQL password (hidden): ")


def connect(args):
    return pymysql.connect(
        host=args.host, port=args.port, user=args.user, password=read_password(),
        database=args.schema, charset="utf8mb4", connect_timeout=10,
        autocommit=False, local_infile=False,
    )


def parse_time(value):
    if value is None or not str(value).strip():
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).strip())


def prepare_events(source_rows, from_date: date, to_date: date):
    """Build event-time ordered rows and hash the exact selected source snapshot."""
    digest = hashlib.sha256(f"mysql-stg-orders|{from_date}|{to_date}|".encode())
    events = []
    skipped = Counter()
    seen = set()
    participating = 0
    for row in source_rows:
        order_id = row["order_id"]
        if not order_id or order_id in seen:
            raise ValueError("Selected stg_Orders contains a missing or duplicate order_id")
        seen.add(order_id)
        digest.update("\x1f".join(str(row.get(name) or "") for name in SOURCE_COLUMNS).encode())
        digest.update(b"\n")
        purchase = parse_time(row["order_purchase_timestamp"])
        if purchase is None or not from_date <= purchase.date() <= to_date:
            raise ValueError(f"Source date filter returned unexpected order {order_id}")
        estimated = parse_time(row["order_estimated_delivery_date"])
        delivered_at = parse_time(row["order_delivered_customer_date"])
        last_valid_at = purchase
        order_events = []
        for event_type, column in MILESTONES:
            event_at = parse_time(row[column])
            if event_at is None:
                continue
            if event_at < last_valid_at or (event_type == "carrier" and delivered_at and event_at > delivered_at):
                skipped[event_type] += 1
                continue
            order_events.append((order_id, event_type, event_at, purchase, estimated))
            last_valid_at = event_at
        if not any(event[1] == "delivered" for event in order_events):
            skipped["excluded_orders_no_valid_delivery"] += 1
            continue
        events.extend(order_events)
        participating += 1
    events.sort(key=lambda item: (item[2], item[0], EVENT_RANK[item[1]]))
    return events, digest.hexdigest(), skipped, participating


def load_source(cursor, from_date: date, to_date: date):
    columns = ",".join(f"`{name}`" for name in SOURCE_COLUMNS)
    cursor.execute(
        f"SELECT {columns} FROM stg_Orders "
        "WHERE order_purchase_timestamp >= %s AND order_purchase_timestamp < %s "
        "AND order_status='delivered' AND order_delivered_customer_date<>'' "
        "ORDER BY order_id",
        (str(from_date), str(to_date + timedelta(days=1))),
    )
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def initialize(cursor):
    sql = (ROOT / "sql/mysql/04_operational_replay.sql").read_text(encoding="utf-8")
    sql = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    for statement in sql.split(";"):
        if statement.strip():
            cursor.execute(statement)


def replay(connection, events, signature, batch_size, interval_seconds, max_batches, reset):
    cursor = connection.cursor()
    cursor.execute("SELECT GET_LOCK('olist_group08_demo_replay', 0)")
    if cursor.fetchone()[0] != 1:
        raise RuntimeError("Another Olist replay is already running")
    try:
        cursor.execute("SELECT SourceSignature, NextEventIndex, TotalEvents FROM DemoReplayCheckpoint WHERE Id=1")
        checkpoint = cursor.fetchone()
        if reset:
            cursor.execute("DELETE FROM DemoReplayBatch")
            cursor.execute("DELETE FROM DemoOrderEvent")
            cursor.execute("DELETE FROM DemoReplayCheckpoint")
            connection.commit()
            checkpoint = None
        if checkpoint:
            if checkpoint[0] != signature or checkpoint[2] != len(events):
                raise ValueError("Source snapshot or date window changed; run with --reset to restart the demo")
            offset = checkpoint[1]
        else:
            cursor.execute("SELECT COUNT(*) FROM DemoOrderEvent")
            if cursor.fetchone()[0]:
                raise ValueError("Demo events exist without a checkpoint; inspect and use --reset")
            cursor.execute(
                "INSERT INTO DemoReplayCheckpoint(Id,SourceSignature,NextEventIndex,TotalEvents) "
                "VALUES (1,%s,0,%s)", (signature, len(events)),
            )
            connection.commit()
            offset = 0
        if offset > len(events):
            raise ValueError("Checkpoint exceeds source event count")
        batches = 0
        while offset < len(events) and (max_batches is None or batches < max_batches):
            batch = events[offset:offset + batch_size]
            committed_at = utc_now()
            try:
                cursor.executemany(
                    "INSERT INTO DemoOrderEvent"
                    "(OrderId,EventType,EventAt,PurchaseAt,EstimatedAt,IngestedAtUtc) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    [(*event, committed_at) for event in batch],
                )
                cursor.execute(
                    "INSERT INTO DemoReplayBatch"
                    "(FirstEventIndex,EventCount,LastEventAt,CommittedAtUtc) VALUES (%s,%s,%s,%s)",
                    (offset, len(batch), batch[-1][2], committed_at),
                )
                offset += len(batch)
                cursor.execute(
                    "UPDATE DemoReplayCheckpoint SET NextEventIndex=%s,LastEventAt=%s,"
                    "LastBatchAtUtc=%s WHERE Id=1",
                    (offset, batch[-1][2], committed_at),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            batches += 1
            print(f"batch {batches}: +{len(batch)} events; {offset}/{len(events)}; "
                  f"source clock {batch[-1][2]}; loaded UTC {committed_at}", flush=True)
            if offset < len(events) and (max_batches is None or batches < max_batches):
                time.sleep(interval_seconds)
        return offset
    finally:
        cursor.execute("SELECT RELEASE_LOCK('olist_group08_demo_replay')")
        cursor.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--schema", default="olist_bi_group08")
    parser.add_argument("--from-date", type=date.fromisoformat, default=date(2018, 7, 1))
    parser.add_argument("--to-date", type=date.fromisoformat, default=date(2018, 7, 31))
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--interval-seconds", type=float, default=5)
    parser.add_argument("--max-batches", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--init-only", action="store_true")
    parser.add_argument("--reset", action="store_true", help="Clear only three Demo* tables before replay")
    args = parser.parse_args()
    if args.from_date > args.to_date or args.batch_size < 1 or args.interval_seconds < 0:
        parser.error("Invalid date range, batch size, or interval")
    if args.max_batches is not None and args.max_batches < 1:
        parser.error("--max-batches must be positive")
    connection = connect(args)
    try:
        cursor = connection.cursor()
        if not args.dry_run:
            initialize(cursor)
            connection.commit()
        if args.init_only:
            print("MySQL operational demo tables and views are ready")
            return
        source_rows = load_source(cursor, args.from_date, args.to_date)
        if not source_rows:
            raise ValueError("No stg_Orders in the selected purchase-date window")
        events, signature, skipped, order_count = prepare_events(source_rows, args.from_date, args.to_date)
        print(f"selected delivered source orders {len(source_rows)}; eligible replay orders {order_count}; "
              f"events {len(events)}; "
              f"skipped invalid milestones {dict(skipped)}; signature {signature[:12]}", flush=True)
        cursor.close()
        if not args.dry_run:
            replay(connection, events, signature, args.batch_size,
                   args.interval_seconds, args.max_batches, args.reset)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
