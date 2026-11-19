"""Read-only checks for the canonical MySQL and PBIP project artifacts."""

from __future__ import annotations

import ast
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PBIP_ROOT = ROOT / "powerbi/pbip_project"
REQUIRED = (
    "README.md", "AGENTS.md", "requirements-etl.txt", "requirements-forecast.txt",
    "scripts/build_mysql_dw.py", "scripts/run_mysql_eda.py",
    "scripts/export_mysql_evidence.py", "scripts/mysql_dss.py",
    "scripts/forecast_late_delivery.py", "scripts/replay_olist_mysql.py",
    "scripts/audit_mysql_schema.py",
    "scripts/streamlit_late_risk_demo.py", "scripts/streamlit_dss_app.py",
    "scripts/streamlit_dss_core.py", "scripts/streamlit_dss_data.py",
    "scripts/export_streamlit_snapshot.py",
    "scripts/run_mysql_demo_cycle.py",
    "document/Demo (2).pdf", "document/Demo (3).pdf",
    "docs/giai-thich-demo-streamlit.md",
    "sql/mysql/01_schema.sql", "sql/mysql/02_transform.sql",
    "sql/mysql/03_views.sql", "sql/mysql/04_operational_replay.sql",
    "diagrams/olist-bi-dss-framework.drawio",
    "diagrams/olist-mysql-architecture.drawio",
    "docs/evidence/mysql/overview.csv", "docs/evidence/mysql/reconciliation.csv",
    "docs/evidence/mysql/schema_inventory.csv",
    "docs/evidence/mysql/eda/README.md",
    "docs/evidence/mysql/forecast_late_delivery/actionable_comparison.csv",
    "powerbi/pbip_project/G8_Olist_Overview_MySQL.pbip",
)


def validate() -> list[str]:
    errors = [f"Missing: {name}" for name in REQUIRED if not (ROOT / name).is_file()]
    for path in (ROOT / "scripts").glob("*.py"):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            errors.append(f"Invalid Python {path.name}: {exc}")
    for path in (ROOT / "diagrams").glob("*.drawio"):
        try:
            ET.parse(path)
        except (OSError, ET.ParseError) as exc:
            errors.append(f"Invalid draw.io {path.name}: {exc}")
    try:
        json.loads((PBIP_ROOT / "G8_Olist_Overview_MySQL.pbip").read_text(encoding="utf-8"))
        report = PBIP_ROOT / "G8_Olist_Overview_MySQL.Report/definition"
        pages = [json.loads(p.read_text(encoding="utf-8")).get("displayName")
                 for p in (report / "pages").glob("*/page.json")]
        if len(pages) != 6 or len(set(pages)) != 6:
            errors.append(f"Expected six distinct Power BI pages, got {pages}")
        model = PBIP_ROOT / "G8_Olist_Overview_MySQL.SemanticModel/definition/tables"
        sources = "\n".join(p.read_text(encoding="utf-8") for p in model.glob("*.tmdl"))
        if sources.count("MySQL.Database(") != 12 or "Sql.Database(" in sources:
            errors.append("PBIP must contain 12 MySQL sources and no SQL Server source")
        if "Table.TransformColumnTypes" not in sources:
            errors.append("PBIP Boolean conversion is missing")
        scripts = PBIP_ROOT / "G8_Olist_Overview_MySQL.SemanticModel/TMDLScripts"
        if any("Sql.Database(" in p.read_text(encoding="utf-8")
               for p in scripts.glob("*.tmdl")):
            errors.append("PBIP still contains a legacy SQL Server TMDL script")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"Cannot inspect PBIP: {exc}")
    eda = ROOT / "docs/evidence/mysql/eda"
    for name in ("bq1_late_month.csv", "bq2_review_delay_bucket.csv",
                 "bq3_seller_candidates.csv", "bq4_category_growth_review.csv",
                 "bq5_monthly_orders_gmv_all.csv"):
        if not (eda / name).is_file():
            errors.append(f"Missing EDA evidence: {name}")
    if len(list((ROOT / "notebooks/eda_output").glob("*.png"))) < 5:
        errors.append("Expected at least five EDA figures")
    for path in [ROOT / "README.md", ROOT / "PROJECT_MAP.md", *
                 (ROOT / "docs").rglob("*.md")]:
        content = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", content):
            target = target.strip("<>").split("#", 1)[0]
            if not target or "://" in target or target.startswith("C:/"):
                continue
            if not (path.parent / target).exists():
                errors.append(f"Broken link in {path.relative_to(ROOT)}: {target}")
    return errors


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("Project validation failed:")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)
    print("Project validation passed: MySQL pipeline, EDA, PBIP, Streamlit.")
