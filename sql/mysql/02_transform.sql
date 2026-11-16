CREATE TABLE CleanGeography AS
SELECT ZipCodePrefix,City,StateCode,Latitude,Longitude FROM (
  SELECT grouped.*,
    ROW_NUMBER() OVER (
      PARTITION BY ZipCodePrefix
      ORDER BY Frequency DESC,StateCode,City
    ) AS rn
  FROM (
    SELECT LPAD(TRIM(geolocation_zip_code_prefix),5,'0') AS ZipCodePrefix,
      UPPER(TRIM(geolocation_city)) AS City,
      UPPER(TRIM(geolocation_state)) AS StateCode,
      AVG(CAST(geolocation_lat AS DECIMAL(18,15))) AS Latitude,
      AVG(CAST(geolocation_lng AS DECIMAL(18,15))) AS Longitude,
      COUNT(*) AS Frequency
    FROM stg_Geolocation
    WHERE REGEXP_LIKE(TRIM(geolocation_zip_code_prefix),'^[0-9]{1,5}$')
    GROUP BY 1,2,3
  ) grouped
) ranked WHERE rn=1;
ALTER TABLE CleanGeography ADD PRIMARY KEY(ZipCodePrefix);

INSERT INTO DimGeography(ZipCodePrefix,City,StateCode,Latitude,Longitude)
SELECT ZipCodePrefix,City,StateCode,Latitude,Longitude FROM CleanGeography
ORDER BY ZipCodePrefix;
INSERT IGNORE INTO DimGeography(ZipCodePrefix,City,StateCode)
SELECT LPAD(TRIM(customer_zip_code_prefix),5,'0'),
       MIN(UPPER(TRIM(customer_city))),MIN(UPPER(TRIM(customer_state)))
FROM stg_Customers
WHERE REGEXP_LIKE(TRIM(customer_zip_code_prefix),'^[0-9]{1,5}$')
GROUP BY 1;
INSERT IGNORE INTO DimGeography(ZipCodePrefix,City,StateCode)
SELECT LPAD(TRIM(seller_zip_code_prefix),5,'0'),
       MIN(UPPER(TRIM(seller_city))),MIN(UPPER(TRIM(seller_state)))
FROM stg_Sellers
WHERE REGEXP_LIKE(TRIM(seller_zip_code_prefix),'^[0-9]{1,5}$')
GROUP BY 1;

INSERT INTO DimCustomer(CustomerId,CustomerUniqueId,GeographyKey)
SELECT c.customer_id,c.customer_unique_id,g.GeographyKey
FROM stg_Customers c
LEFT JOIN DimGeography g ON g.ZipCodePrefix=LPAD(TRIM(c.customer_zip_code_prefix),5,'0')
ORDER BY c.customer_id;
INSERT INTO DimSeller(SellerId,GeographyKey)
SELECT s.seller_id,g.GeographyKey
FROM stg_Sellers s
LEFT JOIN DimGeography g ON g.ZipCodePrefix=LPAD(TRIM(s.seller_zip_code_prefix),5,'0')
ORDER BY s.seller_id;

CREATE TABLE CleanProducts AS
SELECT p.product_id,
  COALESCE(NULLIF(TRIM(t.product_category_name_english),''),
           NULLIF(TRIM(p.product_category_name),''),'unknown') AS CategoryName,
  CAST(NULLIF(p.product_weight_g,'') AS DECIMAL(12,2)) AS ProductWeightG,
  CAST(NULLIF(p.product_length_cm,'') AS DECIMAL(12,2)) AS ProductLengthCm,
  CAST(NULLIF(p.product_height_cm,'') AS DECIMAL(12,2)) AS ProductHeightCm,
  CAST(NULLIF(p.product_width_cm,'') AS DECIMAL(12,2)) AS ProductWidthCm
FROM stg_Products p
LEFT JOIN stg_CategoryTranslation t
  ON t.product_category_name=p.product_category_name;
ALTER TABLE CleanProducts ADD PRIMARY KEY(product_id);
INSERT INTO DimCategory(CategoryName)
SELECT DISTINCT CategoryName FROM CleanProducts ORDER BY CategoryName;
INSERT INTO DimProduct(ProductId,CategoryKey,ProductWeightG,ProductLengthCm,
                       ProductHeightCm,ProductWidthCm)
SELECT p.product_id,c.CategoryKey,p.ProductWeightG,p.ProductLengthCm,
       p.ProductHeightCm,p.ProductWidthCm
FROM CleanProducts p JOIN DimCategory c ON c.CategoryName=p.CategoryName
ORDER BY p.product_id;

CREATE TABLE OrderItemTotals AS
SELECT order_id,COUNT(*) AS ItemCount,COUNT(DISTINCT seller_id) AS SellerCount,
       SUM(CAST(price AS DECIMAL(18,2))) AS GMV,
       SUM(CAST(freight_value AS DECIMAL(18,2))) AS FreightValue
FROM stg_OrderItems GROUP BY order_id;
ALTER TABLE OrderItemTotals ADD PRIMARY KEY(order_id);
CREATE TABLE OrderPaymentTotals AS
SELECT order_id,SUM(CAST(payment_value AS DECIMAL(18,2))) AS PaymentValue
FROM stg_Payments GROUP BY order_id;
ALTER TABLE OrderPaymentTotals ADD PRIMARY KEY(order_id);
CREATE TABLE OrderReviewLatest AS
SELECT order_id,CAST(review_score AS UNSIGNED) AS ReviewScore FROM (
  SELECT order_id,review_score,
    ROW_NUMBER() OVER(PARTITION BY order_id
      ORDER BY review_answer_timestamp DESC,review_id DESC) AS rn
  FROM stg_Reviews
) ranked WHERE rn=1;
ALTER TABLE OrderReviewLatest ADD PRIMARY KEY(order_id);

INSERT INTO FactOrderDelivery(
  OrderId,CustomerKey,PurchaseDateKey,ApprovedDateKey,CarrierDateKey,
  DeliveredDateKey,EstimatedDeliveryDateKey,OrderStatus,DeliveryDays,
  DelayDays,IsDelivered,IsCancelled,IsOnTime,ItemCount,SellerCount,
  GMV,FreightValue,PaymentValue,ReviewScore
)
SELECT o.order_id,c.CustomerKey,
  CAST(REPLACE(LEFT(o.order_purchase_timestamp,10),'-','') AS UNSIGNED),
  CAST(REPLACE(NULLIF(LEFT(o.order_approved_at,10),''),'-','') AS UNSIGNED),
  CAST(REPLACE(NULLIF(LEFT(o.order_delivered_carrier_date,10),''),'-','') AS UNSIGNED),
  CAST(REPLACE(NULLIF(LEFT(o.order_delivered_customer_date,10),''),'-','') AS UNSIGNED),
  CAST(REPLACE(NULLIF(LEFT(o.order_estimated_delivery_date,10),''),'-','') AS UNSIGNED),
  o.order_status,
  CASE WHEN o.order_status='delivered' AND o.order_delivered_customer_date<>''
       THEN DATEDIFF(LEFT(o.order_delivered_customer_date,10),LEFT(o.order_purchase_timestamp,10)) END,
  CASE WHEN o.order_status='delivered' AND o.order_delivered_customer_date<>''
             AND o.order_estimated_delivery_date<>''
       THEN GREATEST(0,DATEDIFF(LEFT(o.order_delivered_customer_date,10),
                                LEFT(o.order_estimated_delivery_date,10))) END,
  CASE WHEN o.order_status='delivered' AND o.order_delivered_customer_date<>'' THEN 1 ELSE 0 END,
  CASE WHEN o.order_status IN ('canceled','unavailable') THEN 1 ELSE 0 END,
  CASE WHEN o.order_status='delivered' AND o.order_delivered_customer_date<>''
             AND o.order_estimated_delivery_date<>''
       THEN CASE WHEN LEFT(o.order_delivered_customer_date,10)<=
                      LEFT(o.order_estimated_delivery_date,10) THEN 1 ELSE 0 END END,
  COALESCE(i.ItemCount,0),COALESCE(i.SellerCount,0),
  COALESCE(i.GMV,0),COALESCE(i.FreightValue,0),p.PaymentValue,r.ReviewScore
FROM stg_Orders o
JOIN DimCustomer c ON c.CustomerId=o.customer_id
LEFT JOIN OrderItemTotals i ON i.order_id=o.order_id
LEFT JOIN OrderPaymentTotals p ON p.order_id=o.order_id
LEFT JOIN OrderReviewLatest r ON r.order_id=o.order_id
ORDER BY o.order_id;

INSERT INTO FactOrderItem(OrderId,OrderItemId,PurchaseDateKey,CustomerKey,
                          SellerKey,ProductKey,Price,FreightValue,ShippingLimitDate)
SELECT i.order_id,CAST(i.order_item_id AS UNSIGNED),
  CAST(REPLACE(LEFT(o.order_purchase_timestamp,10),'-','') AS UNSIGNED),
  c.CustomerKey,s.SellerKey,p.ProductKey,
  CAST(i.price AS DECIMAL(12,2)),CAST(i.freight_value AS DECIMAL(12,2)),
  STR_TO_DATE(NULLIF(i.shipping_limit_date,''),'%Y-%m-%d %H:%i:%s')
FROM stg_OrderItems i
JOIN stg_Orders o ON o.order_id=i.order_id
JOIN DimCustomer c ON c.CustomerId=o.customer_id
JOIN DimSeller s ON s.SellerId=i.seller_id
JOIN DimProduct p ON p.ProductId=i.product_id
ORDER BY i.order_id,CAST(i.order_item_id AS UNSIGNED);

INSERT INTO FactPayment(OrderId,PaymentSequential,PurchaseDateKey,CustomerKey,
                        PaymentType,Installments,PaymentValue)
SELECT p.order_id,CAST(p.payment_sequential AS UNSIGNED),
  CAST(REPLACE(LEFT(o.order_purchase_timestamp,10),'-','') AS UNSIGNED),
  c.CustomerKey,p.payment_type,CAST(NULLIF(p.payment_installments,'') AS UNSIGNED),
  CAST(p.payment_value AS DECIMAL(12,2))
FROM stg_Payments p
JOIN stg_Orders o ON o.order_id=p.order_id
JOIN DimCustomer c ON c.CustomerId=o.customer_id
ORDER BY p.order_id,CAST(p.payment_sequential AS UNSIGNED);

INSERT INTO FactReview(ReviewId,OrderId,CustomerKey,ReviewDateKey,
                       ReviewScore,HasComment,ResponseHours)
SELECT r.review_id,r.order_id,c.CustomerKey,
  CAST(REPLACE(NULLIF(LEFT(r.review_creation_date,10),''),'-','') AS UNSIGNED),
  CAST(NULLIF(r.review_score,'') AS UNSIGNED),
  CASE WHEN TRIM(r.review_comment_message)<>'' THEN 1 ELSE 0 END,
  CASE WHEN r.review_creation_date<>'' AND r.review_answer_timestamp<>''
       THEN TIMESTAMPDIFF(HOUR,r.review_creation_date,r.review_answer_timestamp) END
FROM stg_Reviews r
JOIN stg_Orders o ON o.order_id=r.order_id
JOIN DimCustomer c ON c.CustomerId=o.customer_id
ORDER BY r.order_id,r.review_id;
