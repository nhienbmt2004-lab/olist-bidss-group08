"""Read-only inventory of the project MySQL schema and its retained layers."""

from __future__ import annotations

import csv
import os
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence/mysql/schema_inventory.csv"
SCHEMA = "olist_bi_group08"


def role(name: str, kind: str) -> tuple[str, str]:
    n = name.lower()
    if kind == "VIEW":
        return "Serving view", "Power BI/DSS or micro-batch KPI"
    if n.startswith("stg_"):
        return "Source staging", "CSV fidelity, ETL, EDA and replay source"
    if (n.startswith("clean") or
            (n.startswith("order") and n.endswith("totals")) or
            n == "orderreviewlatest"):
        return "Clean/transform", "Materialized ETL intermediate and audit trail"
    if n.startswith("dim"):
        return "Dimension", "Star schema and Power BI model"
    if n.startswith("fact"):
        return "Fact", "Star schema, EDA, DSS and Power BI model"
    if n.startswith("etl") or n == "dataqualityissues":
        return "Audit", "Run log, source-target reconciliation and data quality"
    if n.startswith("demo"):
        if n == "demoactionlog":
            return "Simulated action audit", "Append-only decisions; scoped by replay run"
        return "Replay", "Historical micro-batch state and checkpoint"
    if n == "powerbiforecastmonthly":
        return "Forecast serving", "Power BI ForecastMonthly import partition"
    return "UNCLASSIFIED", "Review before any database deletion"


def main() -> None:
    password = os.environ.get("OLIST_MYSQL_PASSWORD")
    if password is None:
        password = (ROOT / ".mysql-password").read_text(encoding="utf-8-sig").rstrip("\r\n")
    con = pymysql.connect(host="127.0.0.1", port=3306, user="root",
                          password=password, database=SCHEMA, charset="utf8mb4")
    try:
        with con.cursor() as cur:
            cur.execute("""SELECT TABLE_NAME,TABLE_TYPE FROM information_schema.TABLES
                           WHERE TABLE_SCHEMA=%s ORDER BY TABLE_TYPE,TABLE_NAME""", (SCHEMA,))
            objects = cur.fetchall()
            rows = []
            for name, kind in objects:
                layer, use = role(name, kind)
                count = ""
                if kind == "BASE TABLE":
                    safe = name.replace("`", "``")
                    cur.execute(f"SELECT COUNT(*) FROM `{safe}`")
                    count = cur.fetchone()[0]
                rows.append((name, kind, layer, count, use))
    finally:
        con.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(("ObjectName", "ObjectType", "Role", "ExactRowCount", "UsedFor"))
        writer.writerows(rows)
    unexpected = [name for name, _, layer, _, _ in rows if layer == "UNCLASSIFIED"]
    print(f"{len(rows)} schema objects; {sum(k == 'BASE TABLE' for _, k, *_ in rows)} tables; "
          f"{sum(k == 'VIEW' for _, k, *_ in rows)} views; unclassified={unexpected}")
    print(OUT)
    if unexpected:
        raise SystemExit("Review unclassified schema objects before cleanup")


if __name__ == "__main__":
    main()
