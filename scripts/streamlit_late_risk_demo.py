"""Streamlit demo: two-stage Olist late-delivery warning and MySQL replay."""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import pymysql
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/mysql/forecast_late_delivery"
st.set_page_config(page_title="Olist | Cảnh báo giao trễ sớm", page_icon="📦",
                   layout="wide")
st.markdown("""<style>
div[data-testid="stMetric"]{background:#f3f6fc;border:1px solid #dce5f4;
  border-radius:10px;padding:12px 16px}
</style>""", unsafe_allow_html=True)


EVIDENCE_FILES = ["metrics.csv", "monthly_metrics.csv", "actionable_comparison.csv",
                  "test_risk_queue.csv", "handover_risk_queue.csv"]


@st.cache_data(show_spinner=False)
def load_evidence(signature):
    required = EVIDENCE_FILES
    missing = [name for name in required if not (EVIDENCE / name).is_file()]
    if missing:
        raise FileNotFoundError("Thiếu: " + ", ".join(missing) +
                                ". Chạy python scripts/forecast_late_delivery.py trước.")
    frames = {name: pd.read_csv(EVIDENCE / name) for name in required}
    expected = {
        "test_risk_queue.csv": {"OrderId", "ApprovedAt", "CarrierAt",
                                "DeliveredAt", "EstimatedAt", "Risk", "Late"},
        "handover_risk_queue.csv": {"OrderId", "CarrierAt", "DeliveredAt",
                                    "EstimatedAt", "RemainingCalendarDays",
                                    "HandoverRisk", "Late"},
    }
    for name, columns in expected.items():
        absent = columns.difference(frames[name].columns)
        if absent:
            raise ValueError(f"{name} thiếu cột {sorted(absent)}. "
                             "Chạy lại python scripts/forecast_late_delivery.py.")
    return frames


def mysql_password():
    if os.environ.get("OLIST_MYSQL_PASSWORD"):
        return os.environ["OLIST_MYSQL_PASSWORD"]
    path = ROOT / ".mysql-password"
    if path.is_file():
        return path.read_text(encoding="utf-8-sig").rstrip("\r\n")
    raise RuntimeError("Chưa có .mysql-password hoặc OLIST_MYSQL_PASSWORD")


@st.cache_data(ttl=3, show_spinner=False)
def replay_snapshot():
    con = pymysql.connect(host="127.0.0.1", port=3306, user="root",
                          password=mysql_password(), database="olist_bi_group08",
                          charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
                          connect_timeout=3)
    try:
        with con.cursor() as cur:
            cur.execute("SELECT * FROM DemoReplayCheckpoint WHERE Id=1")
            checkpoint = cur.fetchone()
            cur.execute("SELECT * FROM vw_DemoOperationalKPI")
            kpi = cur.fetchone()
            cur.execute("""SELECT OrderId,CurrentStage,LastEventAt,EstimatedAt,
                           MinutesInCurrentStage,PastEstimate
                           FROM vw_DemoOrderCurrent
                           WHERE CurrentStage='In transit'
                           ORDER BY LastEventAt DESC LIMIT 10000""")
            in_transit = pd.DataFrame(cur.fetchall())
        return checkpoint, kpi, in_transit
    finally:
        con.close()


def percent(value):
    return f"{value:.1%}"


try:
    signature = tuple((name, (EVIDENCE / name).stat().st_mtime_ns,
                       (EVIDENCE / name).stat().st_size)
                      for name in EVIDENCE_FILES if (EVIDENCE / name).is_file())
    evidence = load_evidence(signature)
except (FileNotFoundError, ValueError) as exc:
    st.error(str(exc))
    st.stop()

st.title("📦 Olist · Cảnh báo giao trễ sớm")
st.caption("Mô hình hai thời điểm: sau duyệt đơn → lúc bàn giao cho vận chuyển")
st.info("**Demo trên Olist lịch sử.** Điểm mô hình chỉ dùng để xếp ưu tiên điều tra; "
        "chưa phải xác suất giao trễ đã hiệu chuẩn. Không có đơn hàng live.")
history_tab, replay_tab, validation_tab = st.tabs([
    "Hàng đợi cảnh báo", "Micro-batch MySQL", "Kiểm thử mô hình"])

with history_tab:
    st.subheader("Phát lại hàng đợi theo ngày sự kiện")
    h = evidence["handover_risk_queue.csv"].copy()
    a = evidence["test_risk_queue.csv"].copy()
    for frame in (h, a):
        frame["PurchaseAt"] = pd.to_datetime(frame.PurchaseAt)
        frame["ApprovedAt"] = pd.to_datetime(frame.ApprovedAt)
        frame["CarrierAt"] = pd.to_datetime(frame.CarrierAt)
        frame["DeliveredAt"] = pd.to_datetime(frame.DeliveredAt)
        frame["EstimatedAt"] = pd.to_datetime(frame.EstimatedAt)
    stage = st.radio("Thời điểm chấm rủi ro", ["Sau duyệt", "Lúc bàn giao"],
                     horizontal=True)
    default_day = date(2018, 7, 15)
    if "asof_day" not in st.session_state:
        st.session_state.asof_day = default_day
    prev, next_day, date_col = st.columns([1, 1, 4])
    if prev.button("◀ Ngày trước", width="stretch"):
        st.session_state.asof_day = max(date(2018, 4, 1),
                                        st.session_state.asof_day - timedelta(days=1))
    if next_day.button("Ngày tiếp ▶", width="stretch"):
        st.session_state.asof_day = min(date(2018, 9, 30),
                                        st.session_state.asof_day + timedelta(days=1))
    with date_col:
        asof = st.date_input("Đồng hồ sự kiện lịch sử", key="asof_day",
                             min_value=date(2018, 4, 1),
                             max_value=date(2018, 9, 30))
    end = pd.Timestamp(asof) + pd.Timedelta(days=1)
    if stage == "Sau duyệt":
        visible = a[(a.ApprovedAt < end) & (a.DeliveredAt >= end) &
                    (a.CarrierAt.isna() | (a.CarrierAt >= end))].copy()
        risk_column = "Risk"
    else:
        visible = h[(h.CarrierAt < end) & (h.DeliveredAt >= end) &
                    (h.EstimatedAt.dt.normalize() >= end)].copy()
        risk_column = "HandoverRisk"
    start = pd.Timestamp(asof) - pd.Timedelta(days=30)
    if stage == "Sau duyệt":
        visible = visible[visible.ApprovedAt >= start]
    else:
        visible = visible[visible.CarrierAt >= start]
    left, middle, right = st.columns(3)
    states = sorted(visible.CustomerState.dropna().unique().tolist())
    state = left.selectbox("Bang khách nhận", ["Tất cả"] + states)
    if state != "Tất cả":
        visible = visible[visible.CustomerState == state]
    categories = sorted(visible.CategoryName.dropna().unique().tolist())
    category = middle.selectbox("Danh mục", ["Tất cả"] + categories)
    if category != "Tất cả":
        visible = visible[visible.CategoryName == category]
    share = right.slider("Chọn top bao nhiêu % đơn để kiểm tra?", 1, 30, 10)
    visible = visible.sort_values(risk_column, ascending=False)
    n = max(1, int(len(visible) * share / 100)) if len(visible) else 0
    selected = visible.head(n)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Đơn trong cửa sổ 30 ngày", f"{len(visible):,}")
    col2.metric("Đơn được ưu tiên kiểm tra", f"{len(selected):,}")
    col3.metric("Bang khách trong hàng đợi",
                f"{selected.CustomerState.nunique():,}" if len(selected) else "0")
    col4.metric("Ngày mô phỏng", asof.strftime("%d/%m/%Y"))
    st.caption("Ví dụ chọn 10% trong 1.000 đơn thì bảng chỉ hiện 100 đơn có điểm rủi ro cao nhất. "
               "Tỷ lệ này là giả định để mô phỏng khả năng kiểm tra, không phải năng lực nhân sự đã đo. "
               "Chỉ hiển thị các đơn đã tới thời điểm chấm theo đồng hồ lịch sử. "
               "Ở chế độ bàn giao, loại đơn đã quá ngày hẹn để ưu tiên cảnh báo còn có thể can thiệp.")
    if len(selected):
        show = selected.copy()
        show["Tuyến"] = show.SellerState.fillna("?") + " → " + show.CustomerState.fillna("?")
        show["Điểm ưu tiên"] = show[risk_column].round(3)
        columns = ["OrderId", "Tuyến", "CategoryName", "EstimatedAt", "Điểm ưu tiên"]
        if stage == "Lúc bàn giao":
            show["Còn trước hạn (ngày)"] = (
                show.EstimatedAt.dt.normalize() - pd.Timestamp(asof)).dt.days
            columns.insert(-1, "Còn trước hạn (ngày)")
        st.dataframe(show[columns].rename(columns={"OrderId": "Mã đơn",
                   "CategoryName": "Danh mục", "EstimatedAt": "Ngày hẹn"}),
                   hide_index=True, width="stretch", height=380)
        if st.checkbox("Hiện kết quả sau khi giao (chỉ để kiểm thử)"):
            st.warning("Cột dưới đây là nhãn biết **sau khi giao**, không được dùng "
                       "làm đầu vào lúc chấm rủi ro.")
            st.write(f"Trong {len(selected):,} đơn đang ưu tiên, "
                     f"{int(selected.Late.sum()):,} đơn về sau giao trễ "
                     f"({selected.Late.mean():.1%}).")
    else:
        st.write("Chưa có đơn phù hợp với đồng hồ và bộ lọc này.")

with replay_tab:
    st.subheader("Dữ liệu sự kiện MySQL đang phát lại")
    st.caption("Tab này đọc cùng `Demo*` và `vw_DemoOperationalKPI` với dashboard web cũ. "
               "Tự hỏi lại MySQL mỗi 5 giây khi app đang mở.")
    with st.expander("Vì sao có 23.983 sự kiện nhưng chỉ 6.130 đơn?", expanded=False):
        st.markdown("""Mẫu mặc định là các đơn mua trong **07/2018**. Có **6.156 đơn nguồn**;
        **26 đơn** bị loại vì mốc giao không hợp lệ, nên còn **6.130 đơn** được phát lại.
        Mỗi đơn có thể tạo bốn sự kiện: đặt, duyệt, bàn giao cho vận chuyển, giao khách.
        Trong 6.130 đơn, **537 mốc bàn giao sai thứ tự** bị bỏ. Vì vậy:

        **6.130 đặt + 6.130 duyệt + 5.593 bàn giao + 6.130 giao = 23.983 sự kiện.**

        Một lô nạp tối đa 500 **sự kiện**, không phải 500 đơn; có 47 lô đủ 500
        sự kiện và lô cuối 483 sự kiện. Con số trên áp dụng cho cấu hình nguồn
        mặc định tháng 07/2018; nếu đổi khoảng ngày thì tổng sẽ khác.""")

    @st.fragment(run_every="5s")
    def live_panel():
        try:
            checkpoint, kpi, transit = replay_snapshot()
        except Exception as exc:
            st.warning("Chưa đọc được micro-batch MySQL. Chạy "
                       "`python scripts/run_mysql_demo_cycle.py` nếu muốn xem dữ liệu thay đổi. "
                       f"Chi tiết: {type(exc).__name__}: {exc}")
            return
        if not checkpoint:
            st.warning("Chưa khởi tạo bảng DemoReplayCheckpoint.")
            return
        kpi = kpi or {}
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sự kiện đã phát", f"{checkpoint.get('NextEventIndex', 0):,}")
        c2.metric("Tổng sự kiện", f"{checkpoint.get('TotalEvents', 0):,}")
        c3.metric("Đơn đã xuất hiện", f"{kpi.get('VisibleOrders', 0):,}")
        c4.metric("Đã giao", f"{kpi.get('DeliveredOrders', 0):,}")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Chờ duyệt", f"{kpi.get('AwaitingApprovalOrders', 0):,}")
        s2.metric("Chờ bàn giao", f"{kpi.get('AwaitingCarrierOrders', 0):,}")
        s3.metric("Đang vận chuyển", f"{kpi.get('InTransitOrders', 0):,}")
        s4.metric("Chưa giao, quá ngày hẹn", f"{kpi.get('PastEstimateOrders', 0):,}")
        total = checkpoint.get('TotalEvents') or 0
        if total:
            st.progress(min(1.0, (checkpoint.get('NextEventIndex') or 0) / total),
                        text="Tiến độ phát lại sự kiện lịch sử")
        st.caption(f"Giờ sự kiện: {checkpoint.get('LastEventAt', '—')} · "
                   f"Lô nạp gần nhất UTC: {checkpoint.get('LastBatchAtUtc', '—')} · "
                   f"Đã giao trễ: {kpi.get('LateDeliveredOrders', 0):,}")
        if transit.empty:
            st.write("Hiện chưa có đơn đang vận chuyển trong batch này.")
            return
        scores = evidence["handover_risk_queue.csv"][["OrderId", "SellerState",
            "CustomerState", "CategoryName", "RemainingCalendarDays", "HandoverRisk"]]
        live = transit.merge(scores, on="OrderId", how="inner")
        live["DaysLeftNow"] = (
            pd.to_datetime(live.EstimatedAt).dt.normalize() -
            pd.to_datetime(live.LastEventAt).dt.normalize()).dt.days
        live = live[live.DaysLeftNow > 0]
        if live.empty:
            st.write("Chưa có đơn đang vận chuyển thuộc mẫu dự báo và còn trước hạn.")
            return
        live = live.sort_values("HandoverRisk", ascending=False).head(20).copy()
        live["Tuyến"] = live.SellerState + " → " + live.CustomerState
        live["Điểm ưu tiên"] = live.HandoverRisk.round(3)
        st.dataframe(live[["OrderId", "Tuyến", "CategoryName", "LastEventAt",
                            "EstimatedAt", "Điểm ưu tiên"]]
                     .rename(columns={"OrderId": "Mã đơn", "CategoryName": "Danh mục",
                                      "LastEventAt": "Mốc mới nhất",
                                      "EstimatedAt": "Ngày hẹn"}),
                     hide_index=True, width="stretch")
        st.caption("Dự báo chỉ có cho mẫu đơn một sản phẩm thuộc tập kiểm thử; "
                   "micro-batch phát lại đơn mua 07/2018, còn tập điểm là đơn mua "
                   "04–08/2018 đã giao và đủ nhãn. Đơn chưa có kết quả giao chưa "
                   "được chấm điểm trong demo offline này.")

    live_panel()

with validation_tab:
    st.subheader("Mô hình có còn hữu ích trên dữ liệu về sau?")
    comparison = evidence["actionable_comparison.csv"].copy()
    comparison = comparison[comparison.Cohort == "BeforePromise"]
    comparison["Thời điểm"] = comparison.Stage.map({
        "AfterApproval": "Sau duyệt", "AtCarrierHandover": "Lúc bàn giao"})
    comparison["Tìm được đơn trễ (%)"] = 100 * comparison.Top10Capture
    fig = px.bar(comparison, x="Thời điểm", y="Tìm được đơn trễ (%)",
                 color="Thời điểm", text="Tìm được đơn trễ (%)",
                 color_discrete_sequence=["#4e79a7", "#e15759"])
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.add_hline(y=10, line_dash="dash", line_color="gray",
                  annotation_text="Chọn ngẫu nhiên 10%")
    fig.update_layout(showlegend=False, yaxis_range=[0, 45])
    st.plotly_chart(fig)
    st.caption("So sánh có điều kiện trên 27.639 đơn mua 04–08/2018 đã giao, "
               "một sản phẩm, có mốc bàn giao hợp lệ và còn trong hạn lúc bàn giao. "
               "Lúc duyệt chưa thể biết đơn nào về sau thuộc nhóm này; kết quả "
               "sau duyệt là đối chứng hồi cứu trên cùng đơn. Top 10% là giả định "
               "năng lực kiểm tra, không phải ngưỡng tối ưu.")
    shown = comparison[["Thời điểm", "Orders", "LateRate", "Top10Selected",
                        "Top10LateFound", "Top10Precision", "Top10Capture",
                        "Top10Lift"]].copy()
    shown["LateRate"] = (100 * shown.LateRate).round(2)
    shown["Top10Precision"] = (100 * shown.Top10Precision).round(2)
    shown["Top10Capture"] = (100 * shown.Top10Capture).round(2)
    shown["Top10Lift"] = shown.Top10Lift.round(2)
    st.dataframe(shown.rename(columns={"Orders": "Số đơn", "LateRate": "Tỷ lệ trễ nền (%)",
                 "Top10Selected": "Đơn được kiểm tra", "Top10LateFound": "Đơn trễ tìm được",
                 "Top10Precision": "Precision@10% (%)",
                 "Top10Capture": "Recall@10% (%)", "Top10Lift": "Lift@10%"}),
                 hide_index=True, width="stretch")
    monthly = evidence["monthly_metrics.csv"].copy()
    monthly["Top10CapturePct"] = 100 * monthly.Top10Capture
    fig2 = px.line(monthly, x="Month", y="Top10CapturePct", markers=True,
                   labels={"Month": "Tháng đặt hàng",
                           "Top10CapturePct": "Đơn trễ tìm được trong top 10% (%)"})
    fig2.add_hline(y=10, line_dash="dash", line_color="gray")
    st.plotly_chart(fig2)
    st.dataframe(evidence["metrics.csv"].round(3), hide_index=True,
                 width="stretch")
    st.caption("Micro-batch tháng 7/2018 và quần thể kiểm thử 04–08/2018 có mẫu số khác nhau. "
               "Đơn chưa có kết quả giao bị loại trước khi chấm điểm offline và đánh giá. "
               "Các tỷ lệ chỉ đo khả năng đưa đơn trễ lên trước trong backtest; "
               "chưa chứng minh can thiệp làm giảm giao trễ. "
               "Kết quả chia ngẫu nhiên chỉ để đối chiếu hồi cứu. "
               "Điểm rủi ro chưa được hiệu chuẩn thành xác suất. "
               "Hiệu quả thay đổi theo tháng; không tự động dùng mô hình cho quyết định xử phạt.")
