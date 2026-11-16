"""Edit a Power BI Desktop PBIP project in its supported text-file format.

Save the original working PBIX as a PBIP in Power BI Desktop first. This tool
updates the PBIR visual definitions and the semantic model definition in that
project. It never rewrites a PBIX archive.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEASURES = {
    'BQ4 GMV 2017 Jan-Aug': (
        "CALCULATE([GMV], REMOVEFILTERS('DimDate'), 'DimDate'[YearNumber] = 2017, "
        "'DimDate'[MonthNumber] >= 1, 'DimDate'[MonthNumber] <= 8)", '#,0'),
    'BQ4 GMV 2018 Jan-Aug': (
        "CALCULATE([GMV], REMOVEFILTERS('DimDate'), 'DimDate'[YearNumber] = 2018, "
        "'DimDate'[MonthNumber] >= 1, 'DimDate'[MonthNumber] <= 8)", '#,0'),
    'BQ4 Reviewed Orders 2018 Jan-Aug': (
        "CALCULATE(COUNTROWS(FILTER(VALUES('FactOrderItem'[OrderId]), NOT "
        "ISBLANK(CALCULATE(MAX('FactOrderItem'[ReviewScore]))))), "
        "REMOVEFILTERS('DimDate'), 'DimDate'[YearNumber] = 2018, "
        "'DimDate'[MonthNumber] >= 1, 'DimDate'[MonthNumber] <= 8)", '#,0'),
    'BQ4 Review 2018 Jan-Aug': (
        "CALCULATE([Review (Item)], REMOVEFILTERS('DimDate'), "
        "'DimDate'[YearNumber] = 2018, 'DimDate'[MonthNumber] >= 1, "
        "'DimDate'[MonthNumber] <= 8)", '0.000'),
    'BQ4 GMV Growth %': (
        'VAR PriorGMV = [BQ4 GMV 2017 Jan-Aug] '
        'VAR CurrentGMV = [BQ4 GMV 2018 Jan-Aug] '
        'VAR Reviews = [BQ4 Reviewed Orders 2018 Jan-Aug] '
        'RETURN IF(PriorGMV >= 10000 && CurrentGMV >= 20000 && Reviews >= 100, '
        'DIVIDE(CurrentGMV - PriorGMV, PriorGMV))', '0.00%'),
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def refs(visual: dict) -> set[str]:
    return {
        p.get('queryRef', '')
        for bucket in visual.get('visual', {}).get('query', {}).get('queryState', {}).values()
        for p in bucket.get('projections', [])
    }


def find(page: Path, required: str, kind: str | None = None) -> tuple[Path, dict]:
    for path in page.glob('visuals/*/visual.json'):
        visual = load(path)
        if required in refs(visual) and (
            kind is None or visual.get('visual', {}).get('visualType') == kind
        ):
            return path, visual
    raise ValueError(f'Cannot find {required} ({kind}) in {page}')


def measure(name: str, label: str | None = None) -> dict:
    return {
        'field': {'Measure': {'Expression': {'SourceRef': {'Entity': 'FactOrderItem'}},
                              'Property': name}},
        'queryRef': f'FactOrderItem.{name}',
        'nativeQueryRef': label or name,
    }


def patch_model(model: Path) -> str:
    tmdl = model / 'definition' / 'tables' / 'FactOrderItem.tmdl'
    if tmdl.is_file():
        text = tmdl.read_text(encoding='utf-8-sig')
        if not re.search(r'^table FactOrderItem\s*$', text, re.MULTILINE):
            raise ValueError('Unexpected FactOrderItem.tmdl table header')
        for name, (dax, fmt) in MEASURES.items():
            if f"measure '{name}'" not in text:
                text += f"\n\tmeasure '{name}' = {dax}\n\t\tformatString: {fmt}\n"
        return text
    bim = model / 'model.bim'
    if bim.is_file():
        data = load(bim)
        tables = data.get('model', {}).get('tables', [])
        table = next((t for t in tables if t.get('name') == 'FactOrderItem'), None)
        if table is None:
            raise ValueError('FactOrderItem missing from model.bim')
        existing = {m['name'] for m in table.get('measures', [])}
        for name, (dax, fmt) in MEASURES.items():
            if name not in existing:
                table.setdefault('measures', []).append(
                    {'name': name, 'expression': dax, 'formatString': fmt})
        return json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    raise FileNotFoundError('Neither TMDL FactOrderItem.tmdl nor model.bim found')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('project_root', type=Path)
    args = parser.parse_args()
    project = args.project_root.resolve()
    if not project.is_relative_to(ROOT) or not project.is_dir():
        raise ValueError('PBIP project must be an existing folder inside the workspace')
    projects = list(project.glob('*.pbip'))
    reports = list(project.glob('*.Report'))
    models = list(project.glob('*.SemanticModel'))
    if len(projects) != 1 or len(reports) != 1 or len(models) != 1:
        raise ValueError('Expected one .pbip, one .Report and one .SemanticModel')
    definition = reports[0] / 'definition'
    pages_meta = load(definition / 'pages' / 'pages.json')
    if len(pages_meta['pageOrder']) != 6:
        raise ValueError('Expected six report pages')
    pages = {
        load(p / 'page.json')['displayName']: p
        for p in (definition / 'pages').iterdir() if (p / 'page.json').is_file()
    }
    overview = pages['Executive Overview']
    product = pages['Product/Category Analysis']
    changed: dict[Path, str] = {}

    # BQ5: GMV forecast beside the existing order forecast.
    _, orders = find(overview, 'ForecastMonthly.FC Orders Forecast', 'lineChart')
    donut_path, donut = find(overview, 'FactOrderItem.GMV by Grade', 'donutChart')
    gmv = copy.deepcopy(orders)
    gmv['name'] = donut['name']
    gmv['position'] = donut['position']
    gmv = json.loads(json.dumps(gmv, ensure_ascii=False)
                     .replace('FC Orders', 'FC GMV')
                     .replace('Dự báo số đơn', 'Dự báo GMV'))
    changed[donut_path] = json.dumps(gmv, ensure_ascii=False, separators=(',', ':'))

    # BQ4: like-for-like Jan-Aug growth versus review.
    scatter_path, scatter = find(product, 'FactOrderItem.Avg_Unit_Price', 'scatterChart')
    state = scatter['visual']['query']['queryState']
    state['X']['projections'] = [measure('BQ4 GMV Growth %', 'GMV growth Jan-Aug YoY')]
    state['Y']['projections'] = [measure('BQ4 Review 2018 Jan-Aug', 'Review Jan-Aug 2018')]
    changed[scatter_path] = json.dumps(scatter, ensure_ascii=False, separators=(',', ':'))

    table_path, table = find(product, 'DimProduct.CategoryName', 'tableEx')
    category = table['visual']['query']['queryState']['Values']['projections'][0]
    table['visual']['query']['queryState']['Values']['projections'] = [
        category,
        measure('BQ4 GMV 2017 Jan-Aug', 'GMV Jan-Aug 2017'),
        measure('BQ4 GMV 2018 Jan-Aug', 'GMV Jan-Aug 2018'),
        measure('BQ4 GMV Growth %', 'GMV growth YoY'),
        measure('BQ4 Review 2018 Jan-Aug', 'Review Jan-Aug 2018'),
    ]
    changed[table_path] = json.dumps(table, ensure_ascii=False, separators=(',', ':'))

    for old, new, label in [
        ('FactOrderItem.Total_Products_Sold', 'BQ4 Reviewed Orders 2018 Jan-Aug',
         'Reviewed orders Jan-Aug 2018'),
        ('FactOrderItem.Avg_GMV_Per_Seller', 'BQ4 GMV Growth %', 'GMV growth Jan-Aug YoY'),
        ('FactOrderItem.Avg_Unit_Price', 'BQ4 GMV 2018 Jan-Aug', 'GMV Jan-Aug 2018'),
        ('FactOrderItem.Avg_Seller_Review', 'BQ4 Review 2018 Jan-Aug', 'Review Jan-Aug 2018'),
    ]:
        path, card = find(product, old, 'cardVisual')
        bucket = next(iter(card['visual']['query']['queryState'].values()))
        bucket['projections'] = [measure(new, label)]
        changed[path] = json.dumps(card, ensure_ascii=False, separators=(',', ':'))

    # The inherited Product page header was still labeled Executive Overview.
    headers = [path for path in product.glob('visuals/*/visual.json')
               if load(path).get('visual', {}).get('visualType') == 'textbox'
               and 'Executive Overview' in path.read_text(encoding='utf-8')]
    if len(headers) != 1:
        raise ValueError(f'Expected one Product header, found {len(headers)}')
    header = load(headers[0])
    header = json.loads(json.dumps(header, ensure_ascii=False)
                        .replace('Executive Overview', 'Product/Category Analysis'))
    changed[headers[0]] = json.dumps(header, ensure_ascii=False, separators=(',', ':'))

    model_path = (models[0] / 'definition' / 'tables' / 'FactOrderItem.tmdl')
    if not model_path.is_file():
        model_path = models[0] / 'model.bim'
    changed[model_path] = patch_model(models[0])
    if not model_path.is_file():
        raise FileNotFoundError(model_path)

    # Validate all outputs before writing any project file.
    for path, body in changed.items():
        if path.suffix == '.json' or path.suffix == '.bim':
            json.loads(body)
    assert 'ForecastMonthly.FC GMV Forecast' in refs(gmv)
    assert 'FactOrderItem.BQ4 GMV Growth %' in refs(scatter)
    backup = ROOT / 'temp' / 'pbip_bq_backup'
    for path in changed:
        dest = backup / path.relative_to(project)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    for path, body in changed.items():
        path.write_text(body, encoding='utf-8', newline='\n')
    print(f'Patched {len(changed)} PBIP files; backup: {backup}')


if __name__ == '__main__':
    main()
