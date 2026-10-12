USE Olist_Staging;
GO

SELECT 'Customers' AS Table_Name, COUNT(*) AS Total_Rows
FROM dbo.stg_Customers

UNION ALL
SELECT 'Geolocation', COUNT(*)
FROM dbo.stg_Geolocation

UNION ALL
SELECT 'Orders', COUNT(*)
FROM dbo.stg_Orders

UNION ALL
SELECT 'OrderItems', COUNT(*)
FROM dbo.stg_OrderItems

UNION ALL
SELECT 'Payments', COUNT(*)
FROM dbo.stg_Payments

UNION ALL
SELECT 'Reviews', COUNT(*)
FROM dbo.stg_Reviews

UNION ALL
SELECT 'Products', COUNT(*)
FROM dbo.stg_Products

UNION ALL
SELECT 'Sellers', COUNT(*)
FROM dbo.stg_Sellers

UNION ALL
SELECT 'CategoryTranslation', COUNT(*)
FROM dbo.stg_CategoryTranslation;
GO