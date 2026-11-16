"""Generate DSS evidence from the MySQL warehouse, not from raw CSV files."""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pymysql


ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = {"review": 0.30, "otd": 0.25, "handover": 0.25,
           "avg_delay": 0.10, "cancel_rate": 0.10}
BOUNDS = {"review": (3.0, 4.5), "otd": (0.80, 0.97),
          "handover": (0.80, 0.97), "avg_delay": (14, 1),
          "cancel_rate": (0.02, 0.0)}


def read_table(connection, sql: str) -> pd.DataFrame:
    with connection.cursor() as cursor:
        cursor.execute(sql)
        columns = [item[0] for item in cursor.description]
        return pd.DataFrame(cursor.fetchall(), columns=columns)


def scale(values: pd.Series, lower: float, upper: float) -> pd.Series:
    return (100 * ((values - lower) / (upper - lower)).clip(0, 1)).fillna(0)


def seller_scorecard(connection) -> pd.DataFrame:
    sellers = read_table(connection, "SELECT * FROM vw_SellerPerformance")
    handover = read_table(connection, """
        SELECT i.SellerKey,
          AVG(CASE WHEN o.order_delivered_carrier_date<>'' AND i.ShippingLimitDate IS NOT NULL
              THEN CASE WHEN STR_TO_DATE(o.order_delivered_carrier_date,'%Y-%m-%d %H:%i:%s')<=i.ShippingLimitDate
                        THEN 1.0 ELSE 0.0 END END) AS HandoverProxy
        FROM FactOrderItem i JOIN stg_Orders o ON o.order_id=i.OrderId
        GROUP BY i.SellerKey
    """)
    risk = read_table(connection, """
        SELECT i.SellerKey,
          SUM(CASE WHEN f.IsOnTime=0 OR f.ReviewScore<=2 THEN i.Price ELSE 0 END) AS GMVAtRisk
        FROM FactOrderItem i JOIN FactOrderDelivery f ON f.OrderId=i.OrderId
        GROUP BY i.SellerKey
    """)
    data = sellers.merge(handover, on="SellerKey", how="left").merge(risk, on="SellerKey", how="left")
    for column in ("Orders", "DeliveredOrders", "CancelledOrders", "OnTimeRate",
                   "AvgReviewScore", "AvgLateDays", "GMV", "HandoverProxy", "GMVAtRisk"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data["CancelRate"] = data["CancelledOrders"] / data["Orders"]
    eligible = data[(data["DeliveredOrders"] >= 30) & data["OnTimeRate"].notna()
                    & data["AvgReviewScore"].notna() & data["HandoverProxy"].notna()].copy()
    score_inputs = {
        "review": eligible["AvgReviewScore"],
        "otd": eligible["OnTimeRate"],
        "handover": eligible["HandoverProxy"],
        "avg_delay": eligible["AvgLateDays"].fillna(0),
        "cancel_rate": eligible["CancelRate"].fillna(0),
    }
    eligible["SellerScore"] = sum(
        WEIGHTS[name] * scale(score_inputs[name], *BOUNDS[name])
        for name in WEIGHTS
    ).round(2)
    eligible["Grade"] = pd.cut(
        eligible["SellerScore"], [-np.inf, 50, 70, 85, np.inf],
        right=False, labels=["D", "C", "B", "A"],
    )
    eligible["SuggestedAction"] = eligible["Grade"].map({
        "A": "Maintain", "B": "Monitor", "C": "Investigate", "D": "Investigate first",
    })
    return eligible.sort_values(["SellerScore", "GMVAtRisk"], ascending=[True, False])


def alerts(connection) -> pd.DataFrame:
    data = read_table(connection, "SELECT * FROM vw_DeliveryByMonthState")
    for column in ("EligibleOrders", "LateOrders", "OnTimeRate"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    result = data[(data["EligibleOrders"] >= 100) & (data["OnTimeRate"] < 0.90)].copy()
    return result.sort_values(["OnTimeRate", "EligibleOrders"], ascending=[True, False])


def forecast_backtest(connection) -> pd.DataFrame:
    data = read_table(connection, """
        SELECT DATE_FORMAT(d.FullDate,'%Y-%m') AS PurchaseMonth,
               COUNT(*) AS Orders,SUM(f.GMV) AS GMV
        FROM FactOrderDelivery f JOIN DimDate d ON d.DateKey=f.PurchaseDateKey
        WHERE d.FullDate BETWEEN '2017-01-01' AND '2018-08-31'
        GROUP BY DATE_FORMAT(d.FullDate,'%Y-%m') ORDER BY PurchaseMonth
    """)
    if len(data) < 8:
        raise ValueError("At least eight monthly observations are required for backtest")
    rows = []
    for metric in ("Orders", "GMV"):
        series = pd.to_numeric(data[metric], errors="raise").to_numpy(dtype=float)
        train, test = series[:-3], series[-3:]
        methods = {
            "Naive": np.repeat(train[-1], len(test)),
            "Moving average 3": np.repeat(train[-3:].mean(), len(test)),
            "Linear trend": np.polyval(np.polyfit(np.arange(len(train)), train, 1),
                                       np.arange(len(train), len(series))),
        }
        for method, prediction in methods.items():
            rows.append({
                "Metric": metric, "Method": method,
                "MAE": round(float(np.mean(np.abs(test - prediction))), 2),
                "MAPEPercent": round(float(np.mean(np.abs(test - prediction) /
                                                     np.maximum(np.abs(test), 1)) * 100), 2),
                "TestMonths": ",".join(data["PurchaseMonth"].iloc[-3:]),
            })
    return pd.DataFrame(rows)


def what_if(connection) -> pd.DataFrame:
    groups = read_table(connection, "SELECT * FROM vw_ReviewByDeliveryStatus")
    groups = groups.set_index("DeliveryStatus")
    if not {"Late", "On time"}.issubset(groups.index):
        raise ValueError("Both late and on-time reviewed orders are required")
    late_n = float(groups.loc["Late", "ReviewedOrders"])
    on_n = float(groups.loc["On time", "ReviewedOrders"])
    late_review = float(groups.loc["Late", "AvgReviewScore"])
    on_review = float(groups.loc["On time", "AvgReviewScore"])
    total = late_n + on_n
    baseline = (late_n * late_review + on_n * on_review) / total
    gap = on_review - late_review
    late_rate = late_n / total
    overview = read_table(connection, "SELECT OnTimeRate FROM vw_KPIOverview")
    otd = float(overview.iloc[0]["OnTimeRate"])
    rows = []
    for delta_pp in (0, 1, 2, 3, 4, 5):
        rows.append({
            "DeltaLateRatePercentagePoints": delta_pp,
            "ScenarioOnTimeRatePercent": round(min(100, (otd + delta_pp / 100) * 100), 2),
            "ScenarioReviewScore": round(baseline + gap * min(delta_pp / 100, late_rate), 3),
            "Assumption": "Observed review gap held constant; not a causal estimate",
        })
    return pd.DataFrame(rows)


def run(args) -> None:
    password = os.environ.get("OLIST_MYSQL_PASSWORD")
    password_file = ROOT / ".mysql-password"
    if password is None and password_file.is_file():
        password = password_file.read_text(encoding="utf-8-sig").rstrip("\r\n")
    if password is None:
        password = getpass.getpass("MySQL password (input hidden): ")
    connection = pymysql.connect(
        host=args.host, port=args.port, user=args.user, password=password,
        database=args.schema, charset="utf8mb4", connect_timeout=10,
    )
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    try:
        outputs = {
            "seller_scorecard": seller_scorecard(connection),
            "delivery_alerts": alerts(connection),
            "forecast_backtest": forecast_backtest(connection),
            "what_if": what_if(connection),
        }
        for name, frame in outputs.items():
            path = output / f"{name}.csv"
            frame.to_csv(path, index=False, encoding="utf-8-sig")
            print(f"{path}: {len(frame)} rows")
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--schema", default="olist_bi_group08")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/evidence/mysql/dss")
    run(parser.parse_args())
