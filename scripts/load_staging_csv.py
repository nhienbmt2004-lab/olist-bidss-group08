"""Load the nine original Olist CSVs into the existing SQL Server staging tables.

Requires pyodbc and ODBC Driver 17 for SQL Server. Each table is replaced
transactionally, so a failed file does not leave a partially loaded table.
"""

import argparse
import csv
from decimal import Decimal
from pathlib import Path

import pyodbc


FILES = (
    ("Geolocation", "olist_geolocation_dataset.csv"),
    ("CategoryTranslation", "product_category_name_translation.csv"),
    ("Customers", "olist_customers_dataset.csv"),
    ("Sellers", "olist_sellers_dataset.csv"),
    ("Products", "olist_products_dataset.csv"),
    ("Orders", "olist_orders_dataset.csv"),
    ("OrderItems", "olist_order_items_dataset.csv"),
    ("Payments", "olist_order_payments_dataset.csv"),
    ("Reviews", "olist_order_reviews_dataset.csv"),
)


def load_file(connection, table, path, batch_size):
    cursor = connection.cursor()
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        if not columns or len(columns) != len(set(columns)):
            raise ValueError(f"Invalid CSV header: {path}")
        cursor.execute(
            "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME=? ORDER BY ORDINAL_POSITION",
            f"stg_{table}",
        )
        metadata = cursor.fetchall()
        actual = [row[0] for row in metadata]
        if columns != actual:
            raise ValueError(f"Header mismatch for stg_{table}: {columns} != {actual}")
        sql = (
            f"INSERT INTO dbo.[stg_{table}] ("
            + ",".join(f"[{name}]" for name in columns)
            + ") VALUES ("
            + ",".join("?" for _ in columns)
            + ")"
        )
        cursor.execute(f"TRUNCATE TABLE dbo.[stg_{table}]")
        cursor.fast_executemany = True
        cursor.setinputsizes([
            (pyodbc.SQL_WVARCHAR, 4000 if column[2] == -1 else column[2], 0)
            if column[1] in ("nvarchar", "varchar", "char", "nchar")
            else (pyodbc.SQL_DECIMAL, column[3], column[4])
            if column[1] in ("decimal", "numeric")
            else (pyodbc.SQL_INTEGER, 0, 0)
            for column in metadata
        ])
        count = 0
        batch = []
        def convert(value, column):
            if not value:
                return None
            data_type = column[1]
            if data_type in ("decimal", "numeric"):
                return Decimal(value).quantize(Decimal(1).scaleb(-column[4]))
            if data_type in ("int", "bigint", "smallint", "tinyint"):
                return int(value)
            return value

        for row in reader:
            if None in row:
                raise ValueError(f"Too many fields at CSV line {reader.line_num}: {path}")
            batch.append(tuple(convert(row[name], column) for name, column in zip(columns, metadata)))
            if len(batch) >= batch_size:
                cursor.executemany(sql, batch)
                count += len(batch)
                batch.clear()
        if batch:
            cursor.executemany(sql, batch)
            count += len(batch)
    connection.commit()
    print(f"stg_{table}: {count:,} rows", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_dir", type=Path)
    parser.add_argument("--server", default="localhost")
    parser.add_argument("--batch-size", type=int, default=2000)
    args = parser.parse_args()
    for _, name in FILES:
        if not (args.raw_dir / name).is_file():
            parser.error(f"Missing CSV: {args.raw_dir / name}")
    connection = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={args.server};DATABASE=Olist_Staging;"
        "Trusted_Connection=yes;TrustServerCertificate=yes;",
        autocommit=False,
    )
    try:
        for table, name in FILES:
            try:
                load_file(connection, table, args.raw_dir / name, args.batch_size)
            except Exception:
                connection.rollback()
                raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
