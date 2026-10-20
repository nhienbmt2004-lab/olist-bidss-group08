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
