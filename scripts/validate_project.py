"""Run local, read-only consistency checks for the Olist BI/DSS repository."""

from __future__ import annotations

import ast
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PATHS = (
    "README.md",
    "requirements.txt",
    "requirements-etl.txt",
    "notebooks/olist_bi_dss.ipynb",
    "scripts/load_staging_csv.py",
    "sql/01_create_databases.sql",
    "sql/staging/02_create_staging_tables.sql",
    "sql/staging/05_create_clean_views.sql",
    "sql/warehouse/06_create_dw_tables.sql",
    "sql/warehouse/10_master_etl.sql",
    "sql/validation/11_reconcile_dw.sql",
    "powerbi/Olist_Model.tmdl",
    "ssis/master/Master_ETL.dtsx",
)


def check_required_paths(errors: list[str]) -> None:
    for relative_path in REQUIRED_PATHS:
        if not (ROOT / relative_path).is_file():
            errors.append(f"Missing required file: {relative_path}")


def check_python(errors: list[str]) -> None:
    for path in sorted((ROOT / "scripts").glob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            errors.append(f"Invalid Python file {path.relative_to(ROOT)}: {exc}")


def check_notebook(errors: list[str]) -> None:
    path = ROOT / "notebooks" / "olist_bi_dss.ipynb"
    notebooks = sorted((ROOT / "notebooks").glob("*.ipynb"))
    if notebooks != [path]:
        names = [notebook.name for notebook in notebooks]
        errors.append(f"Expected only the canonical notebook, found: {names}")
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid notebook JSON: {exc}")
        return

    if notebook.get("nbformat") != 4 or not isinstance(notebook.get("cells"), list):
        errors.append("Notebook must use nbformat 4 and contain a cells list")
        return

    import_cells: list[int] = []
    function_cells: list[int] = []
    for index, cell in enumerate(notebook["cells"]):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        source = "".join(source) if isinstance(source, list) else source
        try:
            tree = ast.parse(source, filename=f"notebook cell {index}")
        except SyntaxError as exc:
            errors.append(f"Notebook cell {index} has invalid Python: {exc}")
            continue
        if any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body):
            import_cells.append(index)
        if any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in tree.body):
            function_cells.append(index)
        if cell.get("outputs"):
            errors.append(f"Notebook cell {index} contains saved output")

    if len(import_cells) != 1:
        errors.append(f"Expected one import cell, found {import_cells}")
    if len(function_cells) != 1:
        errors.append(f"Expected one function cell, found {function_cells}")


def check_xml_files(errors: list[str]) -> None:
    paths = list((ROOT / "ssis").rglob("*.dtsx"))
    paths.extend((ROOT / "ssis").rglob("*.dtproj"))
    paths.extend((ROOT / "diagrams").glob("*.drawio"))
    for path in sorted(paths):
        try:
            ET.parse(path)
        except (OSError, ET.ParseError) as exc:
            errors.append(f"Invalid XML {path.relative_to(ROOT)}: {exc}")


def check_documentation(errors: list[str]) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if readme.count("```") % 2:
        errors.append("README.md contains an unclosed fenced code block")
    if readme.startswith("\\#") or "\n\\##" in readme:
        errors.append("README.md contains escaped Markdown headings")


def main() -> int:
    errors: list[str] = []
    check_required_paths(errors)
    check_python(errors)
    check_notebook(errors)
    check_xml_files(errors)
    check_documentation(errors)

    if errors:
        print("Project validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Project validation passed.")
    print(f"Root: {ROOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
