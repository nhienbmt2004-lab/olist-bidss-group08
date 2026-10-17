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
