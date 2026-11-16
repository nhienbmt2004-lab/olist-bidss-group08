"""Export aggregate MySQL ETL/KPI evidence for the Olist report."""

from __future__ import annotations

import argparse
import csv
import getpass
import os
import re
from pathlib import Path

import pymysql


ROOT = Path(__file__).resolve().parents[1]
QUERIES = {
    "etl_run": "SELECT RunId,StartedAtUtc,FinishedAtUtc,Status,ErrorMessage FROM ETLRun ORDER BY RunId DESC LIMIT 10",
    "etl_steps": "SELECT StepName,RowCount,FinishedAtUtc FROM ETLStepLog WHERE RunId=(SELECT MAX(RunId) FROM ETLRun) ORDER BY StepId",
    "reconciliation": "SELECT Metric,SourceValue,TargetValue,Difference,Passed FROM ETLReconciliation WHERE RunId=(SELECT MAX(RunId) FROM ETLRun) ORDER BY Metric",
    "data_quality": "SELECT IssueCode,IssueCount,Severity,Treatment FROM DataQualityIssues ORDER BY Severity,IssueCode",
    "overview": "SELECT * FROM vw_KPIOverview",
    "delivery_by_month_state": "SELECT * FROM vw_DeliveryByMonthState ORDER BY PurchaseMonth,CustomerState",
    "review_by_delivery": "SELECT * FROM vw_ReviewByDeliveryStatus ORDER BY DeliveryStatus",
    "seller_top20": "SELECT * FROM vw_SellerPerformance WHERE DeliveredOrders>=30 ORDER BY GMV DESC LIMIT 20",
}


def export(args) -> None:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", args.schema):
        raise ValueError("Invalid schema name")
    password = os.environ.get("OLIST_MYSQL_PASSWORD")
    password_file = ROOT / ".mysql-password"
    if password is None and password_file.is_file():
        password = password_file.read_text(encoding="utf-8-sig").rstrip("\r\n")
    if password is None:
        password = getpass.getpass("MySQL password (input hidden): ")
    connection = pymysql.connect(
        host=args.host, port=args.port, user=args.user, password=password,
        database=args.schema, connect_timeout=10, charset="utf8mb4",
    )
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        cursor = connection.cursor()
        for name, query in QUERIES.items():
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            path = output_dir / f"{name}.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(columns)
                writer.writerows(rows)
            print(f"{path}: {len(rows)} rows")
        cursor.close()
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--schema", default="olist_bi_group08")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/evidence/mysql")
    export(parser.parse_args())
