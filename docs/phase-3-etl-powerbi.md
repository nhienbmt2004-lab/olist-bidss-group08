# Phase 3 — Warehouse ETL and Power BI

## One-time setup

Run these scripts in SSMS in order after the Phase 2 staging views and empty warehouse schema exist:

1. `sql/warehouse/07_create_etl_support.sql` — audit and reconciliation tables.
2. `sql/warehouse/08_load_dimensions.sql` — one stored procedure for each dimension.
3. `sql/warehouse/09_load_facts.sql` — one stored procedure for each fact.
4. `sql/validation/11_reconcile_dw.sql` — comparison of staging and DW.
5. `sql/warehouse/10_master_etl.sql` — ordered execution and run logging.

The SQL transformations perform source lookups, type conversion and derived columns. Missing required dimension/date keys stop the load with an error. Nullable geography/category keys remain `NULL` if a source mapping is unavailable. Facts are rebuilt from the current staging snapshot on each run; dimensions are updated or inserted by business key. Individual SSIS Execute SQL packages are available under `ssis/dimensions/` and `ssis/facts/` for development and testing; the automated master calls the same procedures in dependency order with centralized logging.

## Run the ETL

Download the nine public Olist CSVs into `data/raw/olist` (the Kaggle ZIP is
`https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce`). From the
repository root in PowerShell, with Python, `pyodbc`, ODBC Driver 17 for SQL
Server, `sqlcmd` and SSIS `dtexec.exe` installed:

```powershell
.\ssis\master\Run-ETL.ps1 -SqlServer localhost -RawDataDirectory .\data\raw\olist
```

To reuse staging data already loaded:

```powershell
.\ssis\master\Run-ETL.ps1 -SqlServer localhost -SkipStaging
```

The runner loads all nine UTF-8 CSVs with `scripts/load_staging_csv.py`, creates
staging indexes/updates statistics with `sql/staging/03_create_staging_indexes.sql`,
then runs `ssis/master/Master_ETL.dtsx`. The original `STG_*.dtsx` packages
remain in the project, but their source/destination code-page mismatch prevents
reliable execution on this machine. The master package invokes
`usp_RunWarehouseETL`, which validates staging, loads six dimensions, loads
four facts, reconciles totals and records each step in `Olist_DW.dbo.ETLRun`,
`ETLStepLog` and `ETLReconciliation`. A failure stops the sequence. The SSIS
master connection currently targets `localhost`; update its connection manager
before running against a different SQL Server.

`Master_ETL.dtsx` can also be run directly when staging has already been loaded. If `dtexec.exe` is not in `PATH`, pass `-DtexecPath` to the PowerShell runner.

## Verify a run

```sql
SELECT TOP (10) * FROM Olist_DW.dbo.ETLRun ORDER BY RunId DESC;
SELECT * FROM Olist_DW.dbo.ETLStepLog
WHERE RunId = (SELECT MAX(RunId) FROM Olist_DW.dbo.ETLRun) ORDER BY StepId;
SELECT * FROM Olist_DW.dbo.ETLReconciliation
WHERE RunId = (SELECT MAX(RunId) FROM Olist_DW.dbo.ETLRun) ORDER BY ReconciliationId;
```

Reconciliation compares Orders, OrderItems, Payments, Reviews, GMV in both order and item facts, Freight, PaymentValue and customer/seller/product counts. Any difference above 0.01 causes the run to fail.

## Power BI semantic model and KPI

Open a blank report in Power BI Desktop, then go to **Model → TMDL view**. Open `powerbi/Olist_Model.tmdl`, replace `localhost` with the SQL Server instance hosting `Olist_DW`, paste the script and select **Apply**. Set SQL Server credentials when prompted and refresh. The script defines import tables, 17 relationships, date/geography/category hierarchies and the requested measures.

`CustomerGeography` and `SellerGeography` are two semantic roles of the same DW geography table. They keep customer and seller location filters unambiguous. `DimDate` uses purchase date as the active relationship for orders; approval, carrier, delivered and estimated dates are inactive. Use `USERELATIONSHIP` in a dedicated measure when analyzing another date role.

Use **Orders** for the count of all order headers. Use **Sales Orders** for seller/product analysis, because sellers and products are attached to order items. **Avg Review** uses one latest review per order from `FactOrderDelivery`; **Reviews** counts every source review from `FactReview`. Monetary measures use Brazilian real values even though the format string omits a currency symbol.

After applying the model, mark `DimDate[FullDate]` as the date table in Power BI Desktop. Save the report as `.pbip` or `.pbix` after checking the model and credentials.
