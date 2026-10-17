USE Olist_Staging;
GO

/* Task 7 - Data profiling. Run after the nine staging packages finish. */
DROP TABLE IF EXISTS dbo.DataQualityIssues;
GO
CREATE TABLE dbo.DataQualityIssues (
    issue_id       int IDENTITY(1,1) PRIMARY KEY,
    profiled_at    datetime2(0) NOT NULL DEFAULT SYSDATETIME(),
    source_table   sysname NOT NULL,
    column_name    sysname NULL,
    issue_type     varchar(40) NOT NULL,
    issue_count    bigint NOT NULL,
    severity       varchar(10) NOT NULL,
    sample_value   nvarchar(255) NULL
);
GO

INSERT dbo.DataQualityIssues(source_table,column_name,issue_type,issue_count,severity)
SELECT 'stg_Customers','customer_id','NULL',COUNT_BIG(*),'ERROR' FROM dbo.stg_Customers WHERE customer_id IS NULL
UNION ALL SELECT 'stg_Customers','customer_id','DUPLICATE',COUNT_BIG(*)-COUNT_BIG(DISTINCT customer_id),'ERROR' FROM dbo.stg_Customers
UNION ALL SELECT 'stg_Customers','customer_unique_id','NULL',COUNT_BIG(*),'ERROR' FROM dbo.stg_Customers WHERE customer_unique_id IS NULL
UNION ALL SELECT 'stg_Orders','order_id','DUPLICATE',COUNT_BIG(*)-COUNT_BIG(DISTINCT order_id),'ERROR' FROM dbo.stg_Orders
UNION ALL SELECT 'stg_Orders','order_id','NULL',COUNT_BIG(*),'ERROR' FROM dbo.stg_Orders WHERE order_id IS NULL
UNION ALL SELECT 'stg_Orders','customer_id','MISSING_REFERENCE',COUNT_BIG(*),'ERROR' FROM dbo.stg_Orders o LEFT JOIN dbo.stg_Customers c ON o.customer_id=c.customer_id WHERE c.customer_id IS NULL
UNION ALL SELECT 'stg_OrderItems','order_id, order_item_id','DUPLICATE',COUNT_BIG(*)-COUNT_BIG(DISTINCT CONCAT(order_id,'|',order_item_id)),'ERROR' FROM dbo.stg_OrderItems
UNION ALL SELECT 'stg_OrderItems','order_id','MISSING_REFERENCE',COUNT_BIG(*),'ERROR' FROM dbo.stg_OrderItems i LEFT JOIN dbo.stg_Orders o ON i.order_id=o.order_id WHERE o.order_id IS NULL
UNION ALL SELECT 'stg_OrderItems','product_id','MISSING_REFERENCE',COUNT_BIG(*),'ERROR' FROM dbo.stg_OrderItems i LEFT JOIN dbo.stg_Products p ON i.product_id=p.product_id WHERE p.product_id IS NULL
UNION ALL SELECT 'stg_OrderItems','seller_id','MISSING_REFERENCE',COUNT_BIG(*),'ERROR' FROM dbo.stg_OrderItems i LEFT JOIN dbo.stg_Sellers s ON i.seller_id=s.seller_id WHERE s.seller_id IS NULL
UNION ALL SELECT 'stg_Payments','order_id, payment_sequential','DUPLICATE',COUNT_BIG(*)-COUNT_BIG(DISTINCT CONCAT(order_id,'|',payment_sequential)),'ERROR' FROM dbo.stg_Payments
UNION ALL SELECT 'stg_Payments','order_id','MISSING_REFERENCE',COUNT_BIG(*),'ERROR' FROM dbo.stg_Payments p LEFT JOIN dbo.stg_Orders o ON p.order_id=o.order_id WHERE o.order_id IS NULL
UNION ALL SELECT 'stg_Products','product_id','DUPLICATE',COUNT_BIG(*)-COUNT_BIG(DISTINCT product_id),'ERROR' FROM dbo.stg_Products
UNION ALL SELECT 'stg_Sellers','seller_id','DUPLICATE',COUNT_BIG(*)-COUNT_BIG(DISTINCT seller_id),'ERROR' FROM dbo.stg_Sellers
UNION ALL SELECT 'stg_Reviews','review_id, order_id','DUPLICATE',COUNT_BIG(*)-COUNT_BIG(DISTINCT CONCAT(review_id,'|',order_id)),'ERROR' FROM dbo.stg_Reviews
UNION ALL SELECT 'stg_Reviews','order_id','MISSING_REFERENCE',COUNT_BIG(*),'ERROR' FROM dbo.stg_Reviews r LEFT JOIN dbo.stg_Orders o ON r.order_id=o.order_id WHERE o.order_id IS NULL
UNION ALL SELECT 'stg_CategoryTranslation','product_category_name','DUPLICATE',COUNT_BIG(*)-COUNT_BIG(DISTINCT product_category_name),'WARN' FROM dbo.stg_CategoryTranslation
UNION ALL SELECT 'stg_Reviews','review_score','OUT_OF_RANGE',COUNT_BIG(*),'ERROR' FROM dbo.stg_Reviews WHERE review_score NOT BETWEEN 1 AND 5
UNION ALL SELECT 'stg_OrderItems','price','OUT_OF_RANGE',COUNT_BIG(*),'ERROR' FROM dbo.stg_OrderItems WHERE price < 0
UNION ALL SELECT 'stg_OrderItems','freight_value','OUT_OF_RANGE',COUNT_BIG(*),'ERROR' FROM dbo.stg_OrderItems WHERE freight_value < 0
UNION ALL SELECT 'stg_Payments','payment_value','OUT_OF_RANGE',COUNT_BIG(*),'ERROR' FROM dbo.stg_Payments WHERE payment_value < 0
UNION ALL SELECT 'stg_Orders','order_purchase_timestamp','INVALID_DATE',COUNT_BIG(*),'ERROR' FROM dbo.stg_Orders WHERE order_purchase_timestamp IS NOT NULL AND TRY_CONVERT(datetime2,order_purchase_timestamp) IS NULL
UNION ALL SELECT 'stg_Orders','order_delivered_customer_date','INVALID_DATE',COUNT_BIG(*),'ERROR' FROM dbo.stg_Orders WHERE order_delivered_customer_date IS NOT NULL AND TRY_CONVERT(datetime2,order_delivered_customer_date) IS NULL
UNION ALL SELECT 'stg_Orders','order_approved_at','INVALID_DATE',COUNT_BIG(*),'ERROR' FROM dbo.stg_Orders WHERE order_approved_at IS NOT NULL AND TRY_CONVERT(datetime2,order_approved_at) IS NULL
UNION ALL SELECT 'stg_Orders','order_delivered_carrier_date','INVALID_DATE',COUNT_BIG(*),'ERROR' FROM dbo.stg_Orders WHERE order_delivered_carrier_date IS NOT NULL AND TRY_CONVERT(datetime2,order_delivered_carrier_date) IS NULL
UNION ALL SELECT 'stg_Orders','order_estimated_delivery_date','INVALID_DATE',COUNT_BIG(*),'ERROR' FROM dbo.stg_Orders WHERE order_estimated_delivery_date IS NOT NULL AND TRY_CONVERT(datetime2,order_estimated_delivery_date) IS NULL
UNION ALL SELECT 'stg_OrderItems','shipping_limit_date','INVALID_DATE',COUNT_BIG(*),'ERROR' FROM dbo.stg_OrderItems WHERE shipping_limit_date IS NOT NULL AND TRY_CONVERT(datetime2,shipping_limit_date) IS NULL
UNION ALL SELECT 'stg_Reviews','review_creation_date','INVALID_DATE',COUNT_BIG(*),'ERROR' FROM dbo.stg_Reviews WHERE review_creation_date IS NOT NULL AND TRY_CONVERT(datetime2,review_creation_date) IS NULL
UNION ALL SELECT 'stg_Reviews','review_answer_timestamp','INVALID_DATE',COUNT_BIG(*),'ERROR' FROM dbo.stg_Reviews WHERE review_answer_timestamp IS NOT NULL AND TRY_CONVERT(datetime2,review_answer_timestamp) IS NULL
UNION ALL SELECT 'stg_Products','product_weight_g','INVALID_NUMBER',COUNT_BIG(*),'WARN' FROM dbo.stg_Products WHERE product_weight_g IS NOT NULL AND TRY_CONVERT(decimal(12,2),product_weight_g) IS NULL
UNION ALL SELECT 'stg_Products','product_length_cm','INVALID_NUMBER',COUNT_BIG(*),'WARN' FROM dbo.stg_Products WHERE product_length_cm IS NOT NULL AND TRY_CONVERT(decimal(12,2),product_length_cm) IS NULL
UNION ALL SELECT 'stg_Products','product_height_cm','INVALID_NUMBER',COUNT_BIG(*),'WARN' FROM dbo.stg_Products WHERE product_height_cm IS NOT NULL AND TRY_CONVERT(decimal(12,2),product_height_cm) IS NULL
UNION ALL SELECT 'stg_Products','product_width_cm','INVALID_NUMBER',COUNT_BIG(*),'WARN' FROM dbo.stg_Products WHERE product_width_cm IS NOT NULL AND TRY_CONVERT(decimal(12,2),product_width_cm) IS NULL
UNION ALL SELECT 'stg_Geolocation','geolocation_lat','OUT_OF_RANGE',COUNT_BIG(*),'WARN' FROM dbo.stg_Geolocation WHERE geolocation_lat NOT BETWEEN -90 AND 90
UNION ALL SELECT 'stg_Geolocation','geolocation_lng','OUT_OF_RANGE',COUNT_BIG(*),'WARN' FROM dbo.stg_Geolocation WHERE geolocation_lng NOT BETWEEN -180 AND 180
UNION ALL SELECT 'stg_Customers','customer_zip_code_prefix','INVALID_FORMAT',COUNT_BIG(*),'WARN' FROM dbo.stg_Customers WHERE customer_zip_code_prefix IS NOT NULL AND (LEN(TRIM(customer_zip_code_prefix)) <> 5 OR TRY_CONVERT(int,customer_zip_code_prefix) IS NULL)
UNION ALL SELECT 'stg_Sellers','seller_zip_code_prefix','INVALID_FORMAT',COUNT_BIG(*),'WARN' FROM dbo.stg_Sellers WHERE seller_zip_code_prefix IS NOT NULL AND (LEN(TRIM(seller_zip_code_prefix)) <> 5 OR TRY_CONVERT(int,seller_zip_code_prefix) IS NULL)
UNION ALL SELECT 'stg_Products','product_category_name','UNTRANSLATED',COUNT_BIG(*),'WARN' FROM dbo.stg_Products p LEFT JOIN dbo.stg_CategoryTranslation t ON p.product_category_name=t.product_category_name WHERE p.product_category_name IS NOT NULL AND t.product_category_name IS NULL;
GO

/* Exploratory IQR outliers are warnings, not automatic data corrections. */
WITH amounts AS (
    SELECT 'stg_OrderItems' source_table, 'price' column_name, CONVERT(float,price) amount FROM dbo.stg_OrderItems WHERE price IS NOT NULL
    UNION ALL SELECT 'stg_OrderItems','freight_value',CONVERT(float,freight_value) FROM dbo.stg_OrderItems WHERE freight_value IS NOT NULL
    UNION ALL SELECT 'stg_Payments','payment_value',CONVERT(float,payment_value) FROM dbo.stg_Payments WHERE payment_value IS NOT NULL
), quartiles AS (
    SELECT source_table,column_name,amount,
           PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY amount) OVER (PARTITION BY source_table,column_name) q1,
           PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY amount) OVER (PARTITION BY source_table,column_name) q3
    FROM amounts
)
INSERT dbo.DataQualityIssues(source_table,column_name,issue_type,issue_count,severity)
SELECT source_table,column_name,'IQR_OUTLIER',COUNT_BIG(*),'WARN'
FROM quartiles
WHERE amount < q1-1.5*(q3-q1) OR amount > q3+1.5*(q3-q1)
GROUP BY source_table,column_name;
GO

SELECT * FROM dbo.DataQualityIssues WHERE issue_count > 0 ORDER BY severity, source_table, column_name;
GO

/* Column inventory for all nine staging sources: type, nulls and row count. */
DECLARE @table sysname, @column sysname, @type sysname, @sql nvarchar(max);
DECLARE @ColumnProfile TABLE (source_table sysname, column_name sysname, data_type sysname,
                             total_rows bigint, missing_rows bigint);
DECLARE profile_columns CURSOR LOCAL FAST_FORWARD FOR
SELECT t.name,c.name,TYPE_NAME(c.user_type_id)
FROM sys.tables t JOIN sys.columns c ON c.object_id=t.object_id
WHERE SCHEMA_NAME(t.schema_id)='dbo' AND t.name LIKE 'stg[_]%'
ORDER BY t.name,c.column_id;
OPEN profile_columns;
FETCH NEXT FROM profile_columns INTO @table,@column,@type;
WHILE @@FETCH_STATUS=0
BEGIN
    SET @sql=N'SELECT @t,@c,@d,COUNT_BIG(*),COUNT_BIG(*)-COUNT_BIG('+QUOTENAME(@column)+N') FROM dbo.'+QUOTENAME(@table);
    INSERT @ColumnProfile EXEC sys.sp_executesql @sql,N'@t sysname,@c sysname,@d sysname',@t=@table,@c=@column,@d=@type;
    FETCH NEXT FROM profile_columns INTO @table,@column,@type;
END;
CLOSE profile_columns;
DEALLOCATE profile_columns;
SELECT * FROM @ColumnProfile ORDER BY source_table,column_name;
GO

/* Numeric and date ranges for detecting unusual distributions. */
SELECT 'stg_OrderItems' source_table, 'price' column_name,
       MIN(price) min_value, MAX(price) max_value, AVG(price) avg_value FROM dbo.stg_OrderItems
UNION ALL SELECT 'stg_OrderItems','freight_value',MIN(freight_value),MAX(freight_value),AVG(freight_value) FROM dbo.stg_OrderItems
UNION ALL SELECT 'stg_Payments','payment_value',MIN(payment_value),MAX(payment_value),AVG(payment_value) FROM dbo.stg_Payments;
SELECT MIN(TRY_CONVERT(datetime2,order_purchase_timestamp)) first_purchase,
       MAX(TRY_CONVERT(datetime2,order_purchase_timestamp)) last_purchase FROM dbo.stg_Orders;
GO
