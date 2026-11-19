"""MySQL snapshot and append-only simulated action log for the DSS demo."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pymysql


ROOT = Path(__file__).resolve().parents[1]


def connect():
    password = os.environ.get("OLIST_MYSQL_PASSWORD")
    if password is None:
        path = ROOT / ".mysql-password"
        if not path.is_file():
            raise RuntimeError("Thiếu .mysql-password hoặc OLIST_MYSQL_PASSWORD")
        password = path.read_text(encoding="utf-8-sig").rstrip("\r\n")
    return pymysql.connect(host="127.0.0.1", port=3306, user="root",
        password=password, database="olist_bi_group08", charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor, connect_timeout=5,
        autocommit=False)


def route_lookup() -> pd.DataFrame:
    """FactOrderDelivery grain: exactly one row per order, including multi-item."""
    con = connect()
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT f.OrderId, MAX(f.GMV) AS GMV,
                       COUNT(DISTINCT i.SellerKey) AS SellerCount,
                       CASE WHEN COUNT(DISTINCT i.SellerKey)=1
                            THEN MAX(gs.StateCode) END AS SellerState,
                       CASE WHEN COUNT(DISTINCT i.SellerKey)=1
                            THEN MAX(gs.Latitude) END AS SellerLatitude,
                       CASE WHEN COUNT(DISTINCT i.SellerKey)=1
                            THEN MAX(gs.Longitude) END AS SellerLongitude,
                       CASE WHEN COUNT(DISTINCT i.SellerKey)=1
                            THEN MAX(s.SellerId) END AS SellerId,
                       MAX(gc.StateCode) AS CustomerState,
                       MAX(gc.Latitude) AS CustomerLatitude,
                       MAX(gc.Longitude) AS CustomerLongitude
                FROM FactOrderDelivery f
                JOIN DimCustomer c ON c.CustomerKey=f.CustomerKey
                LEFT JOIN DimGeography gc ON gc.GeographyKey=c.GeographyKey
                JOIN FactOrderItem i ON i.OrderId=f.OrderId
                JOIN DimSeller s ON s.SellerKey=i.SellerKey
                LEFT JOIN DimGeography gs ON gs.GeographyKey=s.GeographyKey
                GROUP BY f.OrderId
            """)
            return pd.DataFrame(cur.fetchall())
    finally:
        con.close()


def state_centroids() -> pd.DataFrame:
    """Approximate state centers from valid Olist geography coordinates."""
    con = connect()
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT StateCode, AVG(Latitude) AS Latitude, AVG(Longitude) AS Longitude
                FROM DimGeography
                WHERE StateCode IS NOT NULL
                  AND Latitude BETWEEN -34 AND 6
                  AND Longitude BETWEEN -74 AND -34
                GROUP BY StateCode
            """)
            return pd.DataFrame(cur.fetchall())
    finally:
        con.close()


def historical_deliveries() -> pd.DataFrame:
    """Order-grain historical delivery and handover context for as-of analysis."""
    con = connect()
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT o.order_id AS OrderId,
                       o.order_status AS OrderStatus,
                       NULLIF(o.order_purchase_timestamp,'') AS PurchaseAt,
                       NULLIF(o.order_approved_at,'') AS ApprovedAt,
                       NULLIF(o.order_delivered_carrier_date,'') AS CarrierAt,
                       NULLIF(o.order_delivered_customer_date,'') AS DeliveredAt,
                       NULLIF(o.order_estimated_delivery_date,'') AS EstimatedAt,
                       r.ReviewScore, r.ReviewAt,
                       i.SellerId, i.SellerCount, i.ShippingLimitAt, i.GMV
                FROM stg_Orders o
                LEFT JOIN (
                  SELECT order_id,
                         COUNT(DISTINCT seller_id) AS SellerCount,
                         CASE WHEN COUNT(DISTINCT seller_id)=1
                              THEN MAX(seller_id) END AS SellerId,
                         MIN(STR_TO_DATE(NULLIF(shipping_limit_date,''),
                                         '%Y-%m-%d %H:%i:%s')) AS ShippingLimitAt,
                         SUM(CAST(NULLIF(price,'') AS DECIMAL(18,2))) AS GMV
                  FROM stg_OrderItems
                  GROUP BY order_id
                ) i ON i.order_id=o.order_id
                LEFT JOIN (
                  SELECT order_id,
                         CAST(NULLIF(review_score,'') AS DECIMAL(4,2)) AS ReviewScore,
                         STR_TO_DATE(NULLIF(review_answer_timestamp,''),
                                     '%Y-%m-%d %H:%i:%s') AS ReviewAt
                  FROM (
                    SELECT order_id, review_score, review_answer_timestamp,
                           ROW_NUMBER() OVER (
                             PARTITION BY order_id
                             ORDER BY review_answer_timestamp DESC, review_id DESC
                           ) AS rn
                    FROM stg_Reviews
                  ) ranked_reviews
                  WHERE rn=1
                ) r ON r.order_id=o.order_id
            """)
            return pd.DataFrame(cur.fetchall())
    finally:
        con.close()


def forecast_rows() -> pd.DataFrame:
    """Read the already-published SES forecast used by Power BI, if available."""
    con = connect()
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT MonthStart, Metric, Actual, Forecast_SES, Lower95, Upper95,
                       Peak_Scenario, Alpha, K_peak, MAPE_Backtest_pct, `Set` AS DataSet
                FROM PowerBIForecastMonthly
                ORDER BY MonthStart, Metric
            """)
            return pd.DataFrame(cur.fetchall())
    finally:
        con.close()


def snapshot():
    """Read checkpoint, orders and KPI under one consistent MySQL transaction."""
    con = connect()
    try:
        with con.cursor() as cur:
            cur.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT")
            cur.execute("SELECT * FROM DemoReplayCheckpoint WHERE Id=1")
            checkpoint = cur.fetchone()
            if not checkpoint:
                return None, {}, pd.DataFrame(), None
            cur.execute("SELECT MIN(BatchId) AS ReplayRunId FROM DemoReplayBatch")
            run_id = cur.fetchone()["ReplayRunId"]
            cur.execute("SELECT * FROM vw_DemoOperationalKPI")
            kpi = cur.fetchone() or {}
            cur.execute("SELECT * FROM vw_DemoOrderCurrent")
            orders = pd.DataFrame(cur.fetchall())
            con.commit()
        return checkpoint, kpi, orders, run_id
    finally:
        con.close()


def replay_is_running() -> bool:
    """Whether the replay worker currently owns the MySQL advisory lock."""
    con = connect()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT IS_USED_LOCK('olist_group08_demo_replay') AS OwnerId")
            return cur.fetchone()["OwnerId"] is not None
    finally:
        con.close()


def ensure_action_log():
    con = connect()
    try:
        with con.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS DemoActionLog (
                  LogId BIGINT AUTO_INCREMENT PRIMARY KEY,
                  ReplayRunId BIGINT NOT NULL, EventIndex INT NOT NULL,
                  SimAt DATETIME NOT NULL, RecordedAtUtc DATETIME(6) NOT NULL,
                  RouteId VARCHAR(12) NOT NULL, SellerId CHAR(32),
                  UserRole VARCHAR(40) NOT NULL, ActionType VARCHAR(30) NOT NULL,
                  CommentText VARCHAR(500),
                  INDEX IX_DemoActionRunRoute (ReplayRunId,RouteId,LogId)
                ) ENGINE=InnoDB
            """)
        con.commit()
    finally:
        con.close()


def read_actions(run_id: int | None) -> pd.DataFrame:
    if run_id is None:
        return pd.DataFrame()
    con = connect()
    try:
        with con.cursor() as cur:
            cur.execute("""SELECT LogId,EventIndex,SimAt,RecordedAtUtc,RouteId,
                        SellerId,UserRole,ActionType,CommentText
                        FROM DemoActionLog WHERE ReplayRunId=%s
                        ORDER BY LogId DESC""", (run_id,))
            return pd.DataFrame(cur.fetchall())
    finally:
        con.close()


def write_action(expected_run_id: int, route_id: str, seller_id: str | None,
                 role: str, action: str, comment: str):
    """Log a demo decision only if the replay cycle has not rolled over."""
    if action == "CLOSE" and not comment.strip():
        raise ValueError("Đóng cảnh báo cần nêu lý do")
    con = connect()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT NextEventIndex,LastEventAt FROM DemoReplayCheckpoint WHERE Id=1 FOR UPDATE")
            checkpoint = cur.fetchone()
            cur.execute("SELECT MIN(BatchId) AS ReplayRunId FROM DemoReplayBatch")
            current_run_id = cur.fetchone()["ReplayRunId"]
            if (not checkpoint or not checkpoint["LastEventAt"] or
                    current_run_id != expected_run_id):
                raise ValueError("Lượt replay đã đổi; tải lại màn hình trước khi ghi")
            cur.execute("""INSERT INTO DemoActionLog
                (ReplayRunId,EventIndex,SimAt,RecordedAtUtc,RouteId,SellerId,
                 UserRole,ActionType,CommentText)
                VALUES (%s,%s,%s,UTC_TIMESTAMP(6),%s,%s,%s,%s,%s)""",
                (current_run_id, checkpoint["NextEventIndex"], checkpoint["LastEventAt"],
                 route_id, seller_id, role, action, comment.strip()[:500]))
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
