"""Pure as-of calculations for the Olist historical replay dashboard."""

from __future__ import annotations

import math

import pandas as pd


def geohash_encode(latitude: float, longitude: float, precision: int = 3) -> str:
    """Encode a coordinate locally; no external geocoding request is made."""
    alphabet = "0123456789bcdefghjkmnpqrstuvwxyz"
    lat_range, lon_range = [-90.0, 90.0], [-180.0, 180.0]
    bits, number, even, output = 0, 0, True, []
    while len(output) < precision:
        bounds, value = (lon_range, longitude) if even else (lat_range, latitude)
        midpoint = sum(bounds) / 2
        number = (number << 1) | int(value >= midpoint)
        bounds[0 if value >= midpoint else 1] = midpoint
        even = not even
        bits += 1
        if bits == 5:
            output.append(alphabet[number])
            bits, number = 0, 0
    return "".join(output)


def geohash_bounds(code: str) -> tuple[float, float, float, float]:
    """Return (south, west, north, east) for a local geohash cell."""
    alphabet = "0123456789bcdefghjkmnpqrstuvwxyz"
    lat_range, lon_range = [-90.0, 90.0], [-180.0, 180.0]
    even = True
    for letter in code:
        value = alphabet.index(letter)
        for bit in (16, 8, 4, 2, 1):
            bounds = lon_range if even else lat_range
            midpoint = sum(bounds) / 2
            bounds[0 if value & bit else 1] = midpoint
            even = not even
    return lat_range[0], lon_range[0], lat_range[1], lon_range[1]


def prepare_orders(events: pd.DataFrame, lookup: pd.DataFrame,
                   approval_scores: pd.DataFrame, handover_scores: pd.DataFrame,
                   sim_timestamp) -> pd.DataFrame:
    """One row per ingested order, with only its currently available score."""
    if events.empty or sim_timestamp is None:
        return pd.DataFrame()
    clock = pd.Timestamp(sim_timestamp)
    visible = events.copy()
    for column in ("PurchaseAt", "ApprovedAt", "CarrierAt", "DeliveredAt",
                   "EstimatedAt", "LastEventAt"):
        visible[column] = pd.to_datetime(visible[column], errors="coerce")
    if visible.OrderId.duplicated().any() or (visible.LastEventAt > clock).any():
        raise ValueError("Replay snapshot has duplicate or future order events")
    if lookup.OrderId.duplicated().any():
        raise ValueError("Route lookup must have one row per order")
    visible = visible.merge(lookup, on="OrderId", how="left", validate="one_to_one")
    visible["RouteId"] = visible.SellerState.fillna("?") + " → " + visible.CustomerState.fillna("?")
    visible["RouteEligible"] = (visible.SellerCount.eq(1) &
                                 visible.SellerState.notna() &
                                 visible.CustomerState.notna())
    # The CSVs contain eventual outcome columns; import only the stored scores.
    approval = approval_scores[["OrderId", "Risk"]].drop_duplicates("OrderId")
    handover = handover_scores[["OrderId", "HandoverRisk"]].drop_duplicates("OrderId")
    visible = visible.merge(approval, on="OrderId", how="left", validate="one_to_one")
    visible = visible.merge(handover, on="OrderId", how="left", validate="one_to_one")
    visible["AvailableScore"] = visible["Risk"]
    handed_over = visible.CarrierAt.notna() & visible.CarrierAt.le(clock)
    visible.loc[handed_over, "AvailableScore"] = visible.loc[handed_over, "HandoverRisk"]
    visible.loc[visible.ApprovedAt.isna(), "AvailableScore"] = math.nan
    visible["ScoreStage"] = "Chưa duyệt"
    visible.loc[visible.ApprovedAt.notna(), "ScoreStage"] = "Sau duyệt"
    visible.loc[handed_over, "ScoreStage"] = "Lúc bàn giao"
    visible["Open"] = visible.CurrentStage.ne("Delivered")
    visible["Overdue"] = (visible.Open & visible.EstimatedAt.notna() &
                          (clock.normalize() > visible.EstimatedAt.dt.normalize()))
    visible["DaysToPromise"] = (visible.EstimatedAt.dt.normalize() -
                                clock.normalize()).dt.days
    scored_open = visible.Open & visible.AvailableScore.notna()
    # A capacity assumption, not a calibrated probability threshold.
    ranked = visible.loc[scored_open, "AvailableScore"]
    cutoff = ranked.nlargest(max(1, math.ceil(len(ranked) * .10))).min() if len(ranked) else math.inf
    visible["RiskFlag"] = visible.Overdue | (scored_open & visible.AvailableScore.ge(cutoff))
    return visible


def route_metrics(orders: pd.DataFrame, sim_timestamp, min_delivered: int = 30,
                  historical: pd.DataFrame | None = None) -> pd.DataFrame:
    """Route OTD from as-of historical deliveries, open risk from replay orders."""
    columns = ["RouteId", "OrdersSeen", "Delivered14d", "OnTime14d", "OTD14d",
               "OpenOrders", "ScoredOpen", "OverdueOpen", "Overdue3Open",
               "OpenGMVAtRisk", "Color"]
    if orders.empty or sim_timestamp is None:
        return pd.DataFrame(columns=columns)
    clock = pd.Timestamp(sim_timestamp)
    eligible = orders[orders.RouteEligible].copy()
    if eligible.empty:
        return pd.DataFrame(columns=columns)
    eligible["FlaggedOpenGMV"] = pd.to_numeric(eligible.GMV, errors="coerce").fillna(0).where(
        eligible.Open & eligible.RiskFlag, 0)
    eligible["ScoredOpenFlag"] = eligible.Open & eligible.AvailableScore.notna()
    eligible["Overdue3Flag"] = eligible.Overdue & eligible.DaysToPromise.le(-3)
    result = eligible.groupby("RouteId", as_index=False).agg(
        OrdersSeen=("OrderId", "nunique"),
        OpenOrders=("Open", "sum"),
        ScoredOpen=("ScoredOpenFlag", "sum"),
        OverdueOpen=("Overdue", "sum"),
        Overdue3Open=("Overdue3Flag", "sum"),
        OpenGMVAtRisk=("FlaggedOpenGMV", "sum"),
    )
    source = eligible if historical is None else historical.copy()
    if not source.empty:
        source["DeliveredAt"] = pd.to_datetime(source.DeliveredAt, errors="coerce")
        source["EstimatedAt"] = pd.to_datetime(source.EstimatedAt, errors="coerce")
        if "RouteEligible" in source.columns:
            source = source[source.RouteEligible]
        recent = source[(source.DeliveredAt.notna() & source.EstimatedAt.notna() &
                         source.DeliveredAt.le(clock) &
                         source.DeliveredAt.gt(clock - pd.Timedelta(days=14)))].copy()
        recent["OnTime"] = recent.DeliveredAt.dt.normalize().le(
            recent.EstimatedAt.dt.normalize())
        by_route = recent.groupby("RouteId", as_index=False).agg(
            Delivered14d=("OrderId", "nunique"), OnTime14d=("OnTime", "sum"))
        result = result.merge(by_route, on="RouteId", how="left", validate="one_to_one")
    else:
        result["Delivered14d"] = 0
        result["OnTime14d"] = 0
    result[["Delivered14d", "OnTime14d"]] = result[["Delivered14d", "OnTime14d"]].fillna(0).astype(int)
    result["OTD14d"] = result.OnTime14d.div(result.Delivered14d.replace(0, math.nan))
    result["Color"] = "Xám"
    enough = result.Delivered14d.ge(min_delivered)
    result.loc[enough, "Color"] = "Xanh"
    result.loc[enough & (result.OTD14d.lt(.90) | result.Overdue3Open.ge(3)), "Color"] = "Vàng"
    result.loc[enough & result.OTD14d.lt(.85), "Color"] = "Đỏ"
    return result[columns].sort_values(["OrdersSeen", "RouteId"], ascending=[False, True])


def customer_geohash_points(orders: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the live replay queue by buyer geohash and alert severity."""
    columns = ["Geohash", "Latitude", "Longitude", "Orders",
               "RedOrders", "YellowOrders", "NormalOrders"]
    if orders.empty:
        return pd.DataFrame(columns=columns)
    source = orders.copy()
    # A route cell needs an unambiguous seller → buyer route. Exclude orders
    # with multiple sellers or missing state codes when that flag is available.
    if "RouteEligible" in source.columns:
        source = source[source.RouteEligible.fillna(False)]
    if "Alert" not in source.columns:
        source["Alert"] = "NORMAL"
    points = source[["OrderId", "CustomerLatitude", "CustomerLongitude", "Alert"]].dropna().copy()
    if points.empty:
        return pd.DataFrame(columns=columns)
    points = points[(points.CustomerLatitude.between(-34, 6)) &
                    (points.CustomerLongitude.between(-74, -34))]
    points["Alert"] = points.Alert.where(points.Alert.isin(["RED", "YELLOW", "NORMAL"]), "NORMAL")
    points["Geohash"] = [geohash_encode(lat, lon) for lat, lon in
                          zip(points.CustomerLatitude, points.CustomerLongitude)]
    points["RedOrders"] = points.Alert.eq("RED").astype(int)
    points["YellowOrders"] = points.Alert.eq("YELLOW").astype(int)
    points["NormalOrders"] = points.Alert.eq("NORMAL").astype(int)
    return points.groupby("Geohash", as_index=False).agg(
        Latitude=("CustomerLatitude", "mean"),
        Longitude=("CustomerLongitude", "mean"),
        Orders=("OrderId", "nunique"),
        RedOrders=("RedOrders", "sum"),
        YellowOrders=("YellowOrders", "sum"),
        NormalOrders=("NormalOrders", "sum"))[columns]
