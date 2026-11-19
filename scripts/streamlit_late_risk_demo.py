"""Canonical Streamlit entry point for the three-screen Olist route control tower."""

import sys
import runpy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Streamlit reruns this entry point for every browser session and interaction.
# A normal import would reuse sys.modules and leave subsequent runs blank.
runpy.run_path(str(Path(__file__).with_name("streamlit_dss_app.py")), run_name="__main__")
