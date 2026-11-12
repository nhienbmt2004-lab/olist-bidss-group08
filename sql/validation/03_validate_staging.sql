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

USE Olist_Staging;
GO

/* =========================================================
   2. VALIDATE NULL / BLANK BUSINESS KEYS
   ========================================================= */

SELECT 'Customers - customer_id' AS Check_Name, COUNT(*) AS Error_Count
FROM dbo.stg_Customers
WHERE NULLIF(LTRIM(RTRIM(customer_id)), '') IS NULL

UNION ALL
SELECT 'Orders - order_id', COUNT(*)
FROM dbo.stg_Orders
WHERE NULLIF(LTRIM(RTRIM(order_id)), '') IS NULL

UNION ALL
SELECT 'OrderItems - order_id', COUNT(*)
FROM dbo.stg_OrderItems
WHERE NULLIF(LTRIM(RTRIM(order_id)), '') IS NULL

UNION ALL
SELECT 'OrderItems - product_id', COUNT(*)
FROM dbo.stg_OrderItems
WHERE NULLIF(LTRIM(RTRIM(product_id)), '') IS NULL

UNION ALL
SELECT 'OrderItems - seller_id', COUNT(*)
FROM dbo.stg_OrderItems
WHERE NULLIF(LTRIM(RTRIM(seller_id)), '') IS NULL

UNION ALL
SELECT 'Payments - order_id', COUNT(*)
FROM dbo.stg_Payments
WHERE NULLIF(LTRIM(RTRIM(order_id)), '') IS NULL

UNION ALL
SELECT 'Reviews - review_id', COUNT(*)
FROM dbo.stg_Reviews
WHERE NULLIF(LTRIM(RTRIM(review_id)), '') IS NULL

UNION ALL
SELECT 'Reviews - order_id', COUNT(*)
FROM dbo.stg_Reviews
WHERE NULLIF(LTRIM(RTRIM(order_id)), '') IS NULL

UNION ALL
SELECT 'Products - product_id', COUNT(*)
FROM dbo.stg_Products
WHERE NULLIF(LTRIM(RTRIM(product_id)), '') IS NULL

UNION ALL
SELECT 'Sellers - seller_id', COUNT(*)
FROM dbo.stg_Sellers
WHERE NULLIF(LTRIM(RTRIM(seller_id)), '') IS NULL;
GO


/* =========================================================
   3. VALIDATE DUPLICATE BUSINESS KEYS
   ========================================================= */

SELECT 'Customers - duplicate customer_id' AS Check_Name,
       COUNT(*) AS Duplicate_Groups
FROM (
    SELECT customer_id
    FROM dbo.stg_Customers
    GROUP BY customer_id
    HAVING COUNT(*) > 1
) x

UNION ALL

SELECT 'Orders - duplicate order_id',
       COUNT(*)
FROM (
    SELECT order_id
    FROM dbo.stg_Orders
    GROUP BY order_id
    HAVING COUNT(*) > 1
) x

UNION ALL

SELECT 'OrderItems - duplicate order_id + order_item_id',
       COUNT(*)
FROM (
    SELECT order_id, order_item_id
    FROM dbo.stg_OrderItems
    GROUP BY order_id, order_item_id
    HAVING COUNT(*) > 1
) x

UNION ALL

SELECT 'Payments - duplicate order_id + payment_sequential',
       COUNT(*)
FROM (
    SELECT order_id, payment_sequential
    FROM dbo.stg_Payments
    GROUP BY order_id, payment_sequential
    HAVING COUNT(*) > 1
) x

UNION ALL

SELECT 'Products - duplicate product_id',
       COUNT(*)
FROM (
    SELECT product_id
    FROM dbo.stg_Products
    GROUP BY product_id
    HAVING COUNT(*) > 1
) x

UNION ALL

SELECT 'Sellers - duplicate seller_id',
       COUNT(*)
FROM (
    SELECT seller_id
    FROM dbo.stg_Sellers
    GROUP BY seller_id
    HAVING COUNT(*) > 1
) x

UNION ALL

SELECT 'CategoryTranslation - duplicate category',
       COUNT(*)
FROM (
    SELECT product_category_name
    FROM dbo.stg_CategoryTranslation
    GROUP BY product_category_name
    HAVING COUNT(*) > 1
) x;
GO




USE Olist_Staging;
GO

/* =========================================================
   4. VALIDATE REFERENTIAL INTEGRITY / ORPHAN RECORDS
   ========================================================= */

SELECT
    'Orders -> Customers' AS Check_Name,
    COUNT(*) AS Orphan_Count
FROM dbo.stg_Orders o
WHERE NOT EXISTS (
    SELECT 1
    FROM dbo.stg_Customers c
    WHERE c.customer_id = o.customer_id
)

UNION ALL

SELECT
    'OrderItems -> Orders',
    COUNT(*)
FROM dbo.stg_OrderItems oi
WHERE NOT EXISTS (
    SELECT 1
    FROM dbo.stg_Orders o
    WHERE o.order_id = oi.order_id
)

UNION ALL

SELECT
    'OrderItems -> Products',
    COUNT(*)
FROM dbo.stg_OrderItems oi
WHERE NOT EXISTS (
    SELECT 1
    FROM dbo.stg_Products p
    WHERE p.product_id = oi.product_id
)

UNION ALL

SELECT
    'OrderItems -> Sellers',
    COUNT(*)
FROM dbo.stg_OrderItems oi
WHERE NOT EXISTS (
    SELECT 1
    FROM dbo.stg_Sellers s
    WHERE s.seller_id = oi.seller_id
)

UNION ALL

SELECT
    'Payments -> Orders',
    COUNT(*)
FROM dbo.stg_Payments p
WHERE NOT EXISTS (
    SELECT 1
    FROM dbo.stg_Orders o
    WHERE o.order_id = p.order_id
)

UNION ALL

SELECT
    'Reviews -> Orders',
    COUNT(*)
FROM dbo.stg_Reviews r
WHERE NOT EXISTS (
    SELECT 1
    FROM dbo.stg_Orders o
    WHERE o.order_id = r.order_id
)

UNION ALL

SELECT
    'Products -> CategoryTranslation',
    COUNT(*)
FROM dbo.stg_Products p
WHERE NULLIF(LTRIM(RTRIM(p.product_category_name)), '') IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM dbo.stg_CategoryTranslation ct
      WHERE ct.product_category_name = p.product_category_name
  );
GO

USE Olist_Staging;
GO

SELECT
    p.product_category_name,
    COUNT(*) AS Product_Count
FROM dbo.stg_Products p
WHERE NULLIF(LTRIM(RTRIM(p.product_category_name)), '') IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM dbo.stg_CategoryTranslation ct
      WHERE ct.product_category_name = p.product_category_name
  )
GROUP BY p.product_category_name
ORDER BY Product_Count DESC;
GO

SELECT COUNT(DISTINCT p.product_category_name) AS Missing_Category_Count
FROM dbo.stg_Products p
WHERE NULLIF(LTRIM(RTRIM(p.product_category_name)), '') IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM dbo.stg_CategoryTranslation ct
      WHERE ct.product_category_name = p.product_category_name
  );
GO


SELECT COUNT(*) AS Missing_Product_Category
FROM dbo.stg_Products
WHERE NULLIF(LTRIM(RTRIM(product_category_name)), '') IS NULL;
GO


USE Olist_Staging;
GO

/* =========================================================
   5. BASIC DATA QUALITY CHECKS
   ========================================================= */

SELECT 'Orders - blank order_status' AS Check_Name, COUNT(*) AS Issue_Count
FROM dbo.stg_Orders
WHERE NULLIF(LTRIM(RTRIM(order_status)), '') IS NULL

UNION ALL

SELECT 'Orders - blank purchase timestamp', COUNT(*)
FROM dbo.stg_Orders
WHERE NULLIF(LTRIM(RTRIM(order_purchase_timestamp)), '') IS NULL

UNION ALL

SELECT 'OrderItems - negative price', COUNT(*)
FROM dbo.stg_OrderItems
WHERE price < 0

UNION ALL

SELECT 'OrderItems - negative freight', COUNT(*)
FROM dbo.stg_OrderItems
WHERE freight_value < 0

UNION ALL

SELECT 'Payments - negative payment value', COUNT(*)
FROM dbo.stg_Payments
WHERE payment_value < 0

UNION ALL

SELECT 'Payments - negative installments', COUNT(*)
FROM dbo.stg_Payments
WHERE payment_installments < 0

UNION ALL

SELECT 'Reviews - invalid review score', COUNT(*)
FROM dbo.stg_Reviews
WHERE review_score NOT BETWEEN 1 AND 5;
GO