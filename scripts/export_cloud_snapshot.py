"""Xuất dữ liệu từ MySQL thành file nén để app Streamlit chạy được trên Streamlit Cloud.

Chạy trên máy có MySQL:  python scripts/export_cloud_snapshot.py
Kết quả: data/streamlit/streamlit_history_fallback.csv.gz (commit file này lên GitHub).
"""
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from streamlit_dss_data import historical_deliveries, route_lookup  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "streamlit" / "streamlit_history_fallback.csv.gz"

history = historical_deliveries()
lookup = route_lookup()[["OrderId", "SellerState", "SellerLatitude", "SellerLongitude",
                         "CustomerState", "CustomerLatitude", "CustomerLongitude"]]
frame = history.merge(lookup, on="OrderId", how="left", validate="one_to_one")
OUT.parent.mkdir(parents=True, exist_ok=True)
frame.to_csv(OUT, index=False, date_format="%Y-%m-%d %H:%M:%S",
             compression={"method": "gzip", "mtime": 0})
print(f"Đã ghi {len(frame):,} đơn vào {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")
