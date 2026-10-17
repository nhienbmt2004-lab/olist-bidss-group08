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
