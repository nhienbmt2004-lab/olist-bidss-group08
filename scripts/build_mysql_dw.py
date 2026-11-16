"""Build the Olist staging and dimensional warehouse in a dedicated MySQL schema.

The script never reads credentials from the repository or accepts a password on
the command line. Set OLIST_MYSQL_PASSWORD in the current shell or enter it at
the prompt. Existing non-empty schemas are left untouched by default.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pymysql


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = {
    "stg_Customers": "olist_customers_dataset.csv",
    "stg_Geolocation": "olist_geolocation_dataset.csv",
    "stg_Orders": "olist_orders_dataset.csv",
    "stg_OrderItems": "olist_order_items_dataset.csv",
    "stg_Payments": "olist_order_payments_dataset.csv",
    "stg_Reviews": "olist_order_reviews_dataset.csv",
    "stg_Products": "olist_products_dataset.csv",
    "stg_Sellers": "olist_sellers_dataset.csv",
    "stg_CategoryTranslation": "product_category_name_translation.csv",
}
DATE_COLUMNS = {
    "order_purchase_timestamp", "order_approved_at",
    "order_delivered_carrier_date", "order_delivered_customer_date",
    "order_estimated_delivery_date", "shipping_limit_date",
    "review_creation_date", "review_answer_timestamp",
}
SCHEMA_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def read_statements(path: Path) -> list[str]:
    """Split the project SQL files (which contain no procedures or quoted semicolons)."""
    return [statement.strip() for statement in path.read_text(encoding="utf-8").split(";")
            if statement.strip()]


def scalar(cursor, query: str):
    cursor.execute(query)
    return cursor.fetchone()[0]


def log_step(cursor, run_id: int, name: str, row_count: int | None = None) -> None:
    cursor.execute(
        "INSERT INTO ETLStepLog(RunId,StepName,RowCount,FinishedAtUtc)"
        " VALUES (%s,%s,%s,%s)",
        (run_id, name, row_count, utc_now()),
    )


def load_csv(cursor, table: str, path: Path, batch_size: int = 1000):
    first_date = last_date = None
    row_count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        if not header or len(header) != len(set(header)):
            raise ValueError(f"Invalid CSV header: {path}")
        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
        columns = [row[0] for row in cursor.fetchall()]
        if header != columns:
            raise ValueError(f"CSV header differs from {table}: {header} vs {columns}")
        names = ",".join(f"`{col}`" for col in header)
        placeholders = ",".join(["%s"] * len(header))
        statement = f"INSERT INTO `{table}` ({names}) VALUES ({placeholders})"
        batch = []
        for row in reader:
            if None in row:
                raise ValueError(f"Malformed CSV row in {path.name} near line {reader.line_num}")
            batch.append(tuple(row[col] for col in header))
            for col in DATE_COLUMNS.intersection(header):
                value = row[col][:10]
                if value:
                    parsed = date.fromisoformat(value)
                    first_date = parsed if first_date is None else min(first_date, parsed)
                    last_date = parsed if last_date is None else max(last_date, parsed)
            if len(batch) >= batch_size:
                cursor.executemany(statement, batch)
                row_count += len(batch)
                batch.clear()
        if batch:
            cursor.executemany(statement, batch)
            row_count += len(batch)
    return row_count, first_date, last_date


def load_date_dimension(cursor, first: date, last: date) -> int:
    if (last - first).days > 20000:
        raise ValueError("Date span exceeds 20,000 days; inspect source dates")
    values = []
    day = first
    while day <= last:
        values.append((int(day.strftime("%Y%m%d")), day, day.day, day.month,
                       (day.month - 1) // 3 + 1, day.year, day.isoweekday(),
                       int(day.isoweekday() >= 6)))
        day += timedelta(days=1)
    cursor.executemany(
        "INSERT INTO DimDate(DateKey,FullDate,DayNumber,MonthNumber,QuarterNumber,"
        "YearNumber,DayOfWeekNumber,IsWeekend) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        values,
    )
    return len(values)


def record_quality(cursor):
    checks = [
        ("DUPLICATE_ORDER_ID", "ERROR", "Reject duplicate order IDs", """
          SELECT COALESCE(SUM(n-1),0) FROM
          (SELECT COUNT(*) n FROM stg_Orders GROUP BY order_id HAVING COUNT(*)>1) x"""),
        ("ORDER_WITHOUT_CUSTOMER", "ERROR", "Reject orphan orders", """
          SELECT COUNT(*) FROM stg_Orders o LEFT JOIN stg_Customers c
          ON c.customer_id=o.customer_id WHERE c.customer_id IS NULL"""),
        ("DELIVERED_WITHOUT_DATE", "WARN", "Exclude from on-time denominator", """
          SELECT COUNT(*) FROM stg_Orders WHERE order_status='delivered'
          AND (order_delivered_customer_date='' OR order_estimated_delivery_date='')"""),
        ("NEGATIVE_APPROVAL_TO_CARRIER", "WARN", "Exclude from stage-duration summary", """
          SELECT COUNT(*) FROM stg_Orders WHERE order_approved_at<>''
          AND order_delivered_carrier_date<>''
          AND order_delivered_carrier_date<order_approved_at"""),
        ("NEGATIVE_CARRIER_TO_DELIVERY", "WARN", "Exclude from stage-duration summary", """
          SELECT COUNT(*) FROM stg_Orders WHERE order_delivered_carrier_date<>''
          AND order_delivered_customer_date<>''
          AND order_delivered_customer_date<order_delivered_carrier_date"""),
        ("ORDER_WITHOUT_REVIEW", "INFO", "Keep order; review metric omits null", """
          SELECT COUNT(*) FROM stg_Orders o LEFT JOIN stg_Reviews r
          ON r.order_id=o.order_id WHERE r.order_id IS NULL"""),
        ("MULTI_SELLER_ORDER", "INFO", "Do not infer seller caused order delay", """
          SELECT COUNT(*) FROM (SELECT order_id FROM stg_OrderItems
          GROUP BY order_id HAVING COUNT(DISTINCT seller_id)>1) x"""),
    ]
    for code, severity, treatment, query in checks:
        cursor.execute(query)
        count = int(cursor.fetchone()[0])
        cursor.execute(
            "INSERT INTO DataQualityIssues(IssueCode,IssueCount,Severity,Treatment)"
            " VALUES (%s,%s,%s,%s)", (code, count, severity, treatment),
        )
        if severity == "ERROR" and count:
            raise ValueError(f"Data quality gate failed: {code}={count}")


def reconcile(cursor, run_id: int) -> list[tuple[str, Decimal, Decimal, bool]]:
    pairs = [
        ("orders", "SELECT COUNT(*) FROM stg_Orders", "SELECT COUNT(*) FROM FactOrderDelivery"),
        ("items", "SELECT COUNT(*) FROM stg_OrderItems", "SELECT COUNT(*) FROM FactOrderItem"),
        ("payments", "SELECT COUNT(*) FROM stg_Payments", "SELECT COUNT(*) FROM FactPayment"),
        ("reviews", "SELECT COUNT(*) FROM stg_Reviews", "SELECT COUNT(*) FROM FactReview"),
        ("customers", "SELECT COUNT(*) FROM stg_Customers", "SELECT COUNT(*) FROM DimCustomer"),
        ("sellers", "SELECT COUNT(*) FROM stg_Sellers", "SELECT COUNT(*) FROM DimSeller"),
        ("products", "SELECT COUNT(*) FROM stg_Products", "SELECT COUNT(*) FROM DimProduct"),
        ("gmv", "SELECT COALESCE(SUM(CAST(price AS DECIMAL(18,2))),0) FROM stg_OrderItems",
         "SELECT COALESCE(SUM(Price),0) FROM FactOrderItem"),
        ("freight", "SELECT COALESCE(SUM(CAST(freight_value AS DECIMAL(18,2))),0) FROM stg_OrderItems",
         "SELECT COALESCE(SUM(FreightValue),0) FROM FactOrderItem"),
        ("payment_value", "SELECT COALESCE(SUM(CAST(payment_value AS DECIMAL(18,2))),0) FROM stg_Payments",
         "SELECT COALESCE(SUM(PaymentValue),0) FROM FactPayment"),
    ]
    results = []
    for name, source_sql, target_sql in pairs:
        source = Decimal(str(scalar(cursor, source_sql)))
        target = Decimal(str(scalar(cursor, target_sql)))
        difference = target - source
        passed = difference == 0
        cursor.execute(
            "INSERT INTO ETLReconciliation(RunId,Metric,SourceValue,TargetValue,Difference,Passed)"
            " VALUES (%s,%s,%s,%s,%s,%s)",
            (run_id, name, source, target, difference, int(passed)),
        )
        results.append((name, source, target, passed))
    return results


def build(args) -> None:
    raw_dir = args.raw_dir.resolve()
    for filename in MANIFEST.values():
        if not (raw_dir / filename).is_file():
            raise FileNotFoundError(raw_dir / filename)
    if not SCHEMA_NAME.fullmatch(args.schema):
        raise ValueError("Schema must contain letters, numbers and underscores")
    password = os.environ.get("OLIST_MYSQL_PASSWORD")
    password_file = ROOT / ".mysql-password"
    if password is None and password_file.is_file():
        password = password_file.read_text(encoding="utf-8-sig").rstrip("\r\n")
    if password is None:
        password = getpass.getpass("MySQL password (input hidden): ")
    connection = pymysql.connect(
        host=args.host, port=args.port, user=args.user,
        password=password, connect_timeout=10,
        charset="utf8mb4", use_unicode=True, local_infile=False,
    )
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s",
            (args.schema,),
        )
        if cursor.fetchone()[0]:
            raise RuntimeError(f"Schema {args.schema} already has tables; no existing data was changed")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{args.schema}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE `{args.schema}`")
        for statement in read_statements(ROOT / "sql/mysql/01_schema.sql"):
            cursor.execute(statement)
        connection.commit()
        cursor.execute(
            "INSERT INTO ETLRun(StartedAtUtc,Status,SourceDirectory) VALUES (%s,'RUNNING',%s)",
            (utc_now(), str(raw_dir)),
        )
        run_id = cursor.lastrowid
        connection.commit()
        first = last = None
        for table, filename in MANIFEST.items():
            count, low, high = load_csv(cursor, table, raw_dir / filename)
            log_step(cursor, run_id, f"load_{table}", count)
            connection.commit()
            if low is not None:
                first = low if first is None else min(first, low)
                last = high if last is None else max(last, high)
            print(f"Loaded {table}: {count:,}", flush=True)
        if first is None or last is None:
            raise ValueError("No valid dates in source data")
        count = load_date_dimension(cursor, first, last)
        log_step(cursor, run_id, "load_DimDate", count)
        connection.commit()
        print(f"Loaded DimDate: {count:,} ({first} to {last})", flush=True)
        record_quality(cursor)
        log_step(cursor, run_id, "data_quality", scalar(cursor, "SELECT COUNT(*) FROM DataQualityIssues"))
        connection.commit()
        for index, statement in enumerate(read_statements(ROOT / "sql/mysql/02_transform.sql"), start=1):
            cursor.execute(statement)
            log_step(cursor, run_id, f"transform_{index:02d}", max(cursor.rowcount, 0))
            connection.commit()
        for statement in read_statements(ROOT / "sql/mysql/03_views.sql"):
            cursor.execute(statement)
        connection.commit()
        rows = reconcile(cursor, run_id)
        log_step(cursor, run_id, "reconcile", len(rows))
        if not all(row[3] for row in rows):
            raise ValueError("Source-to-warehouse reconciliation failed")
        cursor.execute(
            "UPDATE ETLRun SET Status='SUCCEEDED',FinishedAtUtc=%s WHERE RunId=%s",
            (utc_now(), run_id),
        )
        connection.commit()
        for name, source, target, _ in rows:
            print(f"{name}: {source} = {target}")
        print(f"MySQL build complete: {args.host}:{args.port}/{args.schema}")
    except Exception as error:
        connection.rollback()
        try:
            cursor.execute(
                "UPDATE ETLRun SET Status='FAILED',FinishedAtUtc=%s,ErrorMessage=%s"
                " WHERE Status='RUNNING'", (utc_now(), str(error)[:1000]),
            )
            connection.commit()
        except pymysql.MySQLError:
            pass
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--schema", default="olist_bi_group08")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw")
    build(parser.parse_args())
