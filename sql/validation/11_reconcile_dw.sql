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
