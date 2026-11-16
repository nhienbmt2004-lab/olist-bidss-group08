"""Rebuild report EDA charts and source tables from the existing MySQL warehouse.

Usage: python scripts/run_mysql_eda.py
Credentials: OLIST_MYSQL_PASSWORD or the ignored .mysql-password file.
The script only reads MySQL. It writes figures and CSV evidence in this repo.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import pymysql

from eda_bq_additions import run_bq_eda


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "notebooks" / "eda_output"
EVIDENCE_DIR = ROOT / "docs" / "evidence" / "mysql" / "eda"
SCHEMA = "olist_bi_group08"
STAGING = {
    "Customers": "stg_Customers",
    "Geolocation": "stg_Geolocation",
    "Orders": "stg_Orders",
    "OrderItems": "stg_OrderItems",
    "Payments": "stg_Payments",
    "Reviews": "stg_Reviews",
    "Products": "stg_Products",
    "Sellers": "stg_Sellers",
    "CategoryTranslation": "stg_CategoryTranslation",
}


def frame(connection, sql: str) -> pd.DataFrame:
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])


def save_table(table: pd.DataFrame, name: str) -> None:
    table.to_csv(EVIDENCE_DIR / name, index=False, encoding="utf-8-sig")


def save_chart(name: str) -> None:
    plt.tight_layout()
    plt.savefig(FIG_DIR / name, dpi=240, bbox_inches="tight")
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--schema", default=SCHEMA)
    args = parser.parse_args()

    password = os.environ.get("OLIST_MYSQL_PASSWORD")
    secret_file = ROOT / ".mysql-password"
    if password is None and secret_file.is_file():
        password = secret_file.read_text(encoding="utf-8-sig").rstrip("\r\n")
    if password is None:
        raise RuntimeError("Set OLIST_MYSQL_PASSWORD or create .mysql-password")

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.facecolor": "white", "axes.spines.top": False,
                         "axes.spines.right": False, "font.size": 10})
    connection = pymysql.connect(
        host=args.host, port=args.port, user=args.user, password=password,
        database=args.schema, charset="utf8mb4", connect_timeout=10,
        cursorclass=pymysql.cursors.Cursor, read_timeout=90,
    )
    try:
        inventory = pd.DataFrame([
            {"source_table": name, "mysql_table": table,
             "rows": int(frame(connection, f"SELECT COUNT(*) AS n FROM `{table}`").iloc[0, 0])}
            for name, table in STAGING.items()
        ])
        save_table(inventory, "source_inventory.csv")

        status = frame(connection, """
            SELECT order_status, COUNT(*) AS order_count
            FROM stg_Orders GROUP BY order_status ORDER BY order_count DESC
        """)
        status["percentage"] = status.order_count / status.order_count.sum() * 100
        save_table(status, "order_status.csv")
        plot_status = status.sort_values("percentage")
        plt.figure(figsize=(9, 5))
        plt.barh(plot_status.order_status, plot_status.percentage, color="#5278AF")
        plt.xlabel("Share of all orders (%)")
        plt.title("Order status distribution, Olist history")
        plt.xlim(0, max(plot_status.percentage) * 1.12)
        for y, pct in enumerate(plot_status.percentage):
            plt.text(pct + .5, y, f"{pct:.2f}%", va="center")
        save_chart("order_status.png")

        monthly = frame(connection, """
            SELECT LEFT(order_purchase_timestamp, 7) AS purchase_month,
                   COUNT(DISTINCT order_id) AS order_count
            FROM stg_Orders WHERE order_purchase_timestamp <> ''
            GROUP BY LEFT(order_purchase_timestamp, 7)
            ORDER BY purchase_month
        """)
        save_table(monthly, "monthly_orders_all.csv")
        plot_monthly = monthly[monthly.purchase_month.between("2017-01", "2018-08")]
        plt.figure(figsize=(10, 5))
        plt.plot(plot_monthly.purchase_month, plot_monthly.order_count,
                 marker="o", markersize=3, color="#5278AF")
        plt.xticks(rotation=60, ha="right")
        plt.xlabel("Purchase month")
        plt.ylabel("Orders")
        plt.title("Monthly orders, Jan 2017–Aug 2018")
        save_chart("monthly_orders.png")

        delivery = frame(connection, """
            SELECT CASE WHEN IsOnTime=1 THEN 'On time' ELSE 'Late' END AS delivery_status,
                   COUNT(*) AS order_count
            FROM FactOrderDelivery WHERE IsOnTime IS NOT NULL
            GROUP BY IsOnTime ORDER BY IsOnTime DESC
        """)
        delivery["percentage"] = delivery.order_count / delivery.order_count.sum() * 100
        save_table(delivery, "delivery_status.csv")
        plt.figure(figsize=(7, 5))
        bars = plt.bar(delivery.delivery_status, delivery.percentage,
                       color=["#3F9E81", "#E59B59"])
        plt.ylabel("Share of eligible delivered orders (%)")
        plt.title("Delivery against promised date")
        plt.ylim(0, 100)
        for bar, pct in zip(bars, delivery.percentage):
            plt.text(bar.get_x() + bar.get_width() / 2, pct + 1,
                     f"{pct:.2f}%", ha="center")
        save_chart("delivery_status.png")

        review = frame(connection, """
            SELECT ReviewScore AS review_score, COUNT(*) AS review_count
            FROM OrderReviewLatest WHERE ReviewScore IS NOT NULL
            GROUP BY ReviewScore ORDER BY ReviewScore
        """)
        review["percentage"] = review.review_count / review.review_count.sum() * 100
        save_table(review, "review_score.csv")
        plt.figure(figsize=(7, 5))
        bars = plt.bar(review.review_score.astype(str), review.percentage,
                       color="#7394C2")
        plt.xlabel("Review score")
        plt.ylabel("Share of orders with a review (%)")
        plt.title("Latest review score per order")
        for bar, pct in zip(bars, review.percentage):
            plt.text(bar.get_x() + bar.get_width() / 2, pct + .4,
                     f"{pct:.2f}%", ha="center")
        save_chart("review_score.png")

        review_delivery = frame(connection, """
            SELECT CASE WHEN IsOnTime=1 THEN 'On time' ELSE 'Late' END AS delivery_status,
                   COUNT(*) AS reviewed_orders,
                   ROUND(AVG(ReviewScore), 3) AS avg_review_score,
                   ROUND(AVG(CASE WHEN ReviewScore<=2 THEN 1 ELSE 0 END), 5) AS low_review_rate
            FROM FactOrderDelivery
            WHERE IsOnTime IS NOT NULL AND ReviewScore IS NOT NULL
            GROUP BY IsOnTime ORDER BY IsOnTime DESC
        """)
        save_table(review_delivery, "review_by_delivery.csv")
        plt.figure(figsize=(7, 5))
        scores = review_delivery.avg_review_score.astype(float)
        bars = plt.bar(review_delivery.delivery_status, scores,
                       color=["#3F9E81", "#E59B59"])
        plt.ylabel("Average latest review score")
        plt.title("Review score by delivery status (association)")
        plt.ylim(0, 5)
        for bar, value in zip(bars, scores):
            plt.text(bar.get_x() + bar.get_width() / 2, value + .06,
                     f"{value:.2f}", ha="center")
        save_chart("delivery_review.png")

        order_level = frame(connection, """
            SELECT GMV, FreightValue, PaymentValue, ItemCount, SellerCount,
                   DeliveryDays, DelayDays, ReviewScore
            FROM FactOrderDelivery
        """)
        labels = ["GMV", "Freight", "Payment", "Item count", "Seller count",
                  "Delivery days", "Delay days", "Review score"]
        numeric = order_level.apply(pd.to_numeric, errors="coerce")
        correlation = numeric.corr(method="spearman")
        correlation.index = labels
        correlation.columns = labels
        correlation.to_csv(EVIDENCE_DIR / "correlation_spearman.csv",
                           encoding="utf-8-sig", float_format="%.5f")
        fig, ax = plt.subplots(figsize=(9, 7))
        image = ax.imshow(correlation, vmin=-1, vmax=1, cmap="coolwarm")
        ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
        ax.set_yticks(range(len(labels)), labels)
        for y in range(len(labels)):
            for x in range(len(labels)):
                ax.text(x, y, f"{correlation.iloc[y, x]:.2f}", ha="center", va="center")
        fig.colorbar(image, ax=ax, shrink=.8)
        ax.set_title("Spearman correlations at order grain")
        save_chart("correlation_heatmap.png")

        overview = frame(connection, """
            SELECT COUNT(*) AS orders,
                   SUM(CASE WHEN IsOnTime IS NOT NULL THEN 1 ELSE 0 END) AS eligible,
                   SUM(CASE WHEN IsOnTime=0 THEN 1 ELSE 0 END) AS late_orders,
                   ROUND(AVG(IsOnTime), 5) AS on_time_rate,
                   ROUND(SUM(GMV), 2) AS gmv
            FROM FactOrderDelivery
        """)
        save_table(overview, "eda_kpi_check.csv")
        assert int(overview.loc[0, "orders"]) == int(inventory.loc[inventory.source_table == "Orders", "rows"].iloc[0])
        assert int(overview.loc[0, "eligible"]) == int(delivery.order_count.sum())
        assert int(overview.loc[0, "late_orders"]) == int(delivery.loc[delivery.delivery_status == "Late", "order_count"].iloc[0])
        assert int(review_delivery.reviewed_orders.sum()) <= int(delivery.order_count.sum())
        bq_summary = run_bq_eda(connection, EVIDENCE_DIR, FIG_DIR)
        print(f"EDA done: {len(inventory)} source tables; BQ1–BQ5 analysis added")
        print(overview.to_string(index=False))
        print(review_delivery.to_string(index=False))
        print('BQ summary:', bq_summary)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
