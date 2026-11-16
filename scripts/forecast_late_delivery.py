"""Leakage-aware late-delivery forecast at order approval time.

Reads the existing MySQL warehouse and exports chronological evaluation evidence.
No warehouse tables are changed. A score is an investigation priority, not a
claim that a seller or carrier caused a late delivery.
"""

from __future__ import annotations

import getpass
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pymysql
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence/mysql/forecast_late_delivery"


def read(connection: pymysql.Connection, query: str) -> pd.DataFrame:
    with connection.cursor() as cursor:
        cursor.execute(query)
        return pd.DataFrame(cursor.fetchall(), columns=[c[0] for c in cursor.description])


def load_data(connection: pymysql.Connection) -> pd.DataFrame:
    orders = read(connection, """
        SELECT o.OrderId, o.IsOnTime, o.ItemCount, o.SellerCount,
               o.GMV, o.FreightValue, o.PaymentValue,
               s.order_purchase_timestamp PurchaseAt,
               s.order_approved_at ApprovedAt,
               s.order_delivered_carrier_date CarrierAt,
               s.order_delivered_customer_date DeliveredAt,
               s.order_estimated_delivery_date EstimatedAt,
               g.StateCode CustomerState
        FROM FactOrderDelivery o
        JOIN stg_Orders s ON s.order_id=o.OrderId
        JOIN DimCustomer c ON c.CustomerKey=o.CustomerKey
        JOIN DimGeography g ON g.GeographyKey=c.GeographyKey
        WHERE o.IsOnTime IS NOT NULL AND s.order_approved_at<>''
    """)
    items = read(connection, """
        SELECT i.OrderId, i.OrderItemId, i.Price, i.FreightValue ItemFreight,
               i.ShippingLimitDate,
               p.ProductWeightG, p.ProductLengthCm, p.ProductWidthCm,
               p.ProductHeightCm, cat.CategoryName, sg.StateCode SellerState
        FROM FactOrderItem i
        JOIN DimProduct p ON p.ProductKey=i.ProductKey
        JOIN DimCategory cat ON cat.CategoryKey=p.CategoryKey
        JOIN DimSeller seller ON seller.SellerKey=i.SellerKey
        JOIN DimGeography sg ON sg.GeographyKey=seller.GeographyKey
    """)
    payments = read(connection, """
        SELECT OrderId, PaymentType, Installments, PaymentValue
        FROM FactPayment
    """)
    for frame, columns in ((items, ["Price", "ItemFreight", "ProductWeightG",
                                    "ProductLengthCm", "ProductWidthCm", "ProductHeightCm"]),
                           (payments, ["Installments", "PaymentValue"])):
        for column in columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    items["VolumeCm3"] = (items.ProductLengthCm * items.ProductWidthCm *
                           items.ProductHeightCm)
    item_summary = items.groupby("OrderId").agg(
        WeightG=("ProductWeightG", "sum"), VolumeCm3=("VolumeCm3", "sum"),
    ).reset_index()
    primary_item = (items.sort_values(["OrderId", "Price", "OrderItemId"],
                                      ascending=[True, False, True])
                    .drop_duplicates("OrderId")
                    [["OrderId", "CategoryName", "SellerState", "ShippingLimitDate"]])
    payment_summary = (payments.sort_values(["OrderId", "PaymentValue"],
                                            ascending=[True, False])
                       .drop_duplicates("OrderId")
                       [["OrderId", "PaymentType", "Installments"]])
    data = (orders.merge(item_summary, on="OrderId", how="left", validate="one_to_one")
            .merge(primary_item, on="OrderId", how="left", validate="one_to_one")
            .merge(payment_summary, on="OrderId", how="left", validate="one_to_one"))
    for column in ["PurchaseAt", "ApprovedAt", "CarrierAt", "DeliveredAt",
                   "EstimatedAt", "ShippingLimitDate"]:
        data[column] = pd.to_datetime(data[column], errors="coerce")
    data = data[data.PurchaseAt.notna() & data.ApprovedAt.notna() &
                data.DeliveredAt.notna() & data.EstimatedAt.notna()].copy()
    data = data[(data.ApprovedAt >= data.PurchaseAt) &
                (data.ApprovedAt <= data.DeliveredAt)].copy()
    data["Late"] = 1 - pd.to_numeric(data.IsOnTime).astype(int)
    for column in ["ItemCount", "SellerCount", "GMV", "FreightValue", "PaymentValue"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data["PromiseDays"] = (data.EstimatedAt - data.PurchaseAt).dt.total_seconds() / 86400
    data["ApprovalDays"] = (data.ApprovedAt - data.PurchaseAt).dt.total_seconds() / 86400
    data["Month"] = data.PurchaseAt.dt.month
    data["Weekday"] = data.PurchaseAt.dt.dayofweek
    data["PurchaseMonth"] = data.PurchaseAt.dt.to_period("M").astype(str)
    data["FreightShare"] = data.FreightValue / data.GMV.replace(0, np.nan)
    data["SameState"] = (data.CustomerState == data.SellerState).astype(int)
    return data


CATEGORICAL = ["CustomerState", "SellerState", "CategoryName", "PaymentType"]
NUMERIC = ["ItemCount", "SellerCount", "GMV", "FreightValue", "PaymentValue",
           "WeightG", "VolumeCm3", "Installments", "PromiseDays", "ApprovalDays",
           "Month", "Weekday", "FreightShare", "SameState"]
FEATURES = CATEGORICAL + NUMERIC


def make_pipeline(estimator, numeric=NUMERIC):
    prep = ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")),
                              ("scale", StandardScaler())]), numeric),
        ("category", Pipeline([("impute", SimpleImputer(strategy="constant",
                                                   fill_value="unknown")),
                               ("encode", OneHotEncoder(handle_unknown="ignore"))]),
         CATEGORICAL),
    ])
    return Pipeline([("prep", prep), ("model", estimator)])


def evaluate(y: pd.Series, risk: np.ndarray) -> dict:
    risk = np.clip(risk, 0, 1)
    k = max(1, int(np.ceil(len(y) * .10)))
    top = np.argsort(-risk)[:k]
    positives = int(y.sum())
    top_precision = float(y.iloc[top].mean())
    base_rate = float(y.mean())
    return {
        "Orders": len(y), "LateOrders": positives,
        "LateRate": base_rate,
        "AveragePrecision": float(average_precision_score(y, risk)),
        "APLift": float(average_precision_score(y, risk) / y.mean()),
        "ROCAUC": float(roc_auc_score(y, risk)),
        "Brier": float(brier_score_loss(y, risk)),
        "Top10Selected": k,
        "Top10LateFound": int(y.iloc[top].sum()),
        "Top10Precision": top_precision,
        "Top10Capture": float(y.iloc[top].sum() / positives),
        "Top10Lift": top_precision / base_rate,
    }


def run() -> None:
    password = os.environ.get("OLIST_MYSQL_PASSWORD")
    password_file = ROOT / ".mysql-password"
    if password is None and password_file.is_file():
        password = password_file.read_text(encoding="utf-8-sig").rstrip("\r\n")
    if password is None:
        password = getpass.getpass("MySQL password: ")
    connection = pymysql.connect(host="127.0.0.1", port=3306, user="root",
                                 password=password, database="olist_bi_group08",
                                 charset="utf8mb4")
    try:
        data = load_data(connection)
    finally:
        connection.close()
    # At 01-Apr-2018, only earlier orders whose outcomes have been observed
    # can train or validate a deployed model. March is an unused maturity gap.
    train = data[(data.PurchaseAt >= "2017-01-01") &
                 (data.PurchaseAt < "2018-01-01") &
                 (data.DeliveredAt < "2018-04-01")].copy()
    valid = data[(data.PurchaseAt >= "2018-01-01") &
                 (data.PurchaseAt < "2018-03-01") &
                 (data.DeliveredAt < "2018-04-01")].copy()
    test = data[(data.PurchaseAt >= "2018-04-01") &
                (data.PurchaseAt < "2018-09-01")].copy()
    assert not train.empty and not valid.empty and not test.empty
    assert train.DeliveredAt.max() < pd.Timestamp("2018-04-01")
    assert valid.DeliveredAt.max() < pd.Timestamp("2018-04-01")
    assert test.PurchaseAt.min() >= pd.Timestamp("2018-04-01")
    candidates = {
        "Logistic": LogisticRegression(max_iter=500, random_state=8),
        "RandomForest": RandomForestClassifier(n_estimators=120, max_depth=12,
                                                 min_samples_leaf=30,
                                                 n_jobs=-1, random_state=8),
    }
    fitted = {}
    validation_scores = {}
    for name, estimator in candidates.items():
        model = make_pipeline(estimator)
        model.fit(train[FEATURES], train.Late)
        prediction = model.predict_proba(valid[FEATURES])[:, 1]
        fitted[name] = model
        validation_scores[name] = evaluate(valid.Late, prediction)
        print(name, "validation AP", round(validation_scores[name]["AveragePrecision"], 4))
    selected = max(validation_scores, key=lambda name: validation_scores[name]["AveragePrecision"])
    model = fitted[selected]
    valid_risk = model.predict_proba(valid[FEATURES])[:, 1]
    test_risk = model.predict_proba(test[FEATURES])[:, 1]
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1)
    calibrator.fit(valid_risk, valid.Late)
    calibrated_risk = calibrator.predict(test_risk)
    rows = []
    for name, subset, risk in [
        ("PrevalenceOnly", test, np.repeat(float(train.Late.mean()), len(test))),
        (selected + "_Validation", valid, valid_risk),
        (selected + "_Raw", test, test_risk),
        (selected + "_Calibrated", test, calibrated_risk),
    ]:
        rows.append({"Model": name, "Window": "Jan-Feb2018" if subset is valid else
                     "Apr-Aug2018", **evaluate(subset.Late, risk)})
    # A retrospective random holdout provides a contrast, not a deployment score:
    # it lets training contain observations from after some test orders.
    random_pool = data[(data.PurchaseAt >= "2017-01-01") &
                       (data.PurchaseAt < "2018-09-01")]
    random_train, random_test = train_test_split(
        random_pool, test_size=.15, stratify=random_pool.Late, random_state=8)
    random_model = make_pipeline(LogisticRegression(max_iter=500, random_state=8))
    random_model.fit(random_train[FEATURES], random_train.Late)
    random_risk = random_model.predict_proba(random_test[FEATURES])[:, 1]
    rows.append({"Model": "Logistic_RandomHoldout", "Window": "Random15pct",
                 **evaluate(random_test.Late, random_risk)})
    metric = pd.DataFrame(rows)
    monthly = []
    # Use the raw score for ranking. Calibration is reported as a diagnostic;
    # it must not be adopted merely because it was fitted on validation data.
    test["Risk"] = test_risk
    for month, group in test.groupby("PurchaseMonth", sort=True):
        monthly.append({"Month": month, **evaluate(group.Late, group.Risk.to_numpy())})
    queue = test[["OrderId", "PurchaseAt", "ApprovedAt", "CarrierAt",
                  "DeliveredAt", "EstimatedAt",
                  "CustomerState", "SellerState",
                  "CategoryName", "Risk", "Late"]].sort_values("Risk", ascending=False)

    # At carrier handover, update the warning using timestamps known by then.
    # Single-item orders avoid assigning one carrier event to several sellers.
    handover = data[(data.ItemCount == 1) & data.CarrierAt.notna() &
                    (data.CarrierAt >= data.ApprovedAt) &
                    (data.CarrierAt <= data.DeliveredAt)].copy()
    handover["RemainingPromiseDays"] = (
        handover.EstimatedAt - handover.CarrierAt).dt.total_seconds() / 86400
    # The Olist promise is date-based (the estimated timestamp is midnight).
    # An actionable handover must occur on a calendar date before that date.
    handover["RemainingCalendarDays"] = (
        handover.EstimatedAt.dt.normalize() -
        handover.CarrierAt.dt.normalize()).dt.days
    handover["ApprovalToCarrierDays"] = (
        handover.CarrierAt - handover.ApprovedAt).dt.total_seconds() / 86400
    handover["CarrierAfterShippingLimitDays"] = (
        handover.CarrierAt - handover.ShippingLimitDate).dt.total_seconds() / 86400
    handover_numeric = NUMERIC + ["RemainingPromiseDays", "ApprovalToCarrierDays",
                                  "CarrierAfterShippingLimitDays"]
    handover_features = CATEGORICAL + handover_numeric
    handover_train = handover[handover.OrderId.isin(train.OrderId) &
                              (handover.CarrierAt < "2018-04-01")]
    handover_valid = handover[handover.OrderId.isin(valid.OrderId) &
                              (handover.CarrierAt < "2018-04-01")]
    handover_test = handover[handover.OrderId.isin(test.OrderId)].copy()
    handover_scores = {}
    handover_models = {}
    for name, estimator in {
        "Logistic": LogisticRegression(max_iter=500, random_state=8),
        "RandomForest": RandomForestClassifier(n_estimators=120, max_depth=12,
                                                 min_samples_leaf=30,
                                                 n_jobs=-1, random_state=8),
    }.items():
        m = make_pipeline(estimator, handover_numeric)
        m.fit(handover_train[handover_features], handover_train.Late)
        handover_models[name] = m
        handover_scores[name] = average_precision_score(
            handover_valid.Late,
            m.predict_proba(handover_valid[handover_features])[:, 1])
    handover_selected = max(handover_scores, key=handover_scores.get)
    handover_test["HandoverRisk"] = handover_models[handover_selected].predict_proba(
        handover_test[handover_features])[:, 1]
    handover_test = handover_test.merge(
        test[["OrderId", "Risk"]], on="OrderId", how="left", validate="one_to_one")
    same_cohort = pd.DataFrame([
        {"Stage": "AfterApproval", **evaluate(handover_test.Late,
                                                handover_test.Risk.to_numpy())},
        {"Stage": "AtCarrierHandover", **evaluate(handover_test.Late,
                                                   handover_test.HandoverRisk.to_numpy())},
    ])
    actionable_rows = []
    for label, subset in [
        ("BeforePromise", handover_test[handover_test.RemainingCalendarDays > 0]),
        ("AtLeast3DaysBeforePromise",
         handover_test[handover_test.RemainingCalendarDays >= 3]),
    ]:
        for stage, column in [("AfterApproval", "Risk"),
                              ("AtCarrierHandover", "HandoverRisk")]:
            actionable_rows.append({"Cohort": label, "Stage": stage,
                                    **evaluate(subset.Late, subset[column].to_numpy())})
    actionable = pd.DataFrame(actionable_rows)
    handover_queue = (handover_test[["OrderId", "PurchaseAt", "ApprovedAt",
                                     "CarrierAt", "DeliveredAt", "EstimatedAt",
                                     "CustomerState", "SellerState", "CategoryName",
                                     "RemainingPromiseDays", "RemainingCalendarDays",
                                     "Risk", "HandoverRisk", "Late"]]
                      .sort_values("HandoverRisk", ascending=False))
    OUT.mkdir(parents=True, exist_ok=True)
    metric.to_csv(OUT / "metrics.csv", index=False)
    pd.DataFrame(monthly).to_csv(OUT / "monthly_metrics.csv", index=False)
    queue.to_csv(OUT / "test_risk_queue.csv", index=False)
    same_cohort.to_csv(OUT / "two_stage_comparison.csv", index=False)
    actionable.to_csv(OUT / "actionable_comparison.csv", index=False)
    handover_queue.to_csv(OUT / "handover_risk_queue.csv", index=False)
    print("selected:", selected, "train/valid/test:", len(train), len(valid), len(test))
    print(metric.round(4).to_string(index=False))
    print(pd.DataFrame(monthly).round(4).to_string(index=False))
    print("handover selected:", handover_selected,
          "train/valid/test:", len(handover_train), len(handover_valid), len(handover_test))
    print(same_cohort.round(4).to_string(index=False))
    print(actionable.round(4).to_string(index=False))
    print("evidence:", OUT)


if __name__ == "__main__":
    run()
