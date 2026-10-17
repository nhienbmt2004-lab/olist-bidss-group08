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
