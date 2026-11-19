"""Export the exact Streamlit as-of views to CSV for review."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from streamlit_dss_core import geohash_encode
from streamlit_dss_data import historical_deliveries, route_lookup


ROOT = Path(__file__).resolve().parents[1]
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of-date", default="2018-03-15", help="Replay date YYYY-MM-DD")
    args = parser.parse_args()
    sim_date = pd.Timestamp(args.as_of_date).normalize()
    out_dir = ROOT / "output" / f"streamlit_{sim_date:%Y-%m-%d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    t = sim_date + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    start30 = sim_date - pd.Timedelta(days=29)

    history = historical_deliveries()
    lookup_cols = ["OrderId", "SellerState", "CustomerState", "CustomerLatitude", "CustomerLongitude"]
    history = history.merge(route_lookup()[lookup_cols], on="OrderId", how="left", validate="one_to_one")
    for col in ("PurchaseAt", "CarrierAt", "DeliveredAt", "EstimatedAt", "ShippingLimitAt"):
        history[col] = pd.to_datetime(history[col], errors="coerce")
    history["GMV"] = pd.to_numeric(history.GMV, errors="coerce").fillna(0.0)
    history["RouteEligible"] = (history.SellerCount.eq(1) & history.SellerState.notna() &
                                history.CustomerState.notna())
    history["RouteId"] = history.SellerState.fillna("?") + " → " + history.CustomerState.fillna("?")

    source_before_cancel_filter = history[history.PurchaseAt.le(t)].copy()
    canceled_asof = int(source_before_cancel_filter.OrderStatus.astype("string").str.lower().eq("canceled").sum())
    source = source_before_cancel_filter.copy()
    # Cancellation has no event timestamp in Olist. Exclude final canceled
    # records from operational queues; retain invoiced orders for review.
    if "OrderStatus" in source:
        source = source[source.OrderStatus.astype("string").str.lower().ne("canceled")]
    completed = source[source.DeliveredAt.notna() & source.DeliveredAt.le(t)].copy()
    # Match the app: the operational cohort is every order still undelivered
    # at T, not only orders already handed to the carrier.
    opened = source.loc[~source.OrderId.isin(completed.OrderId)].copy()
    opened.loc[opened.CarrierAt.gt(t), "CarrierAt"] = pd.NaT
    done30 = completed[completed.RouteEligible & completed.DeliveredAt.ge(start30) &
                       completed.EstimatedAt.notna()].copy()
    done30["Late"] = done30.DeliveredAt.dt.normalize().gt(done30.EstimatedAt.dt.normalize())
    done30["ActualDays"] = (done30.DeliveredAt - done30.PurchaseAt).dt.total_seconds() / 86400
    done30["PromiseDays"] = (done30.EstimatedAt - done30.PurchaseAt).dt.total_seconds() / 86400

    route_done = done30.groupby("RouteId", as_index=False).agg(
        Delivered30d=("OrderId", "nunique"), LateDelivered30d=("Late", "sum"),
        MeanActualDeliveryDays=("ActualDays", "mean"), MeanPromisedDays=("PromiseDays", "mean"),
        HistoricalLateGMV=("GMV", lambda s: float(s[done30.loc[s.index, "Late"]].sum())))
    route_done["OTD30d"] = 1 - route_done.LateDelivered30d / route_done.Delivered30d

    open_route = opened[opened.RouteEligible].copy()
    open_route["InTransit"] = open_route.CarrierAt.notna() & open_route.CarrierAt.le(t)
    open_route["DaysOverdue"] = (t.normalize() - open_route.EstimatedAt.dt.normalize()).dt.days.clip(lower=0).fillna(0)
    open_route["Delayed"] = open_route.DaysOverdue.gt(0)
    open_route["RescueEligible"] = open_route.DaysOverdue.ge(3)
    open_route["InTransitDelayed"] = open_route.InTransit & open_route.Delayed
    open_route["InTransitRescue"] = open_route.InTransit & open_route.RescueEligible
    open_route["RiskGMV"] = open_route.GMV.where(open_route.RescueEligible, 0.0)
    open_route["InTransitRiskGMV"] = open_route.GMV.where(open_route.InTransitRescue, 0.0)
    route_open = open_route.groupby("RouteId", as_index=False).agg(
        OpenOrders=("OrderId", "nunique"), DelayedOpenOrders=("Delayed", "sum"),
        InTransitOrders=("InTransit", "sum"),
        InTransitDelayedOrders=("InTransitDelayed", "sum"),
        InTransitRescueOrders3d=("InTransitRescue", "sum"),
        InTransitGMVAtRisk3d=("InTransitRiskGMV", "sum"),
        RescueOrders3d=("RescueEligible", "sum"), OpenGMV=("GMV", "sum"),
        OpenGMVAtRisk3d=("RiskGMV", "sum"))
    routes = route_done.merge(route_open, on="RouteId", how="outer").fillna(0)
    routes["OTD30d"] = (routes.Delivered30d - routes.LateDelivered30d).div(
        routes.Delivered30d.replace(0, pd.NA))
    routes["Status"] = "GRAY"
    enough = routes.Delivered30d.ge(30)
    routes.loc[enough & routes.OTD30d.ge(.90), "Status"] = "GREEN"
    routes.loc[enough & routes.OTD30d.ge(.85) & routes.OTD30d.lt(.90), "Status"] = "YELLOW"
    routes.loc[enough & routes.OTD30d.lt(.85), "Status"] = "RED"
    status_sort = routes.Status.map({"RED": 0, "YELLOW": 1, "GREEN": 2, "GRAY": 3})
    routes = routes.assign(_sort=status_sort).sort_values(
        ["_sort", "OpenGMVAtRisk3d", "Delivered30d"], ascending=[True, False, False]
    ).drop(columns="_sort").reset_index(drop=True)

    # Same initial route selection rule as the dashboard.
    default_route = routes.sort_values(["OpenGMVAtRisk3d", "Delivered30d"],
                                       ascending=[False, False]).iloc[0].RouteId
    default_origin = default_route.split(" → ", 1)[0]
    route_table = routes.copy()
    route_table.insert(0, "AsOfDate", sim_date.date().isoformat())
    route_table.to_csv(out_dir / "route_summary.csv", index=False, encoding="utf-8-sig")

    # Map cells locate customers; their fill color is the state-pair route OTD.
    map_orders = done30[done30.SellerState.eq(default_origin)].dropna(
        subset=["CustomerLatitude", "CustomerLongitude"]
    ).copy()
    map_orders["Geohash"] = [geohash_encode(lat, lon, precision=4) for lat, lon in
                             zip(map_orders.CustomerLatitude, map_orders.CustomerLongitude)]
    cells = map_orders.groupby("Geohash", as_index=False).agg(
        Latitude=("CustomerLatitude", "mean"), Longitude=("CustomerLongitude", "mean"),
        BuyerState=("CustomerState", lambda s: s.mode().iloc[0]),
        DeliveredOrdersInCell=("OrderId", "nunique"))
    state_region = {}
    state_region["TO"] = "Norte"
    state_region["RO"] = "Norte"
    state_region["AC"] = "Norte"
    state_region["PA"] = "Norte"
    state_region["AM"] = "Norte"
    state_region["AP"] = "Norte"
    state_region["RR"] = "Norte"
    state_region["PB"] = "Nordeste"
    state_region["PE"] = "Nordeste"
    state_region["RN"] = "Nordeste"
    state_region["MA"] = "Nordeste"
    state_region["CE"] = "Nordeste"
    state_region["PI"] = "Nordeste"
    state_region["BA"] = "Nordeste"
    state_region["AL"] = "Nordeste"
    state_region["SE"] = "Nordeste"
    state_region["MS"] = "Centro-Oeste"
    state_region["GO"] = "Centro-Oeste"
    state_region["MT"] = "Centro-Oeste"
    state_region["DF"] = "Centro-Oeste"
    state_region["ES"] = "Sudeste"
    state_region["SP"] = "Sudeste"
    state_region["MG"] = "Sudeste"
    state_region["RJ"] = "Sudeste"
    state_region["RS"] = "Sul"
    state_region["PR"] = "Sul"
    state_region["SC"] = "Sul"
    cells["BuyerRegion"] = cells.BuyerState.map(state_region).fillna("Unknown")
    pd.DataFrame([{"StateCode": state, "RegionName": region,
                   "Basis": "Derived from StateCode; DimGeography has no Region column"}
                  for state, region in state_region.items()]).sort_values("StateCode").to_csv(
        out_dir / "region_state_mapping.csv", index=False, encoding="utf-8-sig")
    cells["AsOfDate"] = sim_date.date().isoformat()
    cells["MapSellerState"] = default_origin
    cells["RouteId"] = cells.MapSellerState + " → " + cells.BuyerState
    cells = cells.merge(routes[["RouteId", "Delivered30d", "OTD30d", "Status"]],
                        on="RouteId", how="left")
    cells = cells.rename(columns={"Delivered30d": "RouteDelivered30d",
                                  "OTD30d": "RouteOTD30d", "Status": "RouteColor"})
    cells["Meaning"] = "Geohash chỉ là vị trí khách; màu lấy từ OTD tuyến, không tính OTD riêng cho ô"
    cells.to_csv(out_dir / "map_geohash_cells.csv", index=False, encoding="utf-8-sig")

    selected = open_route[open_route.RouteId.eq(default_route)].copy()
    selected["StageAtT"] = selected.CarrierAt.notna().map(
        {True: "Handed to carrier", False: "No handover timestamp"})
    selected["QueueColor"] = selected.DaysOverdue.map(
        lambda d: "RED (4+ days)" if d >= 4 else "ORANGE (3 days)" if d == 3 else "GREEN (<3 days late)")
    selected = selected.sort_values(["DaysOverdue", "GMV"], ascending=[False, False])
    selected[["OrderId", "RouteId", "SellerId", "CustomerState", "EstimatedAt",
              "DaysOverdue", "GMV", "QueueColor"]].to_csv(
        out_dir / "rescue_queue_selected_route.csv", index=False, encoding="utf-8-sig")

    delivered_selected = done30[done30.RouteId.eq(default_route)].copy()
    delivered_selected["LateOriginal"] = delivered_selected.DeliveredAt.dt.normalize().gt(
        delivered_selected.EstimatedAt.dt.normalize())
    baseline_late_gmv = float(delivered_selected.loc[delivered_selected.LateOriginal, "GMV"].sum())
    scenario_rows = []
    for days in (0, 3, 6, 9, 12):
        late = (delivered_selected.DeliveredAt - pd.to_timedelta(days, unit="D")).dt.normalize().gt(
            delivered_selected.EstimatedAt.dt.normalize())
        scenario_rows.append({"Scenario": "Delivery improvement", "AssumptionDays": days,
            "OTD": float((~late).mean()) if len(late) else None,
            "LateOrders": int(late.sum()), "LateGMV": float(delivered_selected.loc[late, "GMV"].sum()),
            "MeanActualDeliveryDays": float(delivered_selected.ActualDays.mean() - days) if len(late) else None,
            "ActualWaitChangedByAssumption": True})
    for days in (0, 2, 4, 6):
        late = delivered_selected.DeliveredAt.dt.normalize().gt(
            (delivered_selected.EstimatedAt + pd.to_timedelta(days, unit="D")).dt.normalize())
        scenario_rows.append({"Scenario": "Promise extension", "AssumptionDays": days,
            "OTD": float((~late).mean()) if len(late) else None,
            "LateOrders": int(late.sum()), "LateGMV": float(delivered_selected.loc[late, "GMV"].sum()),
            "MeanActualDeliveryDays": float(delivered_selected.ActualDays.mean()) if len(late) else None,
            "ActualWaitChangedByAssumption": False})
    scenarios = pd.DataFrame(scenario_rows)
    scenarios["AsOfDate"] = sim_date.date().isoformat()
    scenarios["SelectedRoute"] = default_route
    scenarios["BaselineLateGMV"] = baseline_late_gmv
    scenarios["Interpretation"] = "Arithmetic scenario on completed orders; not savings or causal impact"
    scenarios.to_csv(out_dir / "what_if_scenarios.csv", index=False, encoding="utf-8-sig")

    eligible_sellers = history[(history.OrderStatus.astype("string").str.lower().ne("canceled")) &
        (history.RouteEligible) & history.RouteId.eq(default_route) &
        history.SellerId.notna() & history.CarrierAt.notna() & history.CarrierAt.le(t) &
        history.ShippingLimitAt.notna()].copy()
    eligible_sellers["LateHandover"] = eligible_sellers.CarrierAt.gt(eligible_sellers.ShippingLimitAt)
    seller_table = eligible_sellers.groupby("SellerId", as_index=False).agg(
        Orders=("OrderId", "nunique"), LateHandoverOrders=("LateHandover", "sum"), GMV=("GMV", "sum"))
    seller_table["HandoverOnTimeRate"] = 1 - seller_table.LateHandoverOrders / seller_table.Orders
    seller_table["EligibleForComparison"] = seller_table.Orders.ge(30)
    seller_table["AsOfDate"] = sim_date.date().isoformat()
    seller_table["RouteId"] = default_route
    seller_table.to_csv(out_dir / "seller_handover_selected_route.csv", index=False, encoding="utf-8-sig")

    counts = pd.DataFrame([{
        "AsOfDate": sim_date.date().isoformat(), "SourceOrdersByDate": int(len(source)),
        "SourceOrdersAsOfIncludingCanceled": int(len(source_before_cancel_filter)),
        "CanceledExcludedAsOf": canceled_asof,
        "DeliveredAsOf": int(len(completed)), "OpenUndeliveredAsOf": int(len(opened)),
        "OpenInvoicedAsOf": int(opened.OrderStatus.astype("string").str.lower().eq("invoiced").sum()),
        "OpenAlreadyHandedToCarrierAsOf": int(opened.CarrierAt.notna().sum()),
        "OpenRouteEligible": int(open_route.OrderId.nunique()),
        "CompletedRouteEligible30d": int(done30.OrderId.nunique()),
        "DefaultSelectedRoute": default_route, "MapOriginState": default_origin,
        "MapGeohashCells": int(cells.Geohash.nunique()),
    }])
    counts.to_csv(out_dir / "backend_reconciliation.csv", index=False, encoding="utf-8-sig")
    print(f"Exported review CSVs to {out_dir.relative_to(ROOT)}; default route: {default_route.replace(' → ', ' -> ')}")


if __name__ == "__main__":
    main()
