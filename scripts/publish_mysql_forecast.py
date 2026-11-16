"""Build the ForecastMonthly import table used by the six-page Power BI model."""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pymysql
from statsmodels.tsa.holtwinters import SimpleExpSmoothing

ROOT = Path(__file__).resolve().parents[1]
MONTHLY_SQL = """
SELECT DATE_FORMAT(d.FullDate,'%Y-%m') AS Month, COUNT(*) AS Orders,
       SUM(f.GMV) AS GMV
FROM FactOrderDelivery f JOIN DimDate d ON d.DateKey=f.PurchaseDateKey
WHERE d.FullDate BETWEEN '2017-01-01' AND '2018-08-31'
GROUP BY DATE_FORMAT(d.FullDate,'%Y-%m') ORDER BY Month
"""
DDL = """
CREATE TABLE IF NOT EXISTS PowerBIForecastMonthly (
  MonthStart DATE NOT NULL, Metric VARCHAR(12) NOT NULL,
  Actual DOUBLE NULL, Fitted_SES DOUBLE NULL, Backtest_SES DOUBLE NULL,
  Forecast_SES DOUBLE NULL, Lower95 DOUBLE NULL, Upper95 DOUBLE NULL,
  Peak_Scenario DOUBLE NULL, Alpha DOUBLE NULL, K_peak DOUBLE NULL,
  MAPE_Backtest_pct DOUBLE NULL, `Set` VARCHAR(12) NOT NULL,
  PRIMARY KEY (MonthStart,Metric)
) ENGINE=InnoDB
"""
INSERT = """
INSERT INTO PowerBIForecastMonthly
(MonthStart,Metric,Actual,Fitted_SES,Backtest_SES,Forecast_SES,Lower95,
 Upper95,Peak_Scenario,Alpha,K_peak,MAPE_Backtest_pct,`Set`)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
"""


def make_rows(months: list[str], metric: str, values: np.ndarray) -> list[tuple]:
    if len(values) != 20 or months != pd.period_range('2017-01', '2018-08', freq='M').astype(str).tolist():
        raise ValueError("Expected all 20 months from January 2017 through August 2018")
    train, test = values[:-3], values[-3:]
    fit_train = SimpleExpSmoothing(train, initialization_method='estimated').fit()
    backtest = fit_train.forecast(3)
    mape = float(np.mean(np.abs(test - backtest) / np.maximum(np.abs(test), 1)) * 100)
    fit = SimpleExpSmoothing(values, initialization_method='estimated').fit()
    future = fit.forecast(3)
    residual_sd = float(np.std(values - fit.fittedvalues, ddof=1))
    alpha = float(fit.params['smoothing_level'])
    k_peak = float(values[10] / np.mean(values[7:10]))  # Nov 2017 / Aug-Oct 2017
    rows = []
    for i, month in enumerate(months):
        rows.append((month + '-01', metric, float(values[i]), float(fit.fittedvalues[i]),
                     float(backtest[i - 17]) if i >= 17 else None,
                     None, None, None, None, alpha, k_peak, mape, 'Historical'))
    for i, month in enumerate(('2018-09', '2018-10', '2018-11')):
        prediction = float(future[i])
        rows.append((month + '-01', metric, None, None, None, prediction,
                     prediction - 1.96 * residual_sd, prediction + 1.96 * residual_sd,
                     prediction * k_peak if i == 2 else None,
                     alpha, k_peak, mape, 'Future'))
    return rows


def publish(args: argparse.Namespace) -> None:
    password = os.environ.get('OLIST_MYSQL_PASSWORD')
    password_file = ROOT / '.mysql-password'
    if password is None and password_file.is_file():
        password = password_file.read_text(encoding='utf-8-sig').rstrip('\r\n')
    if password is None:
        password = getpass.getpass('MySQL password (input hidden): ')
    connection = pymysql.connect(host=args.host, port=args.port, user=args.user,
                                 password=password, database=args.schema,
                                 charset='utf8mb4', connect_timeout=10)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT Status FROM ETLRun ORDER BY RunId DESC LIMIT 1")
            if cursor.fetchone()[0] != 'SUCCEEDED':
                raise ValueError('Latest warehouse ETL must have succeeded')
            cursor.execute(MONTHLY_SQL)
            data = cursor.fetchall()
        months = [row[0] for row in data]
        rows = []
        for metric, index in (('Orders', 1), ('GMV', 2)):
            values = np.asarray([float(row[index]) for row in data], dtype=float)
            rows.extend(make_rows(months, metric, values))
        with connection.cursor() as cursor:
            cursor.execute(DDL)
            cursor.execute('DELETE FROM PowerBIForecastMonthly')
            cursor.executemany(INSERT, rows)
        connection.commit()
        print(f'PowerBIForecastMonthly: {len(rows)} rows (40 historical, 6 future)')
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', default='root')
    parser.add_argument('--schema', default='olist_bi_group08')
    publish(parser.parse_args())
