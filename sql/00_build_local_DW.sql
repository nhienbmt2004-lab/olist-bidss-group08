SET NOCOUNT ON;
GO

/* ---------- 01_create_databases.sql ---------- */
IF DB_ID('Olist_Staging') IS NULL
BEGIN
    CREATE DATABASE Olist_Staging;
END;
GO

IF DB_ID('Olist_DW') IS NULL
BEGIN
    CREATE DATABASE Olist_DW;
END;
GO

/* ---------- Xóa đối tượng cũ (để chạy lại được) ---------- */
USE Olist_DW;
GO
DROP TABLE IF EXISTS dbo.ETLReconciliation, dbo.ETLStepLog, dbo.ETLRun;
DROP TABLE IF EXISTS dbo.FactReview, dbo.FactPayment, dbo.FactOrderItem, dbo.FactOrderDelivery;
DROP TABLE IF EXISTS dbo.DimProduct, dbo.DimCategory, dbo.DimSeller, dbo.DimCustomer, dbo.DimGeography, dbo.DimDate;
GO
USE Olist_Staging;
GO
DROP TABLE IF EXISTS dbo.stg_CategoryTranslation, dbo.stg_Customers, dbo.stg_Geolocation, dbo.stg_OrderItems,
    dbo.stg_Orders, dbo.stg_Payments, dbo.stg_Products, dbo.stg_Reviews, dbo.stg_Sellers;
GO

/* ---------- staging/02_create_staging_tables.sql ---------- */
USE [Olist_Staging]
GO
/****** Object:  Table [dbo].[stg_CategoryTranslation]    Script Date: 10/12/2026 5:46:44 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[stg_CategoryTranslation](
	[product_category_name] [nvarchar](100) NULL,
	[product_category_name_english] [nvarchar](100) NULL
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[stg_Customers]    Script Date: 10/12/2026 5:46:44 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[stg_Customers](
	[customer_id] [char](32) NOT NULL,
	[customer_unique_id] [char](32) NOT NULL,
	[customer_zip_code_prefix] [char](5) NULL,
	[customer_city] [nvarchar](100) NULL,
	[customer_state] [char](2) NULL
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[stg_Geolocation]    Script Date: 10/12/2026 5:46:44 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[stg_Geolocation](
	[geolocation_zip_code_prefix] [nvarchar](5) NULL,
	[geolocation_lat] [decimal](18, 15) NULL,
	[geolocation_lng] [decimal](18, 15) NULL,
	[geolocation_city] [nvarchar](100) NULL,
	[geolocation_state] [nvarchar](2) NULL
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[stg_OrderItems]    Script Date: 10/12/2026 5:46:44 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[stg_OrderItems](
	[order_id] [nvarchar](32) NOT NULL,
	[order_item_id] [int] NOT NULL,
	[product_id] [nvarchar](32) NOT NULL,
	[seller_id] [nvarchar](32) NOT NULL,
	[shipping_limit_date] [nvarchar](19) NULL,
	[price] [decimal](12, 2) NULL,
	[freight_value] [decimal](12, 2) NULL
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[stg_Orders]    Script Date: 10/12/2026 5:46:44 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[stg_Orders](
	[order_id] [nvarchar](32) NOT NULL,
	[customer_id] [nvarchar](32) NOT NULL,
	[order_status] [nvarchar](20) NULL,
	[order_purchase_timestamp] [nvarchar](19) NULL,
	[order_approved_at] [nvarchar](19) NULL,
	[order_delivered_carrier_date] [nvarchar](19) NULL,
	[order_delivered_customer_date] [nvarchar](19) NULL,
	[order_estimated_delivery_date] [nvarchar](19) NULL
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[stg_Payments]    Script Date: 10/12/2026 5:46:44 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[stg_Payments](
	[order_id] [nvarchar](32) NOT NULL,
	[payment_sequential] [int] NOT NULL,
	[payment_type] [nvarchar](30) NULL,
	[payment_installments] [int] NULL,
	[payment_value] [decimal](12, 2) NULL
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[stg_Products]    Script Date: 10/12/2026 5:46:44 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[stg_Products](
	[product_id] [nvarchar](32) NOT NULL,
	[product_category_name] [nvarchar](100) NULL,
	[product_name_lenght] [nvarchar](20) NULL,
	[product_description_lenght] [nvarchar](20) NULL,
	[product_photos_qty] [nvarchar](20) NULL,
	[product_weight_g] [nvarchar](20) NULL,
	[product_length_cm] [nvarchar](20) NULL,
	[product_height_cm] [nvarchar](20) NULL,
	[product_width_cm] [nvarchar](20) NULL
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[stg_Reviews]    Script Date: 10/12/2026 5:46:44 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[stg_Reviews](
	[review_id] [nvarchar](32) NOT NULL,
	[order_id] [nvarchar](32) NOT NULL,
	[review_score] [int] NULL,
	[review_comment_title] [nvarchar](255) NULL,
	[review_comment_message] [nvarchar](max) NULL,
	[review_creation_date] [nvarchar](19) NULL,
	[review_answer_timestamp] [nvarchar](19) NULL
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[stg_Sellers]    Script Date: 10/12/2026 5:46:45 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[stg_Sellers](
	[seller_id] [nvarchar](32) NOT NULL,
	[seller_zip_code_prefix] [nvarchar](5) NULL,
	[seller_city] [nvarchar](100) NULL,
	[seller_state] [nvarchar](2) NULL
) ON [PRIMARY]
GO


/* ---------- Nạp 9 file CSV vào staging (thay cho load_staging_csv.py) ---------- */
USE Olist_Staging;
GO
BULK INSERT dbo.stg_Geolocation FROM 'D:\olist-bidss-group08\data\raw\olist\olist_geolocation_part1.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', FIELDQUOTE = '"', CODEPAGE = '65001', TABLOCK);
PRINT 'stg_Geolocation part 1: ' + CAST(@@ROWCOUNT AS varchar(20)) + ' rows';
GO
BULK INSERT dbo.stg_Geolocation FROM 'D:\olist-bidss-group08\data\raw\olist\olist_geolocation_part2.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', FIELDQUOTE = '"', CODEPAGE = '65001', TABLOCK);
PRINT 'stg_Geolocation part 2: ' + CAST(@@ROWCOUNT AS varchar(20)) + ' rows';
GO
BULK INSERT dbo.stg_Geolocation FROM 'D:\olist-bidss-group08\data\raw\olist\olist_geolocation_part3.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', FIELDQUOTE = '"', CODEPAGE = '65001', TABLOCK);
PRINT 'stg_Geolocation part 3: ' + CAST(@@ROWCOUNT AS varchar(20)) + ' rows';
GO
BULK INSERT dbo.stg_CategoryTranslation FROM 'D:\olist-bidss-group08\data\raw\olist\product_category_name_translation.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', FIELDQUOTE = '"', CODEPAGE = '65001', TABLOCK);
PRINT 'stg_CategoryTranslation: ' + CAST(@@ROWCOUNT AS varchar(20)) + ' rows';
GO
BULK INSERT dbo.stg_Customers FROM 'D:\olist-bidss-group08\data\raw\olist\olist_customers_dataset.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', FIELDQUOTE = '"', CODEPAGE = '65001', TABLOCK);
PRINT 'stg_Customers: ' + CAST(@@ROWCOUNT AS varchar(20)) + ' rows';
GO
BULK INSERT dbo.stg_Sellers FROM 'D:\olist-bidss-group08\data\raw\olist\olist_sellers_dataset.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', FIELDQUOTE = '"', CODEPAGE = '65001', TABLOCK);
PRINT 'stg_Sellers: ' + CAST(@@ROWCOUNT AS varchar(20)) + ' rows';
GO
BULK INSERT dbo.stg_Products FROM 'D:\olist-bidss-group08\data\raw\olist\olist_products_dataset.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', FIELDQUOTE = '"', CODEPAGE = '65001', TABLOCK);
PRINT 'stg_Products: ' + CAST(@@ROWCOUNT AS varchar(20)) + ' rows';
GO
BULK INSERT dbo.stg_Orders FROM 'D:\olist-bidss-group08\data\raw\olist\olist_orders_dataset.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', FIELDQUOTE = '"', CODEPAGE = '65001', TABLOCK);
PRINT 'stg_Orders: ' + CAST(@@ROWCOUNT AS varchar(20)) + ' rows';
GO
BULK INSERT dbo.stg_OrderItems FROM 'D:\olist-bidss-group08\data\raw\olist\olist_order_items_dataset.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', FIELDQUOTE = '"', CODEPAGE = '65001', TABLOCK);
PRINT 'stg_OrderItems: ' + CAST(@@ROWCOUNT AS varchar(20)) + ' rows';
GO
BULK INSERT dbo.stg_Payments FROM 'D:\olist-bidss-group08\data\raw\olist\olist_order_payments_dataset.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', FIELDQUOTE = '"', CODEPAGE = '65001', TABLOCK);
PRINT 'stg_Payments: ' + CAST(@@ROWCOUNT AS varchar(20)) + ' rows';
GO
BULK INSERT dbo.stg_Reviews FROM 'D:\olist-bidss-group08\data\raw\olist\olist_order_reviews_dataset.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', FIELDQUOTE = '"', CODEPAGE = '65001', TABLOCK);
PRINT 'stg_Reviews: ' + CAST(@@ROWCOUNT AS varchar(20)) + ' rows';
GO

/* ---------- staging/03_create_staging_indexes.sql ---------- */
USE Olist_Staging;
GO

-- Run after the initial CSV load. These keys are used by warehouse joins.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.stg_Orders') AND name='IX_stg_Orders_OrderId')
    CREATE INDEX IX_stg_Orders_OrderId ON dbo.stg_Orders(order_id) INCLUDE(customer_id,order_purchase_timestamp);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.stg_OrderItems') AND name='IX_stg_OrderItems_OrderId')
    CREATE INDEX IX_stg_OrderItems_OrderId ON dbo.stg_OrderItems(order_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.stg_Payments') AND name='IX_stg_Payments_OrderId')
    CREATE INDEX IX_stg_Payments_OrderId ON dbo.stg_Payments(order_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.stg_Reviews') AND name='IX_stg_Reviews_OrderId')
    CREATE INDEX IX_stg_Reviews_OrderId ON dbo.stg_Reviews(order_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.stg_Customers') AND name='IX_stg_Customers_CustomerId')
    CREATE INDEX IX_stg_Customers_CustomerId ON dbo.stg_Customers(customer_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.stg_Products') AND name='IX_stg_Products_ProductId')
    CREATE INDEX IX_stg_Products_ProductId ON dbo.stg_Products(product_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.stg_Sellers') AND name='IX_stg_Sellers_SellerId')
    CREATE INDEX IX_stg_Sellers_SellerId ON dbo.stg_Sellers(seller_id);
GO

UPDATE STATISTICS dbo.stg_Orders WITH FULLSCAN;
UPDATE STATISTICS dbo.stg_OrderItems WITH FULLSCAN;
UPDATE STATISTICS dbo.stg_Payments WITH FULLSCAN;
UPDATE STATISTICS dbo.stg_Reviews WITH FULLSCAN;
GO


/* ---------- staging/05_create_clean_views.sql ---------- */
USE Olist_Staging;
GO

/* Task 8 and 10 - normalized, typed and de-duplicated source layer. */
CREATE OR ALTER VIEW dbo.vw_CleanGeography AS
WITH ranked AS (
    SELECT RIGHT('00000'+TRIM(geolocation_zip_code_prefix),5) AS zip_code_prefix,
           UPPER(TRIM(geolocation_city)) AS city,
           UPPER(TRIM(geolocation_state)) AS state_code,
           AVG(geolocation_lat) AS latitude, AVG(geolocation_lng) AS longitude,
           ROW_NUMBER() OVER (PARTITION BY RIGHT('00000'+TRIM(geolocation_zip_code_prefix),5)
                              ORDER BY COUNT_BIG(*) DESC, UPPER(TRIM(geolocation_state)), UPPER(TRIM(geolocation_city))) AS rn
    FROM dbo.stg_Geolocation
    WHERE TRY_CONVERT(int,geolocation_zip_code_prefix) IS NOT NULL
      AND LEN(TRIM(geolocation_zip_code_prefix)) BETWEEN 1 AND 5
      AND TRY_CONVERT(int,geolocation_zip_code_prefix) >= 0
    GROUP BY RIGHT('00000'+TRIM(geolocation_zip_code_prefix),5),
             UPPER(TRIM(geolocation_city)), UPPER(TRIM(geolocation_state))
)
SELECT zip_code_prefix, city, state_code, latitude, longitude FROM ranked WHERE rn=1;
GO

CREATE OR ALTER VIEW dbo.vw_CleanCustomers AS
SELECT c.customer_id,c.customer_unique_id,
       CASE WHEN TRY_CONVERT(int,c.customer_zip_code_prefix) BETWEEN 0 AND 99999
                  AND LEN(TRIM(c.customer_zip_code_prefix)) BETWEEN 1 AND 5
            THEN RIGHT('00000'+TRIM(c.customer_zip_code_prefix),5) END AS zip_code_prefix,
       COALESCE(g.city,UPPER(TRIM(c.customer_city))) AS city,
       COALESCE(g.state_code,UPPER(TRIM(c.customer_state))) AS state_code
FROM dbo.stg_Customers c
LEFT JOIN dbo.vw_CleanGeography g
  ON g.zip_code_prefix=CASE WHEN TRY_CONVERT(int,c.customer_zip_code_prefix) BETWEEN 0 AND 99999
                                 AND LEN(TRIM(c.customer_zip_code_prefix)) BETWEEN 1 AND 5
                            THEN RIGHT('00000'+TRIM(c.customer_zip_code_prefix),5) END;
GO

CREATE OR ALTER VIEW dbo.vw_CleanSellers AS
SELECT s.seller_id,
       CASE WHEN TRY_CONVERT(int,s.seller_zip_code_prefix) BETWEEN 0 AND 99999
                  AND LEN(TRIM(s.seller_zip_code_prefix)) BETWEEN 1 AND 5
            THEN RIGHT('00000'+TRIM(s.seller_zip_code_prefix),5) END AS zip_code_prefix,
       COALESCE(g.city,UPPER(TRIM(s.seller_city))) AS city,
       COALESCE(g.state_code,UPPER(TRIM(s.seller_state))) AS state_code
FROM dbo.stg_Sellers s
LEFT JOIN dbo.vw_CleanGeography g
  ON g.zip_code_prefix=CASE WHEN TRY_CONVERT(int,s.seller_zip_code_prefix) BETWEEN 0 AND 99999
                                 AND LEN(TRIM(s.seller_zip_code_prefix)) BETWEEN 1 AND 5
                            THEN RIGHT('00000'+TRIM(s.seller_zip_code_prefix),5) END;
GO

CREATE OR ALTER VIEW dbo.vw_CleanProducts AS
SELECT p.product_id,
       COALESCE(NULLIF(TRIM(t.product_category_name_english),''),
                NULLIF(TRIM(p.product_category_name),''),'unknown') AS category_name,
       TRY_CONVERT(int,p.product_name_lenght) AS product_name_length,
       TRY_CONVERT(int,p.product_description_lenght) AS product_description_length,
       TRY_CONVERT(int,p.product_photos_qty) AS product_photos_qty,
       TRY_CONVERT(decimal(12,2),p.product_weight_g) AS product_weight_g,
       TRY_CONVERT(decimal(12,2),p.product_length_cm) AS product_length_cm,
       TRY_CONVERT(decimal(12,2),p.product_height_cm) AS product_height_cm,
       TRY_CONVERT(decimal(12,2),p.product_width_cm) AS product_width_cm
FROM dbo.stg_Products p
OUTER APPLY (
    SELECT TOP (1) product_category_name_english
    FROM dbo.stg_CategoryTranslation t
    WHERE t.product_category_name=p.product_category_name
    ORDER BY CASE WHEN NULLIF(TRIM(t.product_category_name_english),'') IS NULL THEN 1 ELSE 0 END,
             t.product_category_name_english
) t;
GO

CREATE OR ALTER VIEW dbo.vw_OrderSellerBridge AS
SELECT DISTINCT order_id, seller_id FROM dbo.stg_OrderItems;
GO

CREATE OR ALTER VIEW dbo.vw_OrderReview AS
WITH r AS (
 SELECT *, ROW_NUMBER() OVER(PARTITION BY order_id ORDER BY TRY_CONVERT(datetime2,review_answer_timestamp) DESC, review_id DESC) rn
 FROM dbo.stg_Reviews
)
SELECT review_id,order_id,review_score,review_comment_title,review_comment_message,
       TRY_CONVERT(datetime2,review_creation_date) review_creation_date,
       TRY_CONVERT(datetime2,review_answer_timestamp) review_answer_timestamp
FROM r WHERE rn=1;
GO

CREATE OR ALTER VIEW dbo.vw_OrderPayment AS
SELECT order_id, SUM(payment_value) AS payment_value,
       MAX(payment_installments) AS max_installments,
       COUNT(*) AS payment_count,
       STRING_AGG(CONVERT(nvarchar(max),payment_type), ',') AS payment_types
FROM dbo.stg_Payments GROUP BY order_id;
GO


/* ---------- warehouse/06_create_dw_tables.sql ---------- */
USE Olist_DW;
GO

/* Phase 2 schema. Run once on a new, empty Olist_DW database. */
CREATE TABLE dbo.DimDate (
    DateKey int NOT NULL PRIMARY KEY,
    FullDate date NOT NULL UNIQUE,
    DayNumber tinyint NOT NULL,
    MonthNumber tinyint NOT NULL,
    QuarterNumber tinyint NOT NULL,
    YearNumber smallint NOT NULL,
    DayOfWeekNumber tinyint NOT NULL,
    IsWeekend bit NOT NULL
);
CREATE TABLE dbo.DimGeography (
    GeographyKey int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    ZipCodePrefix char(5) NOT NULL UNIQUE,
    City nvarchar(100) NULL,
    StateCode char(2) NULL,
    Latitude decimal(18,15) NULL,
    Longitude decimal(18,15) NULL
);
CREATE TABLE dbo.DimCustomer (
    CustomerKey int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    CustomerId char(32) NOT NULL UNIQUE,
    CustomerUniqueId char(32) NOT NULL,
    GeographyKey int NULL REFERENCES dbo.DimGeography(GeographyKey)
);
CREATE TABLE dbo.DimSeller (
    SellerKey int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    SellerId char(32) NOT NULL UNIQUE,
    GeographyKey int NULL REFERENCES dbo.DimGeography(GeographyKey)
);
CREATE TABLE dbo.DimCategory (
    CategoryKey int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    CategoryName nvarchar(100) NOT NULL UNIQUE
);
CREATE TABLE dbo.DimProduct (
    ProductKey int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    ProductId char(32) NOT NULL UNIQUE,
    CategoryKey int NULL REFERENCES dbo.DimCategory(CategoryKey),
    ProductWeightG decimal(12,2) NULL,
    ProductLengthCm decimal(12,2) NULL,
    ProductHeightCm decimal(12,2) NULL,
    ProductWidthCm decimal(12,2) NULL
);
GO

CREATE TABLE dbo.FactOrderDelivery (
    OrderDeliveryKey bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    OrderId char(32) NOT NULL UNIQUE,
    CustomerKey int NOT NULL REFERENCES dbo.DimCustomer(CustomerKey),
    PurchaseDateKey int NOT NULL REFERENCES dbo.DimDate(DateKey),
    ApprovedDateKey int NULL REFERENCES dbo.DimDate(DateKey),
    CarrierDateKey int NULL REFERENCES dbo.DimDate(DateKey),
    DeliveredDateKey int NULL REFERENCES dbo.DimDate(DateKey),
    EstimatedDeliveryDateKey int NULL REFERENCES dbo.DimDate(DateKey),
    OrderStatus nvarchar(20) NULL,
    DeliveryDays int NULL,
    DelayDays int NULL,
    IsDelivered bit NOT NULL,
    IsCancelled bit NOT NULL,
    IsOnTime bit NULL,
    ItemCount int NOT NULL,
    SellerCount int NOT NULL,
    GMV decimal(18,2) NOT NULL,
    FreightValue decimal(18,2) NOT NULL,
    PaymentValue decimal(18,2) NULL,
    ReviewScore decimal(4,2) NULL
);
CREATE TABLE dbo.FactOrderItem (
    OrderItemKey bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    OrderId char(32) NOT NULL,
    OrderItemId int NOT NULL,
    PurchaseDateKey int NOT NULL REFERENCES dbo.DimDate(DateKey),
    CustomerKey int NOT NULL REFERENCES dbo.DimCustomer(CustomerKey),
    SellerKey int NOT NULL REFERENCES dbo.DimSeller(SellerKey),
    ProductKey int NOT NULL REFERENCES dbo.DimProduct(ProductKey),
    Price decimal(12,2) NOT NULL,
    FreightValue decimal(12,2) NOT NULL,
    ShippingLimitDate datetime2(0) NULL,
    CONSTRAINT UQ_FactOrderItem UNIQUE(OrderId,OrderItemId)
);
CREATE TABLE dbo.FactPayment (
    PaymentKey bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    OrderId char(32) NOT NULL,
    PaymentSequential int NOT NULL,
    PurchaseDateKey int NOT NULL REFERENCES dbo.DimDate(DateKey),
    CustomerKey int NOT NULL REFERENCES dbo.DimCustomer(CustomerKey),
    PaymentType nvarchar(30) NULL,
    Installments int NULL,
    PaymentValue decimal(12,2) NOT NULL,
    CONSTRAINT UQ_FactPayment UNIQUE(OrderId,PaymentSequential)
);
CREATE TABLE dbo.FactReview (
    ReviewKey bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    ReviewId char(32) NOT NULL,
    OrderId char(32) NOT NULL,
    CustomerKey int NOT NULL REFERENCES dbo.DimCustomer(CustomerKey),
    ReviewDateKey int NULL REFERENCES dbo.DimDate(DateKey),
    ReviewScore tinyint NULL CHECK(ReviewScore BETWEEN 1 AND 5),
    HasComment bit NOT NULL,
    ResponseHours int NULL,
    CONSTRAINT UQ_FactReview UNIQUE(ReviewId,OrderId)
);
GO

CREATE INDEX IX_FOD_PurchaseDate ON dbo.FactOrderDelivery(PurchaseDateKey);
CREATE INDEX IX_FOI_DateSeller ON dbo.FactOrderItem(PurchaseDateKey,SellerKey);
CREATE INDEX IX_FOI_Product ON dbo.FactOrderItem(ProductKey);
CREATE INDEX IX_FP_Date ON dbo.FactPayment(PurchaseDateKey);
CREATE INDEX IX_FR_Date ON dbo.FactReview(ReviewDateKey);
GO


/* ---------- warehouse/07_create_etl_support.sql ---------- */
USE Olist_DW;
GO
SET ANSI_NULLS ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET QUOTED_IDENTIFIER ON;
SET NUMERIC_ROUNDABORT OFF;
GO

IF OBJECT_ID('dbo.ETLRun','U') IS NULL
CREATE TABLE dbo.ETLRun (
    RunId bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    StartedAt datetime2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    FinishedAt datetime2(0) NULL,
    Status varchar(12) NOT NULL CHECK (Status IN ('RUNNING','SUCCEEDED','FAILED')),
    ErrorMessage nvarchar(4000) NULL
);
IF OBJECT_ID('dbo.ETLStepLog','U') IS NULL
CREATE TABLE dbo.ETLStepLog (
    StepId bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    RunId bigint NOT NULL REFERENCES dbo.ETLRun(RunId),
    StepName sysname NOT NULL,
    StartedAt datetime2(0) NOT NULL,
    FinishedAt datetime2(0) NOT NULL,
    Status varchar(12) NOT NULL CHECK (Status IN ('SUCCEEDED','FAILED')),
    TargetRows bigint NULL,
    ErrorMessage nvarchar(4000) NULL
);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.ETLStepLog')
               AND name='IX_ETLStepLog_RunId')
CREATE INDEX IX_ETLStepLog_RunId ON dbo.ETLStepLog(RunId,StepId);
IF OBJECT_ID('dbo.ETLReconciliation','U') IS NULL
CREATE TABLE dbo.ETLReconciliation (
    ReconciliationId bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    RunId bigint NULL REFERENCES dbo.ETLRun(RunId),
    MetricName sysname NOT NULL,
    SourceValue decimal(20,2) NOT NULL,
    TargetValue decimal(20,2) NOT NULL,
    Difference AS (TargetValue-SourceValue) PERSISTED,
    CheckedAt datetime2(0) NOT NULL DEFAULT SYSUTCDATETIME()
);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.ETLReconciliation')
               AND name='IX_ETLReconciliation_RunId')
CREATE INDEX IX_ETLReconciliation_RunId ON dbo.ETLReconciliation(RunId,ReconciliationId);
GO


/* ---------- warehouse/08_load_dimensions.sql ---------- */
USE Olist_DW;
GO
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE dbo.usp_LoadDimDate
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET DATEFIRST 1;
    DECLARE @first date, @last date;

    WITH SourceDates AS (
        SELECT TRY_CONVERT(date,v.value) AS FullDate
        FROM Olist_Staging.dbo.stg_Orders o
        CROSS APPLY (VALUES (o.order_purchase_timestamp),(o.order_approved_at),
                            (o.order_delivered_carrier_date),(o.order_delivered_customer_date),
                            (o.order_estimated_delivery_date)) v(value)
        UNION ALL SELECT TRY_CONVERT(date,shipping_limit_date) FROM Olist_Staging.dbo.stg_OrderItems
        UNION ALL SELECT TRY_CONVERT(date,review_creation_date) FROM Olist_Staging.dbo.stg_Reviews
        UNION ALL SELECT TRY_CONVERT(date,review_answer_timestamp) FROM Olist_Staging.dbo.stg_Reviews
    )
    SELECT @first=MIN(FullDate),@last=MAX(FullDate) FROM SourceDates;

    IF @first IS NULL THROW 51001,'No valid source dates; load staging first.',1;
    IF DATEDIFF(day,@first,@last)>20000 THROW 51002,'Date range exceeds 20000 days; inspect source dates.',1;

    ;WITH Dates AS (
        SELECT @first AS FullDate
        UNION ALL SELECT DATEADD(day,1,FullDate) FROM Dates WHERE FullDate<@last
    )
    INSERT dbo.DimDate(DateKey,FullDate,DayNumber,MonthNumber,QuarterNumber,
                        YearNumber,DayOfWeekNumber,IsWeekend)
    SELECT CONVERT(int,CONVERT(char(8),d.FullDate,112)),d.FullDate,
           DAY(d.FullDate),MONTH(d.FullDate),DATEPART(quarter,d.FullDate),
           YEAR(d.FullDate),DATEPART(weekday,d.FullDate),
           CASE WHEN DATEPART(weekday,d.FullDate) IN (6,7) THEN 1 ELSE 0 END
    FROM Dates d
    WHERE NOT EXISTS (SELECT 1 FROM dbo.DimDate x WHERE x.FullDate=d.FullDate)
    OPTION (MAXRECURSION 0);
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_LoadDimGeography
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    ;WITH candidates AS (
        SELECT zip_code_prefix,city,state_code,latitude,longitude,1 AS priority
        FROM Olist_Staging.dbo.vw_CleanGeography
        UNION ALL SELECT zip_code_prefix,city,state_code,NULL,NULL,2
        FROM Olist_Staging.dbo.vw_CleanCustomers WHERE zip_code_prefix IS NOT NULL
        UNION ALL SELECT zip_code_prefix,city,state_code,NULL,NULL,3
        FROM Olist_Staging.dbo.vw_CleanSellers WHERE zip_code_prefix IS NOT NULL
    ), ranked AS (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY zip_code_prefix
                ORDER BY priority,state_code,city) rn FROM candidates
    )
    SELECT zip_code_prefix,city,state_code,latitude,longitude
    INTO #Geography FROM ranked WHERE rn=1;

    UPDATE d SET City=s.city,StateCode=s.state_code,Latitude=s.latitude,Longitude=s.longitude
    FROM dbo.DimGeography d JOIN #Geography s ON d.ZipCodePrefix=s.zip_code_prefix;
    INSERT dbo.DimGeography(ZipCodePrefix,City,StateCode,Latitude,Longitude)
    SELECT s.zip_code_prefix,s.city,s.state_code,s.latitude,s.longitude
    FROM #Geography s WHERE NOT EXISTS
        (SELECT 1 FROM dbo.DimGeography d WHERE d.ZipCodePrefix=s.zip_code_prefix);
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_LoadDimCustomer
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF EXISTS (SELECT customer_id FROM Olist_Staging.dbo.stg_Customers
               GROUP BY customer_id HAVING COUNT_BIG(*)>1)
        THROW 51003,'Duplicate customer_id in staging.',1;
    UPDATE d SET CustomerUniqueId=s.customer_unique_id,GeographyKey=g.GeographyKey
    FROM dbo.DimCustomer d JOIN Olist_Staging.dbo.stg_Customers s ON d.CustomerId=s.customer_id
    LEFT JOIN dbo.DimGeography g ON g.ZipCodePrefix=RIGHT('00000'+TRIM(s.customer_zip_code_prefix),5);
    INSERT dbo.DimCustomer(CustomerId,CustomerUniqueId,GeographyKey)
    SELECT s.customer_id,s.customer_unique_id,g.GeographyKey
    FROM Olist_Staging.dbo.stg_Customers s
    LEFT JOIN dbo.DimGeography g ON g.ZipCodePrefix=RIGHT('00000'+TRIM(s.customer_zip_code_prefix),5)
    WHERE NOT EXISTS (SELECT 1 FROM dbo.DimCustomer d WHERE d.CustomerId=s.customer_id);
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_LoadDimSeller
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF EXISTS (SELECT seller_id FROM Olist_Staging.dbo.stg_Sellers
               GROUP BY seller_id HAVING COUNT_BIG(*)>1)
        THROW 51004,'Duplicate seller_id in staging.',1;
    UPDATE d SET GeographyKey=g.GeographyKey
    FROM dbo.DimSeller d JOIN Olist_Staging.dbo.stg_Sellers s ON d.SellerId=s.seller_id
    LEFT JOIN dbo.DimGeography g ON g.ZipCodePrefix=RIGHT('00000'+TRIM(s.seller_zip_code_prefix),5);
    INSERT dbo.DimSeller(SellerId,GeographyKey)
    SELECT s.seller_id,g.GeographyKey
    FROM Olist_Staging.dbo.stg_Sellers s
    LEFT JOIN dbo.DimGeography g ON g.ZipCodePrefix=RIGHT('00000'+TRIM(s.seller_zip_code_prefix),5)
    WHERE NOT EXISTS (SELECT 1 FROM dbo.DimSeller d WHERE d.SellerId=s.seller_id);
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_LoadDimCategory
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    INSERT dbo.DimCategory(CategoryName)
    SELECT DISTINCT s.category_name
    FROM Olist_Staging.dbo.vw_CleanProducts s
    WHERE NOT EXISTS (SELECT 1 FROM dbo.DimCategory d WHERE d.CategoryName=s.category_name);
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_LoadDimProduct
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF EXISTS (SELECT product_id FROM Olist_Staging.dbo.vw_CleanProducts
               GROUP BY product_id HAVING COUNT_BIG(*)>1)
        THROW 51005,'Duplicate product_id in staging.',1;
    UPDATE d SET CategoryKey=c.CategoryKey,ProductWeightG=s.product_weight_g,
                 ProductLengthCm=s.product_length_cm,ProductHeightCm=s.product_height_cm,
                 ProductWidthCm=s.product_width_cm
    FROM dbo.DimProduct d JOIN Olist_Staging.dbo.vw_CleanProducts s ON d.ProductId=s.product_id
    JOIN dbo.DimCategory c ON c.CategoryName=s.category_name;
    INSERT dbo.DimProduct(ProductId,CategoryKey,ProductWeightG,ProductLengthCm,
                           ProductHeightCm,ProductWidthCm)
    SELECT s.product_id,c.CategoryKey,s.product_weight_g,s.product_length_cm,
           s.product_height_cm,s.product_width_cm
    FROM Olist_Staging.dbo.vw_CleanProducts s
    JOIN dbo.DimCategory c ON c.CategoryName=s.category_name
    WHERE NOT EXISTS (SELECT 1 FROM dbo.DimProduct d WHERE d.ProductId=s.product_id);
END;
GO


/* ---------- warehouse/09_load_facts.sql ---------- */
USE Olist_DW;
GO
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE dbo.usp_LoadFactOrderDelivery
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF EXISTS (SELECT order_id FROM Olist_Staging.dbo.stg_Orders GROUP BY order_id HAVING COUNT_BIG(*)>1)
        THROW 51101,'Duplicate order_id in staging.',1;
    IF EXISTS (
        SELECT 1 FROM Olist_Staging.dbo.stg_Orders o
        LEFT JOIN dbo.DimCustomer c ON c.CustomerId=CONVERT(char(32),o.customer_id)
        LEFT JOIN dbo.DimDate d ON d.FullDate=TRY_CONVERT(date,o.order_purchase_timestamp)
        WHERE c.CustomerKey IS NULL OR d.DateKey IS NULL
    ) THROW 51102,'Order has an unknown customer or invalid purchase date.',1;

    BEGIN TRANSACTION;
    DELETE FROM dbo.FactOrderDelivery;
    ;WITH item_totals AS (
        SELECT order_id,COUNT(*) item_count,COUNT(DISTINCT seller_id) seller_count,
               SUM(CONVERT(decimal(18,2),price)) gmv,
               SUM(CONVERT(decimal(18,2),freight_value)) freight_value
        FROM Olist_Staging.dbo.stg_OrderItems GROUP BY order_id
    ), orders_typed AS (
        SELECT o.*,
               TRY_CONVERT(datetime2(0),o.order_purchase_timestamp) purchase_at,
               TRY_CONVERT(datetime2(0),o.order_approved_at) approved_at,
               TRY_CONVERT(datetime2(0),o.order_delivered_carrier_date) carrier_at,
               TRY_CONVERT(datetime2(0),o.order_delivered_customer_date) delivered_at,
               TRY_CONVERT(datetime2(0),o.order_estimated_delivery_date) estimated_at
        FROM Olist_Staging.dbo.stg_Orders o
    )
    INSERT dbo.FactOrderDelivery(
        OrderId,CustomerKey,PurchaseDateKey,ApprovedDateKey,CarrierDateKey,
        DeliveredDateKey,EstimatedDeliveryDateKey,OrderStatus,DeliveryDays,
        DelayDays,IsDelivered,IsCancelled,IsOnTime,ItemCount,SellerCount,
        GMV,FreightValue,PaymentValue,ReviewScore)
    SELECT o.order_id,c.CustomerKey,p.DateKey,a.DateKey,cr.DateKey,
           dl.DateKey,est.DateKey,o.order_status,
           CASE WHEN o.order_status='delivered' AND o.delivered_at IS NOT NULL
                THEN DATEDIFF(day,o.purchase_at,o.delivered_at) END,
           CASE WHEN o.order_status='delivered' AND o.delivered_at IS NOT NULL
                     AND o.estimated_at IS NOT NULL
                THEN CASE WHEN DATEDIFF(day,o.estimated_at,o.delivered_at)>0
                          THEN DATEDIFF(day,o.estimated_at,o.delivered_at) ELSE 0 END END,
           CASE WHEN o.order_status='delivered' AND o.delivered_at IS NOT NULL THEN 1 ELSE 0 END,
           CASE WHEN o.order_status IN ('canceled','unavailable') THEN 1 ELSE 0 END,
           CASE WHEN o.order_status='delivered' AND o.delivered_at IS NOT NULL
                     AND o.estimated_at IS NOT NULL
                THEN CASE WHEN CONVERT(date,o.delivered_at)<=CONVERT(date,o.estimated_at)
                          THEN 1 ELSE 0 END END,
           COALESCE(i.item_count,0),COALESCE(i.seller_count,0),
           COALESCE(i.gmv,0),COALESCE(i.freight_value,0),
           pay.payment_value,rev.review_score
    FROM orders_typed o
    JOIN dbo.DimCustomer c ON c.CustomerId=CONVERT(char(32),o.customer_id)
    JOIN dbo.DimDate p ON p.FullDate=CONVERT(date,o.purchase_at)
    LEFT JOIN dbo.DimDate a ON a.FullDate=CONVERT(date,o.approved_at)
    LEFT JOIN dbo.DimDate cr ON cr.FullDate=CONVERT(date,o.carrier_at)
    LEFT JOIN dbo.DimDate dl ON dl.FullDate=CONVERT(date,o.delivered_at)
    LEFT JOIN dbo.DimDate est ON est.FullDate=CONVERT(date,o.estimated_at)
    LEFT JOIN item_totals i ON i.order_id=o.order_id
    LEFT JOIN Olist_Staging.dbo.vw_OrderPayment pay ON pay.order_id=o.order_id
    LEFT JOIN Olist_Staging.dbo.vw_OrderReview rev ON rev.order_id=o.order_id;
    COMMIT TRANSACTION;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_LoadFactOrderItem
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF EXISTS (
        SELECT 1 FROM Olist_Staging.dbo.stg_OrderItems i
        LEFT JOIN Olist_Staging.dbo.stg_Orders o ON o.order_id=i.order_id
        LEFT JOIN dbo.DimCustomer c ON c.CustomerId=CONVERT(char(32),o.customer_id)
        LEFT JOIN dbo.DimDate d ON d.FullDate=TRY_CONVERT(date,o.order_purchase_timestamp)
        LEFT JOIN dbo.DimSeller s ON s.SellerId=CONVERT(char(32),i.seller_id)
        LEFT JOIN dbo.DimProduct p ON p.ProductId=CONVERT(char(32),i.product_id)
        WHERE o.order_id IS NULL OR c.CustomerKey IS NULL OR d.DateKey IS NULL
           OR s.SellerKey IS NULL OR p.ProductKey IS NULL
           OR i.price IS NULL OR i.freight_value IS NULL
           OR i.price<0 OR i.freight_value<0
    ) THROW 51103,'Order item has a missing dimension, invalid price or freight.',1;
    BEGIN TRANSACTION;
    DELETE FROM dbo.FactOrderItem;
    INSERT dbo.FactOrderItem(OrderId,OrderItemId,PurchaseDateKey,CustomerKey,
                            SellerKey,ProductKey,Price,FreightValue,ShippingLimitDate)
    SELECT i.order_id,i.order_item_id,d.DateKey,c.CustomerKey,s.SellerKey,p.ProductKey,
           i.price,i.freight_value,TRY_CONVERT(datetime2(0),i.shipping_limit_date)
    FROM Olist_Staging.dbo.stg_OrderItems i
    JOIN Olist_Staging.dbo.stg_Orders o ON o.order_id=i.order_id
    JOIN dbo.DimCustomer c ON c.CustomerId=CONVERT(char(32),o.customer_id)
    JOIN dbo.DimDate d ON d.FullDate=TRY_CONVERT(date,o.order_purchase_timestamp)
    JOIN dbo.DimSeller s ON s.SellerId=CONVERT(char(32),i.seller_id)
    JOIN dbo.DimProduct p ON p.ProductId=CONVERT(char(32),i.product_id);
    COMMIT TRANSACTION;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_LoadFactPayment
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF EXISTS (
        SELECT 1 FROM Olist_Staging.dbo.stg_Payments p
        LEFT JOIN Olist_Staging.dbo.stg_Orders o ON o.order_id=p.order_id
        LEFT JOIN dbo.DimCustomer c ON c.CustomerId=CONVERT(char(32),o.customer_id)
        LEFT JOIN dbo.DimDate d ON d.FullDate=TRY_CONVERT(date,o.order_purchase_timestamp)
        WHERE o.order_id IS NULL OR c.CustomerKey IS NULL OR d.DateKey IS NULL
           OR p.payment_value IS NULL OR p.payment_value<0
    ) THROW 51104,'Payment has a missing dimension or invalid value.',1;
    BEGIN TRANSACTION;
    DELETE FROM dbo.FactPayment;
    INSERT dbo.FactPayment(OrderId,PaymentSequential,PurchaseDateKey,CustomerKey,
                           PaymentType,Installments,PaymentValue)
    SELECT p.order_id,p.payment_sequential,d.DateKey,c.CustomerKey,
           p.payment_type,p.payment_installments,p.payment_value
    FROM Olist_Staging.dbo.stg_Payments p
    JOIN Olist_Staging.dbo.stg_Orders o ON o.order_id=p.order_id
    JOIN dbo.DimCustomer c ON c.CustomerId=CONVERT(char(32),o.customer_id)
    JOIN dbo.DimDate d ON d.FullDate=TRY_CONVERT(date,o.order_purchase_timestamp);
    COMMIT TRANSACTION;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_LoadFactReview
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF EXISTS (
        SELECT 1 FROM Olist_Staging.dbo.stg_Reviews r
        LEFT JOIN Olist_Staging.dbo.stg_Orders o ON o.order_id=r.order_id
        LEFT JOIN dbo.DimCustomer c ON c.CustomerId=CONVERT(char(32),o.customer_id)
        WHERE o.order_id IS NULL OR c.CustomerKey IS NULL
           OR (r.review_score IS NOT NULL AND r.review_score NOT BETWEEN 1 AND 5)
    ) THROW 51105,'Review has an unknown customer/order or invalid score.',1;
    BEGIN TRANSACTION;
    DELETE FROM dbo.FactReview;
    INSERT dbo.FactReview(ReviewId,OrderId,CustomerKey,ReviewDateKey,
                          ReviewScore,HasComment,ResponseHours)
    SELECT r.review_id,r.order_id,c.CustomerKey,d.DateKey,r.review_score,
           CASE WHEN NULLIF(TRIM(r.review_comment_message),'') IS NULL THEN 0 ELSE 1 END,
           DATEDIFF(hour,TRY_CONVERT(datetime2(0),r.review_creation_date),
                         TRY_CONVERT(datetime2(0),r.review_answer_timestamp))
    FROM Olist_Staging.dbo.stg_Reviews r
    JOIN Olist_Staging.dbo.stg_Orders o ON o.order_id=r.order_id
    JOIN dbo.DimCustomer c ON c.CustomerId=CONVERT(char(32),o.customer_id)
    LEFT JOIN dbo.DimDate d ON d.FullDate=TRY_CONVERT(date,r.review_creation_date);
    COMMIT TRANSACTION;
END;
GO


/* ---------- validation/11_reconcile_dw.sql ---------- */
USE Olist_DW;
GO
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE dbo.usp_ReconcileWarehouse @RunId bigint
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF NOT EXISTS (SELECT 1 FROM dbo.ETLRun WHERE RunId=@RunId)
        THROW 51201,'Unknown ETL RunId.',1;

    INSERT dbo.ETLReconciliation(RunId,MetricName,SourceValue,TargetValue)
    SELECT @RunId,'Orders',
           (SELECT COUNT_BIG(*) FROM Olist_Staging.dbo.stg_Orders),
           (SELECT COUNT_BIG(*) FROM dbo.FactOrderDelivery)
    UNION ALL SELECT @RunId,'OrderItems',
           (SELECT COUNT_BIG(*) FROM Olist_Staging.dbo.stg_OrderItems),
           (SELECT COUNT_BIG(*) FROM dbo.FactOrderItem)
    UNION ALL SELECT @RunId,'Payments',
           (SELECT COUNT_BIG(*) FROM Olist_Staging.dbo.stg_Payments),
           (SELECT COUNT_BIG(*) FROM dbo.FactPayment)
    UNION ALL SELECT @RunId,'Reviews',
           (SELECT COUNT_BIG(*) FROM Olist_Staging.dbo.stg_Reviews),
           (SELECT COUNT_BIG(*) FROM dbo.FactReview)
    UNION ALL SELECT @RunId,'GMV_OrderItems',
           (SELECT COALESCE(SUM(CONVERT(decimal(20,2),price)),0) FROM Olist_Staging.dbo.stg_OrderItems),
           (SELECT COALESCE(SUM(CONVERT(decimal(20,2),Price)),0) FROM dbo.FactOrderItem)
    UNION ALL SELECT @RunId,'GMV_Orders',
           (SELECT COALESCE(SUM(CONVERT(decimal(20,2),price)),0) FROM Olist_Staging.dbo.stg_OrderItems),
           (SELECT COALESCE(SUM(CONVERT(decimal(20,2),GMV)),0) FROM dbo.FactOrderDelivery)
    UNION ALL SELECT @RunId,'Freight',
           (SELECT COALESCE(SUM(CONVERT(decimal(20,2),freight_value)),0) FROM Olist_Staging.dbo.stg_OrderItems),
           (SELECT COALESCE(SUM(CONVERT(decimal(20,2),FreightValue)),0) FROM dbo.FactOrderItem)
    UNION ALL SELECT @RunId,'PaymentValue',
           (SELECT COALESCE(SUM(CONVERT(decimal(20,2),payment_value)),0) FROM Olist_Staging.dbo.stg_Payments),
           (SELECT COALESCE(SUM(CONVERT(decimal(20,2),PaymentValue)),0) FROM dbo.FactPayment)
    UNION ALL SELECT @RunId,'Customers',
           (SELECT COUNT_BIG(DISTINCT customer_id) FROM Olist_Staging.dbo.stg_Customers),
           (SELECT COUNT_BIG(*) FROM dbo.DimCustomer)
    UNION ALL SELECT @RunId,'Sellers',
           (SELECT COUNT_BIG(DISTINCT seller_id) FROM Olist_Staging.dbo.stg_Sellers),
           (SELECT COUNT_BIG(*) FROM dbo.DimSeller)
    UNION ALL SELECT @RunId,'Products',
           (SELECT COUNT_BIG(DISTINCT product_id) FROM Olist_Staging.dbo.stg_Products),
           (SELECT COUNT_BIG(*) FROM dbo.DimProduct);

    SELECT MetricName,SourceValue,TargetValue,Difference,
           CASE WHEN ABS(Difference)<=0.01 THEN 'PASS' ELSE 'FAIL' END AS Result
    FROM dbo.ETLReconciliation
    WHERE RunId=@RunId
    ORDER BY ReconciliationId;

    IF EXISTS
        (SELECT 1 FROM dbo.ETLReconciliation WHERE RunId=@RunId AND ABS(Difference)>0.01)
        THROW 51202,'Warehouse reconciliation failed; inspect ETLReconciliation.',1;
END;
GO


/* ---------- warehouse/10_master_etl.sql ---------- */
USE Olist_DW;
GO
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE dbo.usp_ValidateStaging
AS
BEGIN
    SET NOCOUNT ON;
    IF (SELECT COUNT_BIG(*) FROM Olist_Staging.dbo.stg_Customers)=0
       OR (SELECT COUNT_BIG(*) FROM Olist_Staging.dbo.stg_Geolocation)=0
       OR (SELECT COUNT_BIG(*) FROM Olist_Staging.dbo.stg_Orders)=0
       OR (SELECT COUNT_BIG(*) FROM Olist_Staging.dbo.stg_OrderItems)=0
       OR (SELECT COUNT_BIG(*) FROM Olist_Staging.dbo.stg_Payments)=0
       OR (SELECT COUNT_BIG(*) FROM Olist_Staging.dbo.stg_Reviews)=0
       OR (SELECT COUNT_BIG(*) FROM Olist_Staging.dbo.stg_Products)=0
       OR (SELECT COUNT_BIG(*) FROM Olist_Staging.dbo.stg_Sellers)=0
       OR (SELECT COUNT_BIG(*) FROM Olist_Staging.dbo.stg_CategoryTranslation)=0
        THROW 51301,'At least one staging table is empty; stop before DW refresh.',1;

    IF EXISTS (SELECT customer_id FROM Olist_Staging.dbo.stg_Customers GROUP BY customer_id HAVING COUNT_BIG(*)>1)
       OR EXISTS (SELECT seller_id FROM Olist_Staging.dbo.stg_Sellers GROUP BY seller_id HAVING COUNT_BIG(*)>1)
       OR EXISTS (SELECT product_id FROM Olist_Staging.dbo.stg_Products GROUP BY product_id HAVING COUNT_BIG(*)>1)
       OR EXISTS (SELECT order_id FROM Olist_Staging.dbo.stg_Orders GROUP BY order_id HAVING COUNT_BIG(*)>1)
       OR EXISTS (SELECT order_id,order_item_id FROM Olist_Staging.dbo.stg_OrderItems
                  GROUP BY order_id,order_item_id HAVING COUNT_BIG(*)>1)
       OR EXISTS (SELECT order_id,payment_sequential FROM Olist_Staging.dbo.stg_Payments
                  GROUP BY order_id,payment_sequential HAVING COUNT_BIG(*)>1)
       OR EXISTS (SELECT review_id,order_id FROM Olist_Staging.dbo.stg_Reviews
                  GROUP BY review_id,order_id HAVING COUNT_BIG(*)>1)
        THROW 51303,'Duplicate business key in staging; inspect DataQualityIssues.',1;

    IF EXISTS (SELECT 1 FROM Olist_Staging.dbo.stg_Orders o
               LEFT JOIN Olist_Staging.dbo.stg_Customers c ON c.customer_id=o.customer_id
               WHERE c.customer_id IS NULL OR TRY_CONVERT(date,o.order_purchase_timestamp) IS NULL)
       OR EXISTS (SELECT 1 FROM Olist_Staging.dbo.stg_OrderItems i
                  LEFT JOIN Olist_Staging.dbo.stg_Orders o ON o.order_id=i.order_id
                  LEFT JOIN Olist_Staging.dbo.stg_Products p ON p.product_id=i.product_id
                  LEFT JOIN Olist_Staging.dbo.stg_Sellers s ON s.seller_id=i.seller_id
                  WHERE o.order_id IS NULL OR p.product_id IS NULL OR s.seller_id IS NULL
                     OR i.price IS NULL OR i.freight_value IS NULL
                     OR i.price<0 OR i.freight_value<0)
       OR EXISTS (SELECT 1 FROM Olist_Staging.dbo.stg_Payments p
                  LEFT JOIN Olist_Staging.dbo.stg_Orders o ON o.order_id=p.order_id
                  WHERE o.order_id IS NULL OR p.payment_value IS NULL OR p.payment_value<0)
       OR EXISTS (SELECT 1 FROM Olist_Staging.dbo.stg_Reviews r
                  LEFT JOIN Olist_Staging.dbo.stg_Orders o ON o.order_id=r.order_id
                  WHERE o.order_id IS NULL OR r.review_score NOT BETWEEN 1 AND 5)
        THROW 51304,'Invalid required source value or reference; inspect staging profiling.',1;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_RunWarehouseETL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    DECLARE @lockResult int,@runId bigint,@step sysname,@proc sysname,@target sysname,
            @started datetime2(0),@rows bigint,@sql nvarchar(max),@error nvarchar(4000);

    EXEC @lockResult=sys.sp_getapplock @Resource='Olist_DW_Warehouse_ETL',
        @LockMode='Exclusive',@LockOwner='Session',@LockTimeout=0;
    IF @lockResult<0 THROW 51302,'Another warehouse ETL run is active.',1;

    BEGIN TRY
        INSERT dbo.ETLRun(Status) VALUES ('RUNNING');
        SET @runId=CONVERT(bigint,SCOPE_IDENTITY());

        SET @step='ValidateStaging'; SET @started=SYSUTCDATETIME();
        EXEC dbo.usp_ValidateStaging;
        INSERT dbo.ETLStepLog(RunId,StepName,StartedAt,FinishedAt,Status,TargetRows)
        SELECT @runId,@step,@started,SYSUTCDATETIME(),'SUCCEEDED',COUNT_BIG(*)
        FROM Olist_Staging.dbo.stg_Orders;

        DECLARE @steps TABLE (SequenceNo int PRIMARY KEY,StepName sysname,
                              ProcedureName sysname,TargetTable sysname);
        INSERT @steps VALUES
            (1,'DimDate','usp_LoadDimDate','DimDate'),
            (2,'DimGeography','usp_LoadDimGeography','DimGeography'),
            (3,'DimCustomer','usp_LoadDimCustomer','DimCustomer'),
            (4,'DimSeller','usp_LoadDimSeller','DimSeller'),
            (5,'DimCategory','usp_LoadDimCategory','DimCategory'),
            (6,'DimProduct','usp_LoadDimProduct','DimProduct'),
            (7,'FactOrderDelivery','usp_LoadFactOrderDelivery','FactOrderDelivery'),
            (8,'FactOrderItem','usp_LoadFactOrderItem','FactOrderItem'),
            (9,'FactPayment','usp_LoadFactPayment','FactPayment'),
            (10,'FactReview','usp_LoadFactReview','FactReview');

        DECLARE step_cursor CURSOR LOCAL FAST_FORWARD FOR
            SELECT StepName,ProcedureName,TargetTable FROM @steps ORDER BY SequenceNo;
        OPEN step_cursor;
        FETCH NEXT FROM step_cursor INTO @step,@proc,@target;
        WHILE @@FETCH_STATUS=0
        BEGIN
            SET @started=SYSUTCDATETIME();
            SET @sql=N'EXEC dbo.'+QUOTENAME(@proc)+N';';
            EXEC sys.sp_executesql @sql;
            SET @sql=N'SELECT @n=COUNT_BIG(*) FROM dbo.'+QUOTENAME(@target)+N';';
            EXEC sys.sp_executesql @sql,N'@n bigint OUTPUT',@n=@rows OUTPUT;
            INSERT dbo.ETLStepLog(RunId,StepName,StartedAt,FinishedAt,Status,TargetRows)
            VALUES (@runId,@step,@started,SYSUTCDATETIME(),'SUCCEEDED',@rows);
            FETCH NEXT FROM step_cursor INTO @step,@proc,@target;
        END;
        CLOSE step_cursor;
        DEALLOCATE step_cursor;

        SET @step='Reconciliation'; SET @started=SYSUTCDATETIME();
        EXEC dbo.usp_ReconcileWarehouse @RunId=@runId;
        INSERT dbo.ETLStepLog(RunId,StepName,StartedAt,FinishedAt,Status,TargetRows)
        SELECT @runId,@step,@started,SYSUTCDATETIME(),'SUCCEEDED',COUNT_BIG(*)
        FROM dbo.ETLReconciliation WHERE RunId=@runId;
        UPDATE dbo.ETLRun SET Status='SUCCEEDED',FinishedAt=SYSUTCDATETIME()
        WHERE RunId=@runId;
        EXEC sys.sp_releaseapplock @Resource='Olist_DW_Warehouse_ETL',@LockOwner='Session';
        SELECT @runId AS RunId,'SUCCEEDED' AS Status;
    END TRY
    BEGIN CATCH
        SET @error=ERROR_MESSAGE();
        IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
        IF @runId IS NOT NULL
        BEGIN
            INSERT dbo.ETLStepLog(RunId,StepName,StartedAt,FinishedAt,Status,ErrorMessage)
            VALUES (@runId,COALESCE(@step,'Initialize'),COALESCE(@started,SYSUTCDATETIME()),
                    SYSUTCDATETIME(),'FAILED',@error);
            UPDATE dbo.ETLRun SET Status='FAILED',FinishedAt=SYSUTCDATETIME(),
                                  ErrorMessage=@error WHERE RunId=@runId;
        END;
        EXEC sys.sp_releaseapplock @Resource='Olist_DW_Warehouse_ETL',@LockOwner='Session';
        THROW;
    END CATCH;
END;
GO


/* ---------- Chạy ETL (thay cho Master_ETL.dtsx) và kiểm tra ---------- */
USE Olist_DW;
GO
EXEC dbo.usp_RunWarehouseETL;
GO
SELECT TOP (1) RunId, Status, StartedAt, FinishedAt, ErrorMessage FROM dbo.ETLRun ORDER BY RunId DESC;
SELECT MetricName, SourceValue, TargetValue, Difference FROM dbo.ETLReconciliation
WHERE RunId = (SELECT MAX(RunId) FROM dbo.ETLRun) ORDER BY ReconciliationId;
-- Kỳ vọng: Orders 99441, OrderItems 112650, GMV 13591643.70, mọi Difference = 0
SELECT COUNT(*) AS delivered_with_estimate,
       SUM(CASE WHEN IsOnTime = 0 THEN 1 ELSE 0 END) AS late_orders
FROM dbo.FactOrderDelivery WHERE IsOnTime IS NOT NULL;
-- Kỳ vọng: 96470 và 6534
GO
