CREATE VIEW vw_KPIOverview AS
SELECT COUNT(*) AS Orders,
       SUM(IsDelivered) AS DeliveredOrders,
       SUM(CASE WHEN IsOnTime IS NOT NULL THEN 1 ELSE 0 END) AS EligibleDeliveredOrders,
       SUM(CASE WHEN IsOnTime=0 THEN 1 ELSE 0 END) AS LateOrders,
       ROUND(AVG(CASE WHEN IsOnTime IS NOT NULL THEN IsOnTime END),6) AS OnTimeRate,
       ROUND(SUM(GMV),2) AS GMV,
       ROUND(SUM(FreightValue),2) AS FreightValue,
       ROUND(AVG(ReviewScore),3) AS AvgReviewScore
FROM FactOrderDelivery;

CREATE VIEW vw_DeliveryByMonthState AS
SELECT DATE_FORMAT(d.FullDate,'%Y-%m') AS PurchaseMonth,
       g.StateCode AS CustomerState,COUNT(*) AS EligibleOrders,
       SUM(CASE WHEN f.IsOnTime=0 THEN 1 ELSE 0 END) AS LateOrders,
       ROUND(AVG(f.IsOnTime),6) AS OnTimeRate,
       ROUND(AVG(CASE WHEN f.IsOnTime=0 THEN f.DelayDays END),2) AS AvgLateDays,
       ROUND(AVG(f.ReviewScore),3) AS AvgReviewScore
FROM FactOrderDelivery f
JOIN DimDate d ON d.DateKey=f.PurchaseDateKey
JOIN DimCustomer c ON c.CustomerKey=f.CustomerKey
LEFT JOIN DimGeography g ON g.GeographyKey=c.GeographyKey
WHERE f.IsOnTime IS NOT NULL
GROUP BY DATE_FORMAT(d.FullDate,'%Y-%m'),g.StateCode;

CREATE VIEW vw_ReviewByDeliveryStatus AS
SELECT CASE WHEN IsOnTime=1 THEN 'On time' ELSE 'Late' END AS DeliveryStatus,
       COUNT(*) AS ReviewedOrders,
       ROUND(AVG(ReviewScore),3) AS AvgReviewScore,
       ROUND(AVG(CASE WHEN ReviewScore<=2 THEN 1.0 ELSE 0.0 END),6) AS LowReviewRate
FROM FactOrderDelivery
WHERE IsOnTime IS NOT NULL AND ReviewScore IS NOT NULL
GROUP BY IsOnTime;

CREATE VIEW vw_SellerPerformance AS
SELECT s.SellerKey,s.SellerId,metrics.Orders,metrics.DeliveredOrders,
       metrics.CancelledOrders,metrics.OnTimeRate,metrics.AvgReviewScore,
       metrics.AvgLateDays,amounts.GMV
FROM (
  SELECT SellerKey,COUNT(*) AS Orders,
    SUM(IsDelivered) AS DeliveredOrders,
    SUM(CASE WHEN OrderStatus='canceled' THEN 1 ELSE 0 END) AS CancelledOrders,
    ROUND(AVG(CASE WHEN IsOnTime IS NOT NULL THEN IsOnTime END),6) AS OnTimeRate,
    ROUND(AVG(ReviewScore),3) AS AvgReviewScore,
    ROUND(AVG(CASE WHEN IsOnTime=0 THEN DelayDays END),2) AS AvgLateDays
  FROM (
    SELECT DISTINCT i.SellerKey,i.OrderId,f.IsDelivered,f.OrderStatus,
           f.IsOnTime,f.DelayDays,f.ReviewScore
    FROM FactOrderItem i JOIN FactOrderDelivery f ON f.OrderId=i.OrderId
  ) seller_orders GROUP BY SellerKey
) metrics
JOIN DimSeller s ON s.SellerKey=metrics.SellerKey
JOIN (
  SELECT SellerKey,SUM(Price) AS GMV FROM FactOrderItem GROUP BY SellerKey
) amounts ON amounts.SellerKey=metrics.SellerKey;
