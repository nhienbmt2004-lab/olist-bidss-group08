"""Olist historical logistics control tower, rebuilt from the project PDFs."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import folium
    from branca.element import MacroElement, Template
    from streamlit_folium import st_folium
except ImportError:  # The install command in the project guide adds these packages.
    folium = None
    MacroElement = None
    Template = None
    st_folium = None

from streamlit_dss_core import geohash_bounds, geohash_encode
from streamlit_dss_data import historical_deliveries, route_lookup, state_centroids


ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "temp" / "streamlit_dss_actions.log"
FALLBACK_HISTORY_PATH = ROOT / "data" / "processed" / "streamlit_history_fallback.csv"
# Bản nén được commit lên GitHub để app chạy trên Streamlit Cloud (không có MySQL).
CLOUD_SNAPSHOT_PATH = ROOT / "data" / "streamlit" / "streamlit_history_fallback.csv.gz"


def snapshot_path() -> Path | None:
    """Ưu tiên snapshot cục bộ mới nhất, sau đó đến bản nén trên GitHub."""
    for path in (FALLBACK_HISTORY_PATH, CLOUD_SNAPSHOT_PATH):
        if path.is_file():
            return path
    return None
LOG_PATH.parent.mkdir(exist_ok=True)
logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

NAVY = "#123B5D"
BLUE = "#2789E8"
PALE = "#EAF5FC"
GREEN = "#16A36A"
YELLOW = "#F2B84B"
RED = "#E05252"
GRAY = "#94A3B8"
SIM_START = pd.Timestamp("2018-08-30")
SIM_END = pd.Timestamp("2018-08-31")
SIM_MIN_DATE = pd.Timestamp("2016-09-04")
SIM_CLOCK_CONFIG = "2018-08-30-v1"
MAP_GEOHASH_PRECISION = 3
BRAZIL_REGIONS = {
    "Norte": {"AC", "AP", "AM", "PA", "RO", "RR", "TO"},
    "Nordeste": {"AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"},
    "Centro-Oeste": {"DF", "GO", "MS", "MT"},
    "Sudeste": {"ES", "MG", "RJ", "SP"},
    "Sul": {"PR", "RS", "SC"},
}
REGION_COLORS = {
    "Norte": "#53A87F", "Nordeste": "#F1B84B",
    "Centro-Oeste": "#7E8FD2", "Sudeste": "#56A0D2",
    "Sul": "#AD7EC5",
}
st.set_page_config(page_title="RouteOps | Olist Replay", page_icon="🚚",
                   layout="wide", initial_sidebar_state="collapsed")
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root{{--navy:{NAVY};--blue:{BLUE};--pale:{PALE};--green:{GREEN};--yellow:{YELLOW};--red:{RED};--gray:{GRAY}}}
html,body,[class*="css"]{{font-family:Inter,'Segoe UI',sans-serif}}
.stApp{{background:linear-gradient(180deg,#f5faff 0,#fff 330px)}}
[data-testid="stMainBlockContainer"]{{max-width:1500px;padding-top:1rem}}
[data-testid="stHeader"]{{background:rgba(255,255,255,.88)}}
h1,h2,h3{{color:{NAVY};letter-spacing:-.025em}}
div[data-testid="stMetric"]{{background:#fff;border:1px solid #d9e8f4;border-radius:13px;
 padding:13px 16px;box-shadow:0 4px 14px #123b5d0b;min-height:92px}}
div[data-testid="stMetricLabel"]{{color:#52677c;font-weight:600}}
div[data-testid="stMetricValue"]{{color:{NAVY};font-weight:700}}
/* Keep full KPI explanations visible instead of truncating them with an ellipsis. */
div[data-testid="stMetricDelta"]{{white-space:normal!important;overflow:visible!important;
 text-overflow:clip!important;align-items:flex-start;line-height:1.25;max-width:100%}}
div[data-testid="stMetricDelta"] *{{white-space:normal!important;overflow:visible!important;
 text-overflow:clip!important;overflow-wrap:anywhere;line-height:1.25}}
.hero{{background:linear-gradient(110deg,{NAVY},{BLUE});color:white;border-radius:16px;
 padding:18px 24px;margin:0 0 16px;box-shadow:0 10px 24px #123b5d20}}
.hero h1{{color:white;margin:2px 0 5px;font-size:1.65rem}}
.hero p{{margin:0;color:#e4f2ff;font-size:.9rem}}
.eyebrow{{letter-spacing:.11em;text-transform:uppercase;font-size:.69rem;font-weight:700;color:#b9e0ff}}
.pill{{display:inline-block;border-radius:99px;padding:4px 10px;font-size:.76rem;font-weight:700}}
.stTabs [data-baseweb="tab-list"]{{gap:8px;border-bottom:1px solid #dce8f2}}
.stTabs [data-baseweb="tab"]{{font-weight:600;color:#52677c}}
.stTabs [aria-selected="true"]{{color:{NAVY}}}
div[data-testid="stDataFrame"]{{border:1px solid #e1eaf2;border-radius:11px;overflow:hidden}}
.stButton>button{{border-radius:9px;border-color:#cbdceb;font-weight:600}}
    .stButton>button[kind="primary"]{{background:{BLUE};border:0;color:white}}
div[data-testid="stMetricValue"]{{font-size:1.55rem}}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=1800, show_spinner="Đang đọc dữ liệu Olist từ MySQL...")
def get_history() -> pd.DataFrame:
    """Load MySQL history and refresh the local CSV fallback snapshot."""
    try:
        history = historical_deliveries()
        lookup = route_lookup()[["OrderId", "SellerState", "SellerLatitude",
                                "SellerLongitude", "CustomerState",
                                "CustomerLatitude", "CustomerLongitude"]]
        frame = history.merge(lookup, on="OrderId", how="left", validate="one_to_one")
        source = "MySQL"
    except Exception:
        path = snapshot_path()
        if path is None:
            raise
        logging.exception("MySQL unavailable; loading fallback snapshot %s", path)
        frame = pd.read_csv(path, low_memory=False)
        source = "CSV fallback"

    if "ReviewAt" not in frame:
        frame["ReviewAt"] = pd.NaT
    for column in ("PurchaseAt", "ApprovedAt", "CarrierAt", "DeliveredAt",
                   "EstimatedAt", "ShippingLimitAt", "ReviewAt"):
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    frame["GMV"] = pd.to_numeric(frame.GMV, errors="coerce").fillna(0.0)
    if "ReviewScore" in frame:
        frame["ReviewScore"] = pd.to_numeric(frame.ReviewScore, errors="coerce")
    else:
        frame["ReviewScore"] = pd.NA
    frame["SellerCount"] = pd.to_numeric(frame.SellerCount, errors="coerce").fillna(0).astype(int)
    frame["RouteEligible"] = (frame.SellerCount.eq(1) & frame.SellerState.notna() &
                              frame.CustomerState.notna())
    frame["RouteId"] = frame.SellerState.fillna("?") + " \u2192 " + frame.CustomerState.fillna("?")
    frame.attrs["data_source"] = source

    if source == "MySQL":
        try:
            FALLBACK_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(FALLBACK_HISTORY_PATH, index=False, date_format="%Y-%m-%d %H:%M:%S")
            CLOUD_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(CLOUD_SNAPSHOT_PATH, index=False, date_format="%Y-%m-%d %H:%M:%S",
                         compression={"method": "gzip", "mtime": 0})
        except OSError:
            logging.exception("Could not update local Streamlit fallback snapshot")
    return frame


@st.cache_data(ttl=3600, show_spinner=False)
def get_state_centroids() -> pd.DataFrame:
    try:
        return state_centroids()
    except Exception:
        path = snapshot_path()
        if path is None:
            raise
        logging.exception("MySQL geography unavailable; deriving map centers from fallback snapshot")
        history = pd.read_csv(path, low_memory=False)
        points = history[["CustomerState", "CustomerLatitude", "CustomerLongitude"]].copy()
        points["CustomerLatitude"] = pd.to_numeric(points.CustomerLatitude, errors="coerce")
        points["CustomerLongitude"] = pd.to_numeric(points.CustomerLongitude, errors="coerce")
        return (points.dropna().groupby("CustomerState", as_index=False)
                .agg(Latitude=("CustomerLatitude", "mean"),
                     Longitude=("CustomerLongitude", "mean"))
                .rename(columns={"CustomerState": "StateCode"}))


def convex_hull(points):
    """Approximate each Brazil macro-region from MySQL state centroids."""
    points = sorted(set((float(lon), float(lat)) for lat, lon in points))
    if len(points) <= 2:
        return points

    def cross(origin, a, b):
        return (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0])

    lower = []
    for point in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def init_clock() -> None:
    defaults = {"sim_date": SIM_START, "sim_last_tick": time.monotonic(),
                "sim_playing": False, "sim_speed": 1, "sim_actions": []}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if st.session_state.get("sim_clock_config") != SIM_CLOCK_CONFIG:
        st.session_state.sim_date = SIM_START
        st.session_state.sim_playing = False
        st.session_state.sim_last_tick = time.monotonic()
        st.session_state.sim_clock_config = SIM_CLOCK_CONFIG


def advance_clock() -> None:
    now = time.monotonic()
    last = st.session_state.get("sim_last_tick", now)
    step_seconds = 20 / max(1, int(st.session_state.get("sim_speed", 1)))
    if st.session_state.get("sim_playing", False):
        elapsed = max(0.0, now - last)
        days = int(elapsed // step_seconds)
        if days:
            st.session_state.sim_date = min(SIM_END, st.session_state.sim_date + pd.Timedelta(days=days))
            last += days * step_seconds
            if st.session_state.sim_date >= SIM_END:
                st.session_state.sim_playing = False
    st.session_state.sim_last_tick = last if st.session_state.get("sim_playing", False) else now


def asof_groups(history: pd.DataFrame, sim_date: pd.Timestamp):
    """Build completed and in-transit groups using timestamps visible by T."""
    t = pd.Timestamp(sim_date).normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    source = history[history.PurchaseAt.le(t)].copy()
    # Olist has no cancellation timestamp. Exclude orders whose final source
    # status is canceled from operational queues; keep invoiced orders because
    # they are valid created orders and may still be awaiting fulfillment.
    if "OrderStatus" in source:
        source = source[source.OrderStatus.astype("string").str.lower().ne("canceled")]
    completed = source[source.DeliveredAt.notna() & source.DeliveredAt.le(t)].copy()
    # The specification defines ongoing as every order not completed by T.
    # Keep orders still waiting for seller handover in this group as well.
    completed_ids = set(completed.OrderId)
    ongoing = source.loc[~source.OrderId.isin(completed_ids)].copy()
    # Remove future event timestamps from the snapshot after using DeliveredAt
    # only to determine whether an order had completed by T.
    for frame in (completed, ongoing):
        for column in ("ApprovedAt", "CarrierAt", "DeliveredAt"):
            frame.loc[frame[column].gt(t), column] = pd.NaT
    for frame in (completed, ongoing):
        frame["LateDays"] = (t.normalize() - frame.EstimatedAt.dt.normalize()).dt.days
    completed["IsLate"] = completed.DeliveredAt.dt.normalize().gt(
        completed.EstimatedAt.dt.normalize())
    ongoing["DelayDays"] = ongoing.LateDays.clip(lower=0).fillna(0).astype(int)
    ongoing["StageAtT"] = "Chưa có mốc bàn giao"
    handed_over = ongoing.CarrierAt.notna() & ongoing.CarrierAt.le(t)
    ongoing.loc[handed_over, "StageAtT"] = "\u0110ang v\u1eadn chuy\u1ec3n"
    return t, completed, ongoing


def route_rollup(completed: pd.DataFrame, ongoing: pd.DataFrame,
                 sim_date: pd.Timestamp, window_days: int = 30) -> pd.DataFrame:
    """Rolling route OTD and current overdue exposure, each at order grain."""
    start = sim_date.normalize() - pd.Timedelta(days=window_days - 1)
    # OTD needs both an observed delivery and an original promised date; keep
    # the route and marketplace denominators consistent when the promise date
    # is missing in the source data.
    done = completed[completed.RouteEligible & completed.DeliveredAt.ge(start) &
                     completed.EstimatedAt.notna()].copy()
    done["IsLate"] = done.DeliveredAt.dt.normalize().gt(done.EstimatedAt.dt.normalize())
    done["LateGMV"] = done.GMV.where(done.IsLate, 0.0)
    if not done.empty:
        done["ActualDays"] = (done.DeliveredAt - done.PurchaseAt).dt.total_seconds() / 86400
        done["PromisedDays"] = (done.EstimatedAt - done.PurchaseAt).dt.total_seconds() / 86400
        base = done.groupby("RouteId", as_index=False).agg(
            DeliveredN=("OrderId", "nunique"), LateDelivered=("IsLate", "sum"),
            ActualDays=("ActualDays", "mean"), PromisedDays=("PromisedDays", "mean"),
            LateGMV=("LateGMV", "sum"))
    else:
        base = pd.DataFrame(columns=["RouteId", "DeliveredN", "LateDelivered",
                                     "ActualDays", "PromisedDays", "LateGMV"])
    base["OTD"] = 1 - base.LateDelivered.div(base.DeliveredN.replace(0, pd.NA))

    opened = ongoing[ongoing.RouteEligible].copy()
    cutoff = sim_date.normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    opened["HandedOver"] = opened.CarrierAt.notna() & opened.CarrierAt.le(cutoff)
    opened["AtRisk"] = opened.DelayDays.ge(3)
    opened["RiskGMV"] = opened.GMV.where(opened.AtRisk, 0.0)
    opened["Delayed"] = opened.DelayDays.gt(0)
    opened["InTransitDelayed"] = opened.HandedOver & opened.Delayed
    opened["InTransitAtRisk"] = opened.HandedOver & opened.AtRisk
    opened["InTransitRiskGMV"] = opened.GMV.where(opened.InTransitAtRisk, 0.0)
    risk = opened.groupby("RouteId", as_index=False).agg(
        OpenN=("OrderId", "nunique"), DelayedN=("Delayed", "sum"),
        InTransitN=("HandedOver", "sum"),
        NoHandoverEventN=("HandedOver", lambda values: (~values).sum()),
        InTransitDelayedN=("InTransitDelayed", "sum"),
        InTransitRescueN=("InTransitAtRisk", "sum"),
        InTransitGMVAtRisk=("InTransitRiskGMV", "sum"),
        RescueN=("AtRisk", "sum"), OpenGMV=("GMV", "sum"),
        OpenGMVAtRisk=("RiskGMV", "sum"))
    result = base.merge(risk, on="RouteId", how="outer").fillna(0)
    numeric = ["DeliveredN", "LateDelivered", "ActualDays", "PromisedDays", "LateGMV", "OpenN",
               "DelayedN", "InTransitN", "NoHandoverEventN", "InTransitDelayedN",
               "InTransitRescueN", "InTransitGMVAtRisk", "RescueN", "OpenGMV",
               "OpenGMVAtRisk"]
    result[numeric] = result[numeric].apply(pd.to_numeric, errors="coerce").fillna(0)
    result["OTD"] = result.LateDelivered.rsub(result.DeliveredN).div(
        result.DeliveredN.replace(0, pd.NA))
    result["CurrentDelayPct"] = result.DelayedN.div(result.OpenN.replace(0, pd.NA))
    result["RiskPctOfOpenGMV"] = result.OpenGMVAtRisk.div(result.OpenGMV.replace(0, pd.NA))
    result["Status"] = "GRAY"
    enough = result.DeliveredN.ge(30)
    result.loc[enough & result.OTD.ge(.90), "Status"] = "GREEN"
    result.loc[enough & result.OTD.ge(.85) & result.OTD.lt(.90), "Status"] = "YELLOW"
    result.loc[enough & result.OTD.lt(.85), "Status"] = "RED"
    return result.sort_values(["Status", "OpenGMVAtRisk", "DeliveredN"],
                              ascending=[True, False, False]).reset_index(drop=True)


def seller_handover(history: pd.DataFrame, route: str, sim_date: pd.Timestamp) -> pd.DataFrame:
    """Seller responsibility ends at handover; never infer it from delivery delay."""
    cutoff = sim_date.normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    observed = history.copy()
    if "OrderStatus" in observed:
        observed = observed[observed.OrderStatus.astype("string").str.lower().ne("canceled")]
    for column in ("ApprovedAt", "CarrierAt", "DeliveredAt"):
        observed.loc[observed[column].gt(cutoff), column] = pd.NaT
    sellers = observed[(observed.PurchaseAt.le(cutoff)) & observed.RouteEligible &
                       observed.RouteId.eq(route) & observed.SellerId.notna() &
                       observed.CarrierAt.notna() & observed.CarrierAt.le(cutoff) &
                       observed.ShippingLimitAt.notna()].copy()
    if sellers.empty:
        return pd.DataFrame(columns=["SellerId", "Orders", "CompletedOrders", "LateHandoverN",
                                     "HandoverOnTimePct", "GMV"])
    sellers["LateHandover"] = sellers.CarrierAt.gt(sellers.ShippingLimitAt)
    sellers["CompletedOrderId"] = sellers.OrderId.where(
        sellers.DeliveredAt.notna() & sellers.DeliveredAt.le(cutoff))
    result = sellers.groupby("SellerId", as_index=False).agg(
        Orders=("OrderId", "nunique"), LateHandoverN=("LateHandover", "sum"),
        CompletedOrders=("CompletedOrderId", "nunique"), GMV=("GMV", "sum"))
    result["HandoverOnTimePct"] = 1 - result.LateHandoverN.div(result.Orders)
    return result.sort_values(["Orders", "HandoverOnTimePct"],
                              ascending=[False, True]).reset_index(drop=True)


def route_map(route_deliveries: pd.DataFrame, route_rollup: pd.DataFrame,
              seller_state: str, selected_geohash: str | None = None,
              selected_route: str | None = None):
    """Build an interactive Leaflet map; cell color always reflects route OTD."""
    if folium is None or st_folium is None:
        return None
    buyers = route_deliveries.dropna(
        subset=["CustomerLatitude", "CustomerLongitude", "CustomerState"]).copy()
    buyers = buyers[buyers.CustomerLatitude.between(-34, 6) &
                    buyers.CustomerLongitude.between(-74, -34)]
    if buyers.empty:
        return None

    # Precision 3 keeps the country-level grid readable; precision 4 makes labels overlap.
    buyers["Geohash"] = [
        geohash_encode(lat, lon, precision=MAP_GEOHASH_PRECISION)
        for lat, lon in zip(buyers.CustomerLatitude, buyers.CustomerLongitude)
    ]

    cell_rows = []
    for geohash, group in buyers.groupby("Geohash", sort=False):
        modes = group.CustomerState.mode()
        buyer_state = modes.iloc[0] if not modes.empty else group.CustomerState.iloc[0]
        route_rows = group[group.CustomerState.eq(buyer_state)]
        south, west, north, east = geohash_bounds(geohash)
        cell_rows.append({
            "Geohash": geohash,
            "Latitude": (south + north) / 2,
            "Longitude": (west + east) / 2,
            "BuyerState": buyer_state,
            "Orders": route_rows.OrderId.nunique(),
        })
    cells = pd.DataFrame(cell_rows)
    route_stats = route_rollup.set_index("RouteId")
    cells["RouteId"] = seller_state + " \u2192 " + cells.BuyerState
    cells["RouteStatus"] = cells.RouteId.map(route_stats.Status).fillna("GRAY")
    cells["RouteOTD"] = cells.RouteId.map(route_stats.OTD)
    cells["RouteN"] = cells.RouteId.map(route_stats.DeliveredN).fillna(0).astype(int)
    for metric in ("OpenN", "InTransitN", "DelayedN", "InTransitDelayedN",
                   "OpenGMVAtRisk", "InTransitGMVAtRisk"):
        cells[metric] = cells.RouteId.map(route_stats[metric]).fillna(0)

    fills = {"GREEN": "#54A879", "YELLOW": "#E9A94B",
             "RED": "#D96570", "GRAY": "#B8A5C9"}
    labels = {"GREEN": "OTD ≥ 90%", "YELLOW": "85% ≤ OTD < 90%",
              "RED": "OTD &lt; 85%", "GRAY": "Chưa đủ 30 đơn giao"}

    if selected_geohash and cells.Geohash.eq(selected_geohash).any():
        selected = cells[cells.Geohash.eq(selected_geohash)].iloc[0]
        center = [float(selected.Latitude), float(selected.Longitude)]
        zoom = 8
    else:
        center, zoom = [-12.5, -53.0], 4

    # Use the OSM map from the reference and mute it behind the route grid.
    fmap = folium.Map(location=center, zoom_start=zoom, tiles=None,
                      control_scale=False, prefer_canvas=True)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap",
                     opacity=0.72, show=True).add_to(fmap)
    folium.Element("""<style>
      .leaflet-control-attribution { font-size: 0 !important; }
      .leaflet-control-attribution a[href*="openstreetmap.org"] { font-size: 11px !important; }
      .leaflet-control-attribution a[href*="leafletjs.com"],
      .leaflet-control-attribution .leaflet-attribution-flag { display: none !important; }
    </style>""").add_to(fmap.get_root().html)

    cell_layer = folium.FeatureGroup(name="Ô geohash · OTD theo tuyến", show=True)
    for row in cells.itertuples():
        south, west, north, east = geohash_bounds(row.Geohash)
        status = row.RouteStatus
        color = fills[status]
        active = row.RouteId == selected_route
        selected = row.Geohash == selected_geohash
        otd = "—" if pd.isna(row.RouteOTD) else f"{row.RouteOTD:.0%}"
        cell_label = "<30" if status == "GRAY" else otd
        tooltip_html = (
            f"<b>{row.RouteId} - {status}</b><br>"
            f"OTD 30d: {otd}<br>"
            f"\u0110\u00e3 giao tr\u00ean tuy\u1ebfn: {row.RouteN:,}<br>"
            f"\u0110\u01a1n trong \u00f4 n\u00e0y: {row.Orders:,}<br>"
            f"Ch\u01b0a giao: {row.OpenN:,.0f} | \u0111ang v\u1eadn chuy\u1ec3n: {row.InTransitN:,.0f}<br>"
            f"\u0110ang tr\u1ec5: {row.DelayedN:,.0f} | tr\u1ec5 sau b\u00e0n giao: {row.InTransitDelayedN:,.0f}<br>"
            f"GMV r\u1ee7i ro ch\u01b0a giao: R$ {row.OpenGMVAtRisk:,.0f}<br>"
            f"GMV r\u1ee7i ro \u0111\u00e3 b\u00e0n giao: R$ {row.InTransitGMVAtRisk:,.0f}"
        )
        folium.Rectangle(
            bounds=[[south, west], [north, east]],
            color=NAVY if selected else ("#0B2F4A" if active else "#FFFFFF"),
            weight=3 if selected else (2 if active else 1),
            fill=True, fill_color=color, fill_opacity=.68,
            tooltip=folium.Tooltip(tooltip_html, sticky=True,
                                   style="font-size:12px;line-height:1.5"),
        ).add_to(cell_layer)
        folium.Marker(
            [row.Latitude, row.Longitude],
            icon=folium.DivIcon(html=(
                '<div style="font:700 8px Arial;color:#102B3F;text-align:center;'
                'white-space:nowrap;line-height:1.05;text-shadow:0 1px 2px #fff,0 -1px 2px #fff">'
                f'{seller_state} {row.BuyerState}<br>{cell_label}</div>')),
            interactive=False,
        ).add_to(cell_layer)
    cell_layer.add_to(fmap)
    if not selected_geohash:
        bounds = [[float(cells.Latitude.min()), float(cells.Longitude.min())],
                  [float(cells.Latitude.max()), float(cells.Longitude.max())]]
        fmap.fit_bounds(bounds, padding=(18, 18))
    return fmap, cells

def apply_picked_sim_date() -> None:
    picked = st.session_state.get("clock_date_picker")
    if picked is not None:
        st.session_state.sim_date = pd.Timestamp(picked)
        st.session_state.sim_playing = False
        st.session_state.sim_last_tick = time.monotonic()


def render_clock() -> None:
    advance_clock()
    # Keep the date picker synchronized with replay ticks and reset actions.
    current_date = pd.Timestamp(st.session_state.sim_date).date()
    st.session_state.clock_date_picker = current_date
    left, middle, right = st.columns([1, 1.2, 1.6])
    status = "LIVE SIMULATION" if st.session_state.sim_playing else "PAUSED"
    picked_date = left.date_input(
        "Ngày mô phỏng", value=current_date,
        min_value=SIM_MIN_DATE.date(), max_value=SIM_END.date(),
        format="DD/MM/YYYY", key="clock_date_picker",
        on_change=apply_picked_sim_date,
    )
    left.caption(status)
    speed = middle.selectbox("Tốc độ phát", [1, 2, 4], index=[1, 2, 4].index(
        int(st.session_state.sim_speed)), format_func=lambda v: f"{v} ngày / 20 giây",
        key="clock_speed")
    if speed != st.session_state.sim_speed:
        st.session_state.sim_speed = speed
        st.session_state.sim_last_tick = time.monotonic()
    play, reset, span = right.columns([1, 1, 2])
    if play.button("Tạm dừng" if st.session_state.sim_playing else "Tiếp tục",
                   use_container_width=True, key="clock_toggle"):
        st.session_state.sim_playing = not st.session_state.sim_playing
        st.session_state.sim_last_tick = time.monotonic()
        st.rerun(scope="app")
    if reset.button("Đặt lại", use_container_width=True, key="clock_reset"):
        st.session_state.sim_date = SIM_START
        st.session_state.clock_date_picker = SIM_START.date()
        st.session_state.sim_playing = False
        st.session_state.sim_last_tick = time.monotonic()
        st.rerun(scope="app")
    if st.session_state.sim_playing:
        elapsed = max(0.0, time.monotonic() - st.session_state.sim_last_tick)
        remaining = max(0, int(20 / max(1, int(st.session_state.sim_speed)) - elapsed))
        span.caption(f"Ngày kế sau {remaining}s · đến {SIM_END:%d/%m/%Y}")
    else:
        span.caption(f"Tạm dừng · đến {SIM_END:%d/%m/%Y}")


def make_route_queue(history: pd.DataFrame, completed: pd.DataFrame,
                     ongoing: pd.DataFrame, sim_date: pd.Timestamp):
    completed = completed.copy()
    completed["DeliveryDays"] = (completed.DeliveredAt - completed.PurchaseAt).dt.total_seconds() / 86400
    return route_rollup(completed, ongoing, sim_date)


def add_sim_action(kind: str, route: str, seller: str | None, note: str) -> None:
    entry = {"Thời điểm mô phỏng": st.session_state.sim_date.strftime("%Y-%m-%d"),
             "Tuyến": route, "Seller": seller or "—", "Hành động mô phỏng": kind,
             "Ghi chú": note.strip()[:180]}
    st.session_state.sim_actions.insert(0, entry)
    logging.info("sim_action=%s route=%s seller=%s", kind, route, seller or "-")


def sync_overview_route_selection() -> None:
    selected = st.session_state.get("overview_selected_route")
    if selected:
        if selected != st.session_state.get("selected_route"):
            st.session_state.map_selected_geohash = None
        st.session_state.selected_route = selected
        st.session_state.routeops_selected_route = selected


def select_priority_route(route: str) -> None:
    """Make a queue click the single source of truth for the overview route."""
    st.session_state.overview_selected_route = route
    st.session_state.selected_route = route
    st.session_state.routeops_selected_route = route
    st.session_state.map_selected_geohash = None


def mark_overview_origin_selected() -> None:
    st.session_state.overview_origin_user_selected = True


@st.dialog("Xác nhận nhận xử lý tuyến")
def route_ownership_dialog() -> None:
    route = st.session_state.get("route_ownership_pending")
    if not route:
        st.session_state.route_ownership_dialog_open = False
        return
    st.write(f"Bạn xác nhận nhận xử lý tuyến **{route}** chứ?")
    st.caption("Thao tác chỉ ghi nhận người phụ trách trong phiên mô phỏng; không thay đổi đơn hàng hay liên hệ hãng vận chuyển.")
    confirm, cancel = st.columns(2)
    if confirm.button("Xác nhận", type="primary", use_container_width=True,
                      key="confirm_route_ownership"):
        st.session_state.overview_selected_route = route
        st.session_state.selected_route = route
        st.session_state.routeops_selected_route = route
        st.session_state.route_owner = route
        st.session_state.routeops_screen = "Route Detail"
        st.session_state.route_ownership_dialog_open = False
        st.session_state.route_ownership_pending = None
        st.rerun()
    if cancel.button("Huy", use_container_width=True, key="cancel_route_ownership"):
        st.session_state.route_ownership_dialog_open = False
        st.session_state.route_ownership_pending = None
        st.rerun()


def screen_overview(history: pd.DataFrame, completed: pd.DataFrame,
                    ongoing: pd.DataFrame, rollup: pd.DataFrame,
                    sim_date: pd.Timestamp):
    st.subheader("Route Overview")
    if rollup.empty:
        st.info("Ch\u01b0a c\u00f3 d\u1eef li\u1ec7u \u0111\u1ee7 \u0111\u1ec3 t\u1ed5ng h\u1ee3p tuy\u1ebfn t\u1ea1i ng\u00e0y m\u00f4 ph\u1ecfng n\u00e0y.")
        return
    # Only offer origins that have a calculable route in the current 30-day
    # window. This prevents selecting a historical-only state (for example AC)
    # and getting an empty route panel at the current simulated date.
    route_origins = rollup.assign(
        SellerOrigin=rollup.RouteId.str.split(" \u2192 ", n=1).str[0]
    ).groupby("SellerOrigin", as_index=False).DeliveredN.sum()
    origins = sorted(route_origins.loc[route_origins.DeliveredN.gt(0), "SellerOrigin"].tolist())
    if not origins:
        st.info("Kh\u00f4ng c\u00f3 bang seller \u0111\u1ee7 \u0111i\u1ec1u ki\u1ec7n \u0111\u1ec3 l\u1ecdc b\u1ea3n \u0111\u1ed3.")
        return

    origin_totals = rollup.assign(
        SellerOrigin=rollup.RouteId.str.split(" \u2192 ", n=1).str[0]
    ).groupby("SellerOrigin", as_index=False).agg(
        DeliveredN=("DeliveredN", "sum"), OpenGMVAtRisk=("OpenGMVAtRisk", "sum"))
    origin_totals = origin_totals.sort_values(
        ["DeliveredN", "OpenGMVAtRisk"], ascending=[False, False])
    default_origin = origin_totals.iloc[0].SellerOrigin if not origin_totals.empty else origins[0]
    if (st.session_state.get("overview_origin") not in origins or
            not st.session_state.get("overview_origin_user_selected", False)):
        st.session_state.overview_origin = default_origin
    seller_state = st.selectbox(
        "Seller origin \u00b7 bang g\u1eedi", origins, key="overview_origin",
        on_change=mark_overview_origin_selected)
    origin_routes = rollup[rollup.RouteId.str.startswith(seller_state + " \u2192", na=False)].copy()

    if origin_routes.empty:
        st.warning(f"Ch\u01b0a c\u00f3 tuy\u1ebfn n\u00e0o t\u1eeb {seller_state} c\u00f3 d\u1eef li\u1ec7u trong c\u1eeda s\u1ed5 hi\u1ec7n t\u1ea1i. Ch\u1ecdn seller origin kh\u00e1c.")
        return

    origin_routes["_StatusOrder"] = origin_routes.Status.map(
        {"RED": 0, "YELLOW": 1, "GREEN": 2, "GRAY": 3})
    default_route = origin_routes.sort_values(
        ["_StatusOrder", "OpenGMVAtRisk", "DeliveredN"],
        ascending=[True, False, False]).iloc[0].RouteId
    route_choices = origin_routes.RouteId.tolist()
    if st.session_state.get("overview_selected_route") not in route_choices:
        existing = st.session_state.get("selected_route")
        st.session_state.overview_selected_route = existing if existing in route_choices else default_route
    selected_route = st.selectbox(
        "Tuy\u1ebfn \u0111ang xem \u00b7 Seller \u2192 Kh\u00e1ch", route_choices,
        key="overview_selected_route", on_change=sync_overview_route_selection)
    st.session_state.selected_route = selected_route
    st.session_state.routeops_selected_route = selected_route
    selected_route_row = origin_routes[origin_routes.RouteId.eq(selected_route)].iloc[0]
    route_title, route_action = st.columns([4, 1])
    with route_title:
        st.markdown(f"### {selected_route} \u00b7 {selected_route_row.Status}")
    with route_action:
        owned = st.session_state.get("route_owner") == selected_route
        if st.button("Nh\u1eadn x\u1eed l\u00fd" if not owned else "\u0110\u00e3 nh\u1eadn tuy\u1ebfn",
                     type="primary", disabled=owned,
                     key="take_route_ownership", use_container_width=True):
            st.session_state.route_ownership_pending = selected_route
            st.session_state.route_ownership_dialog_open = True
            st.rerun(scope="app")

    selected_route_otd = ("\u2014" if pd.isna(selected_route_row.OTD)
                          else f"{selected_route_row.OTD:.1%}")
    selected_route_risk_pct = ("\u2014" if pd.isna(selected_route_row.RiskPctOfOpenGMV)
                               else f"{selected_route_row.RiskPctOfOpenGMV:.1%}")
    on_time_n = int(selected_route_row.DeliveredN - selected_route_row.LateDelivered)
    cards = st.columns(4)
    cards[0].metric("OTD \u00b7 30 ng\u00e0y", selected_route_otd,
                    f"{on_time_n:,}/{int(selected_route_row.DeliveredN):,} giao \u0111\u00fang h\u1eb9n")
    cards[1].metric("GMV at Risk \u00b7 %", selected_route_risk_pct,
                    f"{int(selected_route_row.RescueN):,} \u0111\u01a1n tr\u1ec5 \u22653 ng\u00e0y")
    cards[2].metric("GMV at Risk \u00b7 BRL",
                    f"R$ {float(selected_route_row.OpenGMVAtRisk):,.0f}",
                    f"R$ {float(selected_route_row.InTransitGMVAtRisk):,.0f} \u0111ang v\u1eadn chuy\u1ec3n")
    cards[3].metric("Giao th\u1ef1c t\u1ebf TB",
                    f"{float(selected_route_row.ActualDays):.1f} ng\u00e0y"
                    if selected_route_row.DeliveredN else "\u2014",
                    f"Ng\u00e0y h\u1eb9n TB: {float(selected_route_row.PromisedDays):.1f} ng\u00e0y"
                    if selected_route_row.DeliveredN else None)

    route_done30 = completed[completed.RouteEligible & completed.EstimatedAt.notna() &
                             completed.DeliveredAt.ge(sim_date.normalize() - pd.Timedelta(days=29))]
    route_map_orders = route_done30[route_done30.SellerState.eq(seller_state)]
    previous_origin = st.session_state.get("map_origin")
    if previous_origin != seller_state:
        st.session_state.map_selected_geohash = None
        st.session_state.map_origin = seller_state
    selected_geohash = st.session_state.get("map_selected_geohash")
    result = route_map(route_map_orders, rollup, seller_state, selected_geohash,
                       selected_route=selected_route)
    map_col, queue_col = st.columns([2.1, 1], gap="large")

    with map_col:
        st.markdown("""
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:18px;
                    padding:9px 15px;margin:0 0 8px;background:#fff;
                    border:1px solid #dbe4eb;border-radius:11px;color:#475569;
                    font-size:13px;line-height:1.2">
          <span><i style="display:inline-block;width:15px;height:15px;border-radius:3px;background:#54A879;vertical-align:-3px;margin-right:7px"></i>OTD &#8805;90%</span>
          <span><i style="display:inline-block;width:15px;height:15px;border-radius:3px;background:#E9A94B;vertical-align:-3px;margin-right:7px"></i>85&#8211;&lt;90%</span>
          <span><i style="display:inline-block;width:15px;height:15px;border-radius:3px;background:#D96570;vertical-align:-3px;margin-right:7px"></i>&lt;85%</span>
          <span><i style="display:inline-block;width:15px;height:15px;border-radius:3px;background:#B8A5C9;vertical-align:-3px;margin-right:7px"></i>&lt;30 &#273;&#417;n giao</span>
        </div>
        """, unsafe_allow_html=True)
        if result is None and (folium is None or st_folium is None):
            st.error("Bản đồ Leaflet chưa được cài. Chạy `python -m pip install -r requirements-forecast.txt` rồi tải lại trang.")
        elif result is None:
            st.info("Ch\u01b0a c\u00f3 \u00f4 \u0111\u1ecba l\u00fd trong c\u1eeda s\u1ed5 30 ng\u00e0y n\u00e0y.")
        else:
            fmap, cells = result
            map_state = st_folium(
                fmap, height=570, width=None,
                key=f"route_overview_map_{seller_state}_{selected_route}_{selected_geohash or 'all'}",
                returned_objects=["last_object_clicked"],
            )
            clicked_point = (map_state or {}).get("last_object_clicked")
            if clicked_point and clicked_point.get("lat") is not None:
                clicked_hash = geohash_encode(clicked_point["lat"], clicked_point["lng"],
                                              precision=MAP_GEOHASH_PRECISION)
                if clicked_hash in set(cells.Geohash) and clicked_hash != selected_geohash:
                    st.session_state.map_selected_geohash = clicked_hash
                    st.rerun(scope="app")
            if selected_geohash and st.button("Bỏ phóng ô", key="clear_map_cell"):
                st.session_state.map_selected_geohash = None
                st.rerun(scope="app")
            selected_geohash = st.session_state.get("map_selected_geohash")
            if selected_geohash:
                cell = cells[cells.Geohash.eq(selected_geohash)]
                if not cell.empty:
                    item = cell.iloc[0]
                    route_row = rollup[rollup.RouteId.eq(item.RouteId)]
                    otd_value = "\u2014" if route_row.empty or pd.isna(route_row.OTD.iloc[0]) else f"{route_row.OTD.iloc[0]:.1%}"
                    sample_n = int(route_row.DeliveredN.iloc[0]) if not route_row.empty else 0
                    st.markdown(f"**Tuy\u1ebfn {item.RouteId} \u00b7 {item.RouteStatus}**")
                    st.caption(f"{item.Orders:,} \u0111\u01a1n \u0111\u00e3 giao trong \u00f4 \u00b7 OTD tuy\u1ebfn: {otd_value} \u00b7 N tuy\u1ebfn: {sample_n:,}")

    with queue_col:
        st.markdown("#### Priority routes")
        priority = origin_routes[origin_routes.Status.isin(["RED", "YELLOW"])].copy()
        priority["_StatusOrder"] = priority.Status.map(
            {"RED": 0, "YELLOW": 1, "GREEN": 2, "GRAY": 3})
        priority = priority.sort_values(
            ["_StatusOrder", "OpenGMVAtRisk", "DeliveredN"], ascending=[True, False, False])
        if priority.empty:
            st.info("Hiện không có tuyến đỏ/vàng đủ mẫu trong cửa sổ 30 ngày.")
        for _, row in priority.iterrows():
            route = str(row.RouteId)
            marker = "\u25cf " if route == selected_route else ""
            label = f"{marker}{route} \u00b7 {row.Status}"
            st.button(label, key=f"priority_route_{route.replace(' ', '_')}",
                      type="primary" if route == selected_route else "secondary",
                      on_click=select_priority_route, args=(route,),
                      use_container_width=True)
            otd = "\u2014" if pd.isna(row.OTD) else f"{row.OTD:.1%}"
            delay_pct = "\u2014" if pd.isna(row.CurrentDelayPct) else f"{row.CurrentDelayPct:.1%}"
            risk_pct_text = ("\u2014" if pd.isna(row.RiskPctOfOpenGMV)
                             else f"{row.RiskPctOfOpenGMV:.1%} GMV m\u1edf")
            st.caption(f"OTD {otd} \u00b7 {int(row.DeliveredN):,} giao \u00b7 "
                       f"{int(row.OpenN):,} ch\u01b0a giao \u00b7 tr\u1ec5 {delay_pct} \u00b7 "
                       f"GMV r\u1ee7i ro R$ {float(row.OpenGMVAtRisk):,.0f} ({risk_pct_text})")
        st.caption("M\u00e0u \u00f4 l\u00e0 OTD c\u1ee7a tuy\u1ebfn seller \u2192 kh\u00e1ch, kh\u00f4ng ph\u1ea3i KPI ri\u00eang c\u1ee7a geohash.")

def screen_route_detail(history: pd.DataFrame, completed: pd.DataFrame,
                        ongoing: pd.DataFrame, rollup: pd.DataFrame,
                        sim_date: pd.Timestamp):
    st.subheader("Chi tiết tuyến · hiệu suất và đơn cần cứu")
    if rollup.empty:
        st.info("Chưa có dữ liệu tuyến tại ngày mô phỏng.")
        return

    options = rollup.RouteId.tolist()
    route = st.session_state.get("selected_route", options[0])
    if route not in options:
        route = options[0]
    st.session_state.detail_route = route
    route_done = completed[completed.RouteEligible & completed.RouteId.eq(route) &
                           completed.DeliveredAt.ge(sim_date.normalize() - pd.Timedelta(days=29)) &
                           completed.EstimatedAt.notna()].copy()
    route_open = ongoing[ongoing.RouteEligible & ongoing.RouteId.eq(route)].copy()

    if not route_done.empty:
        route_done["LateDaysActual"] = (
            route_done.DeliveredAt.dt.normalize() - route_done.EstimatedAt.dt.normalize()
        ).dt.days
        route_done["Late"] = route_done.LateDaysActual.gt(0)
        route_done["ActualDays"] = (
            route_done.DeliveredAt - route_done.PurchaseAt
        ).dt.total_seconds() / 86400
        route_done["DeliveryDate"] = route_done.DeliveredAt.dt.floor("D")
        base_otd = float((~route_done.Late).mean())
        actual_days = float(route_done.ActualDays.mean())
    else:
        base_otd = actual_days = None

    rescue = route_open[route_open.DelayDays.ge(3)].copy()
    selected_rollup = rollup[rollup.RouteId.eq(route)].iloc[0]
    cards = st.columns(4)
    on_time_n = int((~route_done.Late).sum()) if not route_done.empty else 0
    late_delivered_n = int(route_done.Late.sum()) if not route_done.empty else 0
    cards[0].metric("OTD 30 ng\u00e0y", "\u2014" if base_otd is None else f"{base_otd:.1%}",
                    f"{on_time_n:,} \u0111\u01a1n \u0111\u00fang h\u1eb9n / {len(route_done):,} \u0111\u01a1n \u0111\u00e3 giao")
    cards[1].metric("\u0110\u01a1n ch\u01b0a giao", f"{len(route_open):,}",
                    f"\u0110\u00e3 b\u00e0n giao: {int(selected_rollup.InTransitN):,}; "
                    f"ch\u01b0a b\u00e0n giao: {int(selected_rollup.NoHandoverEventN):,}")
    cards[2].metric("Qu\u00e1 h\u1ea1n \u22653 ng\u00e0y", f"{len(rescue):,}",
                    "S\u1ed1 \u0111\u01a1n ch\u01b0a giao tr\u1ec5 t\u1eeb 3 ng\u00e0y")
    cards[3].metric("GMV r\u1ee7i ro \u00b7 ch\u01b0a giao", f"R$ {rescue.GMV.sum():,.0f}",
                    "Gi\u00e1 tr\u1ecb \u0111\u01a1n ch\u01b0a giao tr\u1ec5 t\u1eeb 3 ng\u00e0y")
    st.caption("\u0110\u01a1n giao trong 30 ng\u00e0y d\u00f9ng \u0111\u1ec3 t\u00ednh OTD; \u0111\u01a1n ch\u01b0a giao l\u00e0 h\u00e0ng \u0111\u1ee3i t\u1ea1i ng\u00e0y m\u00f4 ph\u1ecfng. Hai nh\u00f3m t\u00e1ch bi\u1ec7t, \u0111\u00e3 lo\u1ea1i canceled.")

    if st.button("Phân tích seller bàn giao trên tuyến này", key="open_seller_performance"):
        st.session_state.routeops_screen = "Seller Performance"
        st.rerun(scope="app")

    st.markdown("#### Hiệu suất giao hàng")
    if route_done.empty:
        st.info("Không có đơn giao trong 30 ngày này.")
    else:
        daily = route_done.groupby("DeliveryDate").agg(
            Delivered=("OrderId", "nunique"), Late=("Late", "sum")).reset_index()
        daily["OTD"] = 1 - daily.Late / daily.Delivered
        fig = go.Figure(go.Scatter(
            x=daily.DeliveryDate, y=daily.OTD * 100, mode="lines+markers",
            line=dict(color=BLUE, width=3), marker=dict(size=6), name="OTD"))
        fig.add_hline(y=90, line_dash="dot", line_color=GRAY)
        fig.update_layout(height=230, margin=dict(l=5, r=5, t=8, b=5),
                          yaxis_title="OTD (%)", xaxis_title=None,
                          yaxis_range=[0, 105], showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.metric("Thời gian giao thực tế trung bình · mua đến nhận",
                  f"{actual_days:.1f} ngày")

    st.markdown("#### M\u00f4 ph\u1ecfng thay \u0111\u1ed5i ng\u00e0y h\u1eb9n")
    delivered_box, open_box = st.columns(2)
    with delivered_box:
        st.markdown("##### \u0110\u01a1n \u0111\u00e3 giao \u00b7 r\u00fat ng\u1eafn ng\u00e0y h\u1eb9n")
        days = st.slider("R\u00fat ng\u1eafn ng\u00e0y h\u1eb9n (ng\u00e0y)", min_value=0, max_value=12,
                          value=0, step=1, key="delivery_improvement_days")
        if route_done.empty:
            st.info("Ch\u01b0a c\u00f3 \u0111\u01a1n \u0111\u00e3 giao \u0111\u1ec3 m\u00f4 ph\u1ecfng.")
        else:
            ontime_done = route_done[~route_done.Late].copy()
            if ontime_done.empty:
                st.info("Tuy\u1ebfn kh\u00f4ng c\u00f3 \u0111\u01a1n giao \u0111\u00fang h\u1ea1n trong 30 ng\u00e0y.")
            else:
                simulated_promise = ontime_done.EstimatedAt - pd.to_timedelta(days, unit="D")
                simulated_late_days = (
                    ontime_done.DeliveredAt.dt.normalize() - simulated_promise.dt.normalize()
                ).dt.days
                newly_late = simulated_late_days.gt(0)
                newly_at_risk = simulated_late_days.ge(3)
                simulated_late_n = int(route_done.Late.sum() + newly_late.sum())
                simulated_route_otd = 1 - simulated_late_n / len(route_done)
                new_risk_gmv = float(ontime_done.loc[newly_at_risk, "GMV"].sum())
                newly_late_pct = float(newly_late.mean() * 100)

                comparison = st.columns(4)
                comparison[0].metric("OTD g\u1ed1c", f"{base_otd:.1%}")
                comparison[1].metric(
                    "OTD sau \u0111\u1ed5i h\u1eb9n", f"{simulated_route_otd:.1%}",
                    f"{(simulated_route_otd - base_otd) * 100:+.1f} \u0111i\u1ec3m %",
                    delta_color="normal")
                comparison[2].metric(
                    "\u0110\u01a1n \u0111\u00fang h\u1ea1n th\u00e0nh tr\u1ec5",
                    f"{int(newly_late.sum()):,}",
                    f"{newly_late_pct:.1f}% nh\u00f3m \u0111\u00fang h\u1ea1n g\u1ed1c" if newly_late.any() else None,
                    delta_color="inverse")
                comparison[3].metric(
                    "GMV ph\u00e1t sinh tr\u1ec5 \u22653 ng\u00e0y",
                    f"R$ {new_risk_gmv:,.2f}",
                    f"+R$ {new_risk_gmv:,.2f} so v\u1edbi g\u1ed1c" if new_risk_gmv else None,
                    delta_color="inverse")
                st.caption("Ch\u1ec9 \u0111\u1ed5i ng\u00e0y h\u1eb9n; ng\u00e0y giao gi\u1eef nguy\u00ean. K\u1ebft qu\u1ea3 l\u00e0 m\u00f4 ph\u1ecfng.")

            st.markdown("###### \u0110\u01a1n \u0111\u00e3 giao tr\u1ec5")
            late_done = route_done[route_done.Late].copy()
            if late_done.empty:
                st.success("Kh\u00f4ng c\u00f3 \u0111\u01a1n giao tr\u1ec5 trong c\u1eeda s\u1ed5 n\u00e0y.")
            else:
                late_kpis = st.columns(2)
                late_kpis[0].metric("\u0110\u01a1n giao tr\u1ec5", f"{len(late_done):,}")
                late_kpis[1].metric("GMV \u0111\u01a1n giao tr\u1ec5", f"R$ {late_done.GMV.sum():,.2f}")
                if st.button("Y\u00eau c\u1ea7u li\u00ean h\u1ec7 b\u00ean v\u1eadn chuy\u1ec3n",
                             key=f"sla_review_{route}"):
                    add_sim_action("R\u00e0 so\u00e1t SLA v\u1eadn chuy\u1ec3n theo tuy\u1ebfn", route, None,
                                   f"{len(late_done)} \u0111\u01a1n giao tr\u1ec5; y\u00eau c\u1ea7u ki\u1ec3m tra SLA tuy\u1ebfn")
                    st.success("\u0110\u00e3 ghi nh\u1eadn y\u00eau c\u1ea7u trong nh\u1eadt k\u00fd m\u00f4 ph\u1ecfng.")

    with open_box:
        st.markdown("##### \u0110ang giao tr\u1ec5 1\u20132 ng\u00e0y \u00b7 n\u1edbi ng\u00e0y h\u1eb9n")
        in_transit = route_open[route_open.CarrierAt.notna()].copy()
        early_late = in_transit[in_transit.DelayDays.between(1, 2)].copy()
        extra = st.slider("N\u1edbi ng\u00e0y h\u1eb9n th\u00eam (ng\u00e0y)", min_value=0, max_value=7,
                          value=1, step=1, key="promise_extension_days")
        after_extension = (early_late.DelayDays - extra).clip(lower=0)
        still_overdue = after_extension.gt(0)
        base_late_n = int(len(early_late))
        scenario_late_n = int(still_overdue.sum())
        base_late_gmv = float(early_late.GMV.sum())
        scenario_late_gmv = float(early_late.loc[still_overdue, "GMV"].sum())
        count_delta_pct = ((scenario_late_n / base_late_n - 1) * 100) if base_late_n else 0.0
        gmv_delta_pct = ((scenario_late_gmv / base_late_gmv - 1) * 100) if base_late_gmv else 0.0

        comparison = st.columns(3)
        comparison[0].metric("Hi\u1ec7n tr\u1ec5 1\u20132 ng\u00e0y", f"{base_late_n:,}")
        comparison[1].metric(
            "C\u00f2n tr\u1ec5 theo h\u1eb9n m\u1edbi", f"{scenario_late_n:,}",
            f"{scenario_late_n - base_late_n:+,} \u0111\u01a1n ({count_delta_pct:+.1f}%)" if base_late_n else None,
            delta_color="inverse")
        comparison[2].metric(
            "GMV c\u00f2n tr\u1ec5 theo h\u1eb9n m\u1edbi", f"R$ {scenario_late_gmv:,.2f}",
            f"R$ {scenario_late_gmv - base_late_gmv:+,.2f} ({gmv_delta_pct:+.1f}%)" if base_late_gmv else None,
            delta_color="inverse")
        st.caption("\u0110\u1ed5i ng\u00e0y h\u1eb9n ch\u1ec9 \u0111\u1ed5i c\u00e1ch x\u00e1c \u0111\u1ecbnh tr\u1ec5; kh\u00f4ng l\u00e0m \u0111\u01a1n giao nhanh h\u01a1n.")
        open_orders = route_open.copy()
        open_orders["Nh\u00f3m"] = "Ch\u01b0a b\u00e0n giao"
        open_orders.loc[open_orders.CarrierAt.notna() & open_orders.EstimatedAt.isna(), "Nh\u00f3m"] = "\u0110ang giao \u00b7 thi\u1ebfu ng\u00e0y h\u1eb9n"
        open_orders.loc[open_orders.CarrierAt.notna() & open_orders.DelayDays.eq(0) & open_orders.EstimatedAt.notna(), "Nh\u00f3m"] = "\u0110ang giao \u00b7 ch\u01b0a \u0111\u1ebfn h\u1ea1n"
        open_orders.loc[open_orders.CarrierAt.notna() & open_orders.DelayDays.between(1, 2), "Nh\u00f3m"] = "\u0110ang giao \u00b7 tr\u1ec5 1\u20132 ng\u00e0y"
        open_orders.loc[open_orders.DelayDays.ge(3), "Nh\u00f3m"] = "Qu\u00e1 h\u1ea1n \u22653 ng\u00e0y \u00b7 CSKH"

        group_order = ["\u0110ang giao \u00b7 tr\u1ec5 1\u20132 ng\u00e0y", "\u0110ang giao \u00b7 ch\u01b0a \u0111\u1ebfn h\u1ea1n",
                       "Qu\u00e1 h\u1ea1n \u22653 ng\u00e0y \u00b7 CSKH", "Ch\u01b0a b\u00e0n giao",
                       "\u0110ang giao \u00b7 thi\u1ebfu ng\u00e0y h\u1eb9n"]
        group_counts = open_orders["Nh\u00f3m"].value_counts()
        selected_group = st.selectbox(
            "Danh s\u00e1ch \u0111\u01a1n ch\u01b0a giao", group_order,
            format_func=lambda name: f"{name} ({int(group_counts.get(name, 0)):,})",
            key=f"open_order_group_{route}")
        shown = open_orders[open_orders["Nh\u00f3m"].eq(selected_group)].copy()
        if shown.empty:
            st.info("Kh\u00f4ng c\u00f3 \u0111\u01a1n trong nh\u00f3m n\u00e0y.")
        else:
            shown["Nguy\u00ean nh\u00e2n c\u1ea7n ki\u1ec3m tra"] = "Sau b\u00e0n giao / ch\u01b0a x\u00e1c \u0111\u1ecbnh"
            no_handover = shown.CarrierAt.isna()
            seller_late = (shown.CarrierAt.notna() & shown.ShippingLimitAt.notna() &
                           shown.CarrierAt.gt(shown.ShippingLimitAt))
            shown.loc[no_handover, "Nguy\u00ean nh\u00e2n c\u1ea7n ki\u1ec3m tra"] = "Ch\u01b0a b\u00e0n giao"
            shown.loc[seller_late, "Nguy\u00ean nh\u00e2n c\u1ea7n ki\u1ec3m tra"] = "Seller b\u00e0n giao sau h\u1ea1n"
            shown = shown.sort_values(["DelayDays", "GMV"], ascending=[False, False])
            table = shown[["OrderId", "DelayDays", "EstimatedAt", "GMV", "CustomerState",
                           "Nguy\u00ean nh\u00e2n c\u1ea7n ki\u1ec3m tra"]].rename(columns={
                "OrderId": "M\u00e3 \u0111\u01a1n", "DelayDays": "Tr\u1ec5 (ng\u00e0y)",
                "EstimatedAt": "Ng\u00e0y h\u1eb9n", "GMV": "GMV (BRL)",
                "CustomerState": "Bang kh\u00e1ch nh\u1eadn"})
            st.dataframe(table, hide_index=True, width="stretch", height=260,
                         column_config={"Ng\u00e0y h\u1eb9n": st.column_config.DateColumn(format="DD/MM/YYYY"),
                                        "GMV (BRL)": st.column_config.NumberColumn(format="R$ %.2f")})

        rescue = open_orders[open_orders.DelayDays.ge(3)].copy()
        if not rescue.empty and selected_group == "Qu\u00e1 h\u1ea1n \u22653 ng\u00e0y \u00b7 CSKH":
            if st.button(f"Chuy\u1ec3n {len(rescue):,} \u0111\u01a1n tr\u1ec5 t\u1eeb 3 ng\u00e0y sang CSKH",
                         type="primary", key=f"send_cskh_{route}"):
                add_sim_action("Chuy\u1ec3n danh s\u00e1ch \u0111\u01a1n tr\u1ec5 t\u1eeb 3 ng\u00e0y sang CSKH", route, None,
                               f"{len(rescue)} \u0111\u01a1n; ng\u01b0\u1eddi g\u1eedi: Gi\u00e1m \u0111\u1ed1c V\u1eadn chuy\u1ec3n; ng\u01b0\u1eddi nh\u1eadn: CSKH")
                st.success("\u0110\u00e3 ghi nh\u1eadn chuy\u1ec3n danh s\u00e1ch trong nh\u1eadt k\u00fd m\u00f4 ph\u1ecfng.")

def seller_scorecard_asof(history: pd.DataFrame, sim_date: pd.Timestamp) -> pd.DataFrame:
    """Weighted seller score using only events observed by the simulated date."""
    cutoff = sim_date.normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    data = history.copy()
    if "ReviewAt" not in data:
        data["ReviewAt"] = pd.NaT
    if "ReviewScore" not in data:
        data["ReviewScore"] = pd.NA
    data = data[data.PurchaseAt.le(cutoff) & data.SellerCount.eq(1) &
                data.SellerId.notna()].copy()
    for column in ("CarrierAt", "DeliveredAt", "ReviewAt"):
        data.loc[data[column].gt(cutoff), column] = pd.NaT

    canceled = data.OrderStatus.astype("string").str.lower().eq("canceled")
    delivered = ~canceled & data.DeliveredAt.notna()
    handover = ~canceled & data.CarrierAt.notna() & data.ShippingLimitAt.notna()
    otd_eligible = delivered & data.EstimatedAt.notna()
    review_eligible = delivered & data.ReviewAt.notna() & data.ReviewScore.notna()
    late = otd_eligible & data.DeliveredAt.gt(data.EstimatedAt)

    data["_Delivered"] = delivered.astype(int)
    data["_OTDEligible"] = otd_eligible.astype(int)
    data["_OnTime"] = float("nan")
    data.loc[otd_eligible, "_OnTime"] = data.loc[otd_eligible, "DeliveredAt"].le(
        data.loc[otd_eligible, "EstimatedAt"]).astype(int)
    data["_Review"] = float("nan")
    data.loc[review_eligible, "_Review"] = data.loc[review_eligible, "ReviewScore"]
    data["_LateDays"] = float("nan")
    data.loc[late, "_LateDays"] = (data.loc[late, "DeliveredAt"] -
                                      data.loc[late, "EstimatedAt"]).dt.total_seconds() / 86400
    data["_HandoverOnTime"] = float("nan")
    data.loc[handover, "_HandoverOnTime"] = data.loc[handover, "CarrierAt"].le(
        data.loc[handover, "ShippingLimitAt"]).astype(int)
    data["_HandoverCount"] = handover.astype(int)
    data["_CanceledFinal"] = canceled.astype(int)

    scorecard = data.groupby("SellerId", as_index=False).agg(
        Orders=("OrderId", "nunique"), CompletedOrders=("_Delivered", "sum"),
        OTDOrders=("_OTDEligible", "sum"), OnTimeRate=("_OnTime", "mean"),
        AvgReviewScore=("_Review", "mean"), AvgLateDays=("_LateDays", "mean"),
        HandoverOnTimePct=("_HandoverOnTime", "mean"),
        HandoverOrders=("_HandoverCount", "sum"),
        CanceledOrdersFinal=("_CanceledFinal", "sum"), GMV=("GMV", "sum"))
    scorecard["CancelRateFinal"] = scorecard.CanceledOrdersFinal.div(
        scorecard.Orders.replace(0, pd.NA))

    # Match the project's existing scorecard normalization bounds.
    bounds = {
        "AvgReviewScore": (3.0, 4.5), "OnTimeRate": (0.80, 0.97),
        "HandoverOnTimePct": (0.80, 0.97), "AvgLateDays": (14.0, 1.0),
        "CancelRateFinal": (0.02, 0.0),
    }
    weights = {
        "AvgReviewScore": 0.30, "OnTimeRate": 0.25,
        "HandoverOnTimePct": 0.25, "AvgLateDays": 0.10,
        "CancelRateFinal": 0.10,
    }
    for metric, (low, high) in bounds.items():
        values = pd.to_numeric(scorecard[metric], errors="coerce")
        if metric == "AvgLateDays":
            values = values.fillna(0)
        scorecard[f"{metric}Norm"] = (100 * (values - low) / (high - low)).clip(0, 100)
    required = (scorecard.CompletedOrders.ge(30) & scorecard.OnTimeRate.notna() &
                scorecard.AvgReviewScore.notna() & scorecard.HandoverOnTimePct.notna())
    scorecard["SellerScore"] = sum(
        scorecard[f"{metric}Norm"].fillna(0) * weight
        for metric, weight in weights.items())
    scorecard.loc[~required, "SellerScore"] = pd.NA
    scorecard["Grade"] = "Chưa xếp hạng"
    scorecard.loc[required & scorecard.SellerScore.ge(85), "Grade"] = "A"
    scorecard.loc[required & scorecard.SellerScore.ge(70) & scorecard.SellerScore.lt(85), "Grade"] = "B"
    scorecard.loc[required & scorecard.SellerScore.ge(50) & scorecard.SellerScore.lt(70), "Grade"] = "C"
    scorecard.loc[required & scorecard.SellerScore.lt(50), "Grade"] = "D"
    return scorecard


def screen_sellers(history: pd.DataFrame, route: str, sim_date: pd.Timestamp):
    st.subheader("Seller Performance · bàn giao trên tuyến")
    route_sellers = seller_handover(history, route, sim_date)
    if route_sellers.empty:
        st.info("Chưa có dữ liệu bàn giao quan sát được cho tuyến này tại ngày mô phỏng.")
        return

    scorecard = seller_scorecard_asof(history, sim_date)
    sellers = route_sellers.merge(scorecard, on="SellerId", how="left", suffixes=("Route", "Score"))
    sellers["Grade"] = sellers.Grade.fillna("Chưa xếp hạng")
    route_average = float((route_sellers.HandoverOnTimePct * route_sellers.Orders).sum() /
                          route_sellers.Orders.sum()) if route_sellers.Orders.sum() else 0.0
    route_gmv = float(route_sellers.GMV.sum())
    sellers["GMVImpactPct"] = sellers.GMVRoute.div(route_gmv).mul(100) if route_gmv else 0.0
    sellers["QualityRisk"] = (1 - sellers.HandoverOnTimePctRoute) * 100
    sellers["PriorityScore"] = 0.60 * sellers.QualityRisk + 0.40 * sellers.GMVImpactPct
    sellers["RouteAverage"] = route_average
    action_by_grade = {
        "A": "Duy trì", "B": "Theo dõi",
        "C": "Kế hoạch cải thiện 30 ngày",
        "D": "Nhắc nhở và rà soát",
        "Chưa xếp hạng": "Tích lũy thêm dữ liệu",
    }
    sellers["RecommendedAction"] = sellers.Grade.map(action_by_grade)
    sellers = sellers.sort_values(["PriorityScore", "GMVRoute"], ascending=False,
                                  na_position="last").reset_index(drop=True)

    cd = sellers[sellers.Grade.isin(["C", "D"])]
    cd_gmv_pct = float(cd.GMVRoute.sum() / route_gmv * 100) if route_gmv else 0.0
    kpis = st.columns(4)
    kpis[0].metric("Seller trên tuyến", f"{len(sellers):,}")
    kpis[1].metric("Bàn giao đúng hạn · tuyến", f"{route_average:.1%}")
    kpis[2].metric("Seller hạng C/D", f"{len(cd):,}")
    kpis[3].metric("GMV C/D · tuyến", f"{cd_gmv_pct:.1f}%")

    view = sellers[["SellerId", "Grade", "CompletedOrdersScore", "OrdersRoute",
                    "HandoverOnTimePctRoute", "RouteAverage", "SellerScore",
                    "PriorityScore", "RecommendedAction"]].rename(columns={
        "SellerId": "Seller ID", "Grade": "Hạng",
        "CompletedOrdersScore": "Đơn hoàn tất · toàn sàn",
        "OrdersRoute": "Đơn trên tuyến",
        "HandoverOnTimePctRoute": "Bàn giao đúng hạn · tuyến (%)",
        "RouteAverage": "Trung bình tuyến (%)",
        "SellerScore": "Seller Score", "PriorityScore": "Priority Score",
        "RecommendedAction": "Đề xuất",
    })
    for column in ("B\u00e0n giao \u0111\u00fang h\u1ea1n \u00b7 tuy\u1ebfn (%)", "Trung b\u00ecnh tuy\u1ebfn (%)"):
        view[column] = view[column] * 100
    table = st.dataframe(view, hide_index=True, width="stretch", height=430,
        column_config={
            "Bàn giao đúng hạn · tuyến (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "Trung bình tuyến (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "Seller Score": st.column_config.NumberColumn(format="%.1f"),
            "Priority Score": st.column_config.NumberColumn(format="%.1f"),
        }, on_select="rerun", selection_mode="single-row", key=f"seller_table_{route}")

    selected_rows = table.selection.rows if table else []
    selected_index = selected_rows[-1] if selected_rows else 0
    selected = sellers.iloc[selected_index]
    with st.expander("Chi tiết seller được chọn"):
        st.write({
            "Seller ID": selected.SellerId, "Hạng": selected.Grade,
            "Seller Score": round(float(selected.SellerScore), 1)
                if pd.notna(selected.SellerScore) else "Chưa xếp hạng",
            "Review trung bình": round(float(selected.AvgReviewScore), 2)
                if pd.notna(selected.AvgReviewScore) else "N/A",
            "OTD": f"{selected.OnTimeRate:.1%}" if pd.notna(selected.OnTimeRate) else "N/A",
            "Bàn giao đúng hạn · toàn sàn": f"{selected.HandoverOnTimePctScore:.1%}"
                if pd.notna(selected.HandoverOnTimePctScore) else "N/A",
            "Bàn giao đúng hạn · tuyến": f"{selected.HandoverOnTimePctRoute:.1%}",
            "Trễ trung bình · ngày": round(float(selected.AvgLateDays), 1)
                if pd.notna(selected.AvgLateDays) else 0,
            "Tỷ lệ hủy theo trạng thái cuối nguồn": f"{selected.CancelRateFinal:.1%}"
                if pd.notna(selected.CancelRateFinal) else "N/A",
            "Priority Score": round(float(selected.PriorityScore), 1)
                if pd.notna(selected.PriorityScore) else "N/A",
            "Đề xuất": selected.RecommendedAction,
        })
        st.caption("Thang chuẩn hóa: review 3–4.5 sao; OTD/bàn giao 80–97%; trễ 14–1 ngày; hủy 2–0%.")
        st.caption("Olist không có thời điểm hủy; tỷ lệ hủy dùng trạng thái cuối nguồn, không phải trạng thái tại ngày mô phỏng.")

    action = st.selectbox("Hành động hỗ trợ mô phỏng",
        ["Nhắc nhở", "Lộ trình cải thiện 30 ngày", "Rà soát hiệu suất", "Cân nhắc hạn chế hiển thị"],
        key="seller_action")
    comment = st.text_input("Ghi chú", key="seller_action_note")
    if st.button("Ghi nhận hỗ trợ seller", type="primary", key="seller_action_submit"):
        selected_seller = str(sellers.iloc[selected_index].SellerId)
        add_sim_action(action, route, selected_seller, comment)
        st.success("Đã ghi nhận hành động mô phỏng; chưa áp dụng chế tài thật.")

def render_main(history: pd.DataFrame, screen: str, selected_route: str):
    if screen != "Route Overview":
        st.session_state.selected_route = selected_route
        st.session_state.detail_route = selected_route
    st.markdown("""<section class="hero"><div class="eyebrow">Olist · logistics control tower</div>
    <h1>RouteOps · Theo dõi giao hàng theo tuyến</h1>
    <p>Olist lịch sử · 20 giây = 1 ngày mô phỏng.</p></section>""", unsafe_allow_html=True)

    render_clock()
    sim_date = pd.Timestamp(st.session_state.sim_date).normalize()
    _, completed, ongoing = asof_groups(history, sim_date)
    route_completed = completed[completed.RouteEligible].copy()
    rollup = make_route_queue(history, route_completed, ongoing, sim_date)
    invalid_route_orders = int(completed.OrderId.nunique() - route_completed.OrderId.nunique())
    if screen != "Seller Performance":
        st.caption(f"Mốc dữ liệu: {sim_date:%d/%m/%Y} · loại {invalid_route_orders:,} đơn nhiều seller/thiếu bang khỏi KPI tuyến.")

    if rollup.empty:
        st.info("No routes can be calculated at this simulated date.")
        return
    if screen == "Route Overview":
        screen_overview(history, completed, ongoing, rollup, sim_date)
    elif screen == "Route Detail":
        screen_route_detail(history, route_completed, ongoing, rollup, sim_date)
    else:
        screen_sellers(history, selected_route, sim_date)

    if screen in {"Route Detail", "Seller Performance"}:
        with st.expander("Simulated action log", expanded=False):
            actions = st.session_state.get("sim_actions", [])
            if actions:
                st.dataframe(pd.DataFrame(actions), hide_index=True, use_container_width=True)
            else:
                st.caption("No simulated actions recorded in this session.")


def render_app():
    init_clock()
    try:
        history = get_history()
    except Exception as exc:
        logging.exception("Could not load MySQL Olist history")
        st.error(f"Không tải được dữ liệu MySQL: {type(exc).__name__}: {exc}")
        st.info("Kiểm tra MySQL `olist_bi_group08`, mật khẩu `.mysql-password` và các bảng staging/DW.")
        return


    if history.attrs.get("data_source") == "CSV fallback":
        if snapshot_path() == FALLBACK_HISTORY_PATH:
            snapshot_time = pd.Timestamp(FALLBACK_HISTORY_PATH.stat().st_mtime, unit="s")
            st.warning(
                "MySQL unavailable. Using the local CSV backup "
                f"(saved {snapshot_time:%d/%m/%Y %H:%M}); data may be stale. "
                "Reload after MySQL is available to fetch current data."
            )
        else:
            # Trên Streamlit Cloud: dữ liệu là bản chụp từ MySQL của nhóm.
            st.sidebar.caption("Dữ liệu: snapshot Olist xuất từ MySQL của nhóm.")

    route_options = sorted(history.loc[history.RouteEligible, "RouteId"].dropna().unique().tolist())
    if not route_options:
        st.error("Không tìm thấy tuyến hợp lệ trong dữ liệu Olist.")
        return
    current_route = st.session_state.get("routeops_selected_route", route_options[0])
    if current_route not in route_options:
        current_route = route_options[0]
    screen = st.sidebar.radio("RouteOps", ["Route Overview", "Route Detail", "Seller Performance"],
                              key="routeops_screen")
    if screen == "Route Overview":
        selected_route = current_route
    else:
        selected_route = st.sidebar.selectbox("Selected route", route_options,
            index=route_options.index(current_route), key="routeops_selected_route")
    main_view = render_main
    if st.session_state.get("sim_playing", False):
        main_view = st.fragment(run_every="5s")(render_main)
    main_view(history, screen, selected_route)
    if st.session_state.get("route_ownership_dialog_open"):
        route_ownership_dialog()


render_app()
