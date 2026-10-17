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
