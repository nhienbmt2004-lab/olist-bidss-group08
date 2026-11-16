"""Export order-grain checks for the Seller and Product Power BI visuals.

This is a read-only MySQL check. It cannot verify an unapplied PBIX change.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

import pymysql


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evidence" / "mysql" / "visual_checks"

SELLER_SQL = """
SELECT s.SellerId,
       COUNT(DISTINCT CASE WHEN o.IsOnTime IS NOT NULL THEN i.OrderId END) AS EligibleOrders,
       COUNT(DISTINCT CASE WHEN o.IsOnTime = 0 THEN i.OrderId END) AS LateOrders,
       ROUND(COUNT(DISTINCT CASE WHEN o.IsOnTime = 0 THEN i.OrderId END) /
             NULLIF(COUNT(DISTINCT CASE WHEN o.IsOnTime IS NOT NULL THEN i.OrderId END), 0), 4) AS LateRate,
       ROUND(SUM(i.Price), 2) AS GMV
FROM FactOrderItem i
JOIN FactOrderDelivery o ON o.OrderId = i.OrderId
JOIN DimSeller s ON s.SellerKey = i.SellerKey
GROUP BY s.SellerId
HAVING EligibleOrders >= 100
ORDER BY EligibleOrders DESC, s.SellerId
"""

CATEGORY_SQL = """
WITH item_sales AS (
    SELECT c.CategoryName, COUNT(*) AS Items, ROUND(SUM(i.Price), 2) AS GMV
    FROM FactOrderItem i
    JOIN DimProduct p ON p.ProductKey = i.ProductKey
    JOIN DimCategory c ON c.CategoryKey = p.CategoryKey
    GROUP BY c.CategoryName
), order_review AS (
    SELECT DISTINCT c.CategoryName, i.OrderId, o.ReviewScore
    FROM FactOrderItem i
    JOIN FactOrderDelivery o ON o.OrderId = i.OrderId
    JOIN DimProduct p ON p.ProductKey = i.ProductKey
    JOIN DimCategory c ON c.CategoryKey = p.CategoryKey
    WHERE o.ReviewScore IS NOT NULL
), category_review AS (
    SELECT CategoryName, COUNT(*) AS ReviewedOrders,
           ROUND(AVG(ReviewScore), 3) AS AvgReview
    FROM order_review GROUP BY CategoryName
)
SELECT s.CategoryName, s.Items, s.GMV, r.ReviewedOrders, r.AvgReview
FROM item_sales s
LEFT JOIN category_review r ON r.CategoryName = s.CategoryName
WHERE s.Items >= 100
ORDER BY s.GMV DESC, s.CategoryName
"""


def export(cursor, query: str, filename: str) -> list[tuple]:
    cursor.execute(query)
    rows = cursor.fetchall()
    with (OUT / filename).open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow([column[0] for column in cursor.description])
        writer.writerows(rows)
    return rows


def main() -> None:
    password = os.environ.get("OLIST_MYSQL_PASSWORD")
    secret = ROOT / ".mysql-password"
    if password is None and secret.is_file():
        password = secret.read_text(encoding="utf-8-sig").rstrip("\r\n")
    if password is None:
        raise RuntimeError("Set OLIST_MYSQL_PASSWORD or create .mysql-password")
    OUT.mkdir(parents=True, exist_ok=True)
    connection = pymysql.connect(
        host="127.0.0.1", port=3306, user="root", password=password,
        database="olist_bi_group08", charset="utf8mb4", connect_timeout=10,
        read_timeout=90,
    )
    try:
        with connection.cursor() as cursor:
            sellers = export(cursor, SELLER_SQL, "seller_late_rate.csv")
            categories = export(cursor, CATEGORY_SQL, "category_review.csv")
        seller_rates = [float(row[3]) for row in sellers if row[3] is not None]
        category_scores = [float(row[4]) for row in categories if row[4] is not None]
        assert seller_rates and min(seller_rates) < max(seller_rates)
        assert category_scores and min(category_scores) < max(category_scores)
        print(f"Seller groups (>=100 eligible): {len(sellers)}; late rate {min(seller_rates):.2%}–{max(seller_rates):.2%}")
        print(f"Category groups (>=100 items): {len(categories)}; review {min(category_scores):.3f}–{max(category_scores):.3f}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
