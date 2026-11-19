"""Export the nine preprocessed Olist source tables to individual CSV files."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "raw"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "csv"
SOURCE_FILES = (
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
)
DATE_COLUMNS = {
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
    "shipping_limit_date",
    "review_creation_date",
    "review_answer_timestamp",
}
def export_tables(source_dir: Path, output_dir: Path) -> int:
    source_dir = source_dir.resolve()
    output_dir = output_dir.resolve()
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in SOURCE_FILES:
        csv_path = source_dir / filename
        if not csv_path.is_file():
            raise FileNotFoundError(f"Missing source table: {csv_path}")
        frame = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
        # Match the notebook/ETL preprocessing: parse source timestamp columns,
        # keeping invalid or empty timestamps as blank values in Excel.
        for column in DATE_COLUMNS.intersection(frame.columns):
            frame[column] = pd.to_datetime(frame[column], errors="coerce")

        output_path = output_dir / f"{Path(filename).stem}.csv"
        frame.to_csv(output_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d %H:%M:%S")
        print(f"{output_path.name}: {len(frame):,} rows, {len(frame.columns)} columns")

    return len(SOURCE_FILES)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    count = export_tables(args.source_dir, args.output_dir)
    print(f"Exported {count} source tables to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
