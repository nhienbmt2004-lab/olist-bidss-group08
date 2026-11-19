-- Separate operational simulation. Run against olist_bi_group08; never rebuild the DW.
CREATE TABLE IF NOT EXISTS DemoOrderEvent (
  OrderId CHAR(32) NOT NULL,
  EventType VARCHAR(12) NOT NULL,
  EventAt DATETIME NOT NULL,
  PurchaseAt DATETIME NOT NULL,
  EstimatedAt DATETIME,
  IngestedAtUtc DATETIME(6) NOT NULL,
  PRIMARY KEY (OrderId, EventType),
  INDEX IX_DemoEventAt (EventAt),
  INDEX IX_DemoIngestedAt (IngestedAtUtc)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS DemoReplayCheckpoint (
  Id TINYINT PRIMARY KEY,
  SourceSignature CHAR(64) NOT NULL,
  NextEventIndex INT NOT NULL,
  TotalEvents INT NOT NULL,
  LastEventAt DATETIME,
  LastBatchAtUtc DATETIME(6),
  CHECK (Id = 1)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS DemoReplayBatch (
  BatchId BIGINT AUTO_INCREMENT PRIMARY KEY,
  FirstEventIndex INT NOT NULL,
  EventCount INT NOT NULL,
  LastEventAt DATETIME NOT NULL,
  CommittedAtUtc DATETIME(6) NOT NULL
) ENGINE=InnoDB;

-- Append-only decisions made in the local Streamlit simulation. The minimum
-- BatchId of the active DemoReplayBatch set identifies one replay run; deleting
-- batch rows on reset never deletes this audit trail.
CREATE TABLE IF NOT EXISTS DemoActionLog (
  LogId BIGINT AUTO_INCREMENT PRIMARY KEY,
  ReplayRunId BIGINT NOT NULL,
  EventIndex INT NOT NULL,
  SimAt DATETIME NOT NULL,
  RecordedAtUtc DATETIME(6) NOT NULL,
  RouteId VARCHAR(12) NOT NULL,
  SellerId CHAR(32),
  UserRole VARCHAR(40) NOT NULL,
  ActionType VARCHAR(30) NOT NULL,
  CommentText VARCHAR(500),
  INDEX IX_DemoActionRunRoute (ReplayRunId, RouteId, LogId)
) ENGINE=InnoDB;

CREATE OR REPLACE VIEW vw_DemoOrderCurrent AS
SELECT e.OrderId,
       MIN(e.PurchaseAt) AS PurchaseAt,
       MAX(CASE WHEN e.EventType='approved' THEN e.EventAt END) AS ApprovedAt,
       MAX(CASE WHEN e.EventType='carrier' THEN e.EventAt END) AS CarrierAt,
       MAX(CASE WHEN e.EventType='delivered' THEN e.EventAt END) AS DeliveredAt,
       MAX(e.EstimatedAt) AS EstimatedAt,
       MAX(e.EventAt) AS LastEventAt,
       CASE WHEN MAX(CASE WHEN e.EventType='delivered' THEN 1 ELSE 0 END)=1 THEN 'Delivered'
            WHEN MAX(CASE WHEN e.EventType='carrier' THEN 1 ELSE 0 END)=1 THEN 'In transit'
            WHEN MAX(CASE WHEN e.EventType='approved' THEN 1 ELSE 0 END)=1 THEN 'Awaiting carrier'
            ELSE 'Awaiting approval' END AS CurrentStage,
       CASE WHEN MAX(CASE WHEN e.EventType='delivered' THEN 1 ELSE 0 END)=1 THEN 0
            WHEN MAX(e.EstimatedAt) IS NOT NULL AND DATE(c.LastEventAt) > DATE(MAX(e.EstimatedAt)) THEN 1
            ELSE 0 END AS PastEstimate,
       CASE WHEN MAX(CASE WHEN e.EventType='delivered' THEN e.EventAt END) IS NOT NULL
                  AND MAX(e.EstimatedAt) IS NOT NULL
                  AND DATE(MAX(CASE WHEN e.EventType='delivered' THEN e.EventAt END)) > DATE(MAX(e.EstimatedAt))
            THEN 1 ELSE 0 END AS DeliveredLate,
       TIMESTAMPDIFF(MINUTE, MAX(e.EventAt), c.LastEventAt) AS MinutesInCurrentStage,
       TIMESTAMPDIFF(MINUTE,
         MAX(CASE WHEN e.EventType='approved' THEN e.EventAt END),
         MAX(CASE WHEN e.EventType='carrier' THEN e.EventAt END)) AS ApprovalToCarrierMinutes,
       TIMESTAMPDIFF(MINUTE,
         MAX(CASE WHEN e.EventType='carrier' THEN e.EventAt END),
         MAX(CASE WHEN e.EventType='delivered' THEN e.EventAt END)) AS CarrierToDeliveryMinutes
FROM DemoOrderEvent e CROSS JOIN DemoReplayCheckpoint c
WHERE c.Id=1
GROUP BY e.OrderId,c.LastEventAt;

CREATE OR REPLACE VIEW vw_DemoOperationalKPI AS
SELECT COUNT(*) AS VisibleOrders,
       COALESCE(SUM(CurrentStage='Awaiting approval'),0) AS AwaitingApprovalOrders,
       COALESCE(SUM(CurrentStage='Awaiting carrier'),0) AS AwaitingCarrierOrders,
       COALESCE(SUM(CurrentStage='In transit'),0) AS InTransitOrders,
       COALESCE(SUM(CurrentStage='Delivered'),0) AS DeliveredOrders,
       COALESCE(SUM(PastEstimate),0) AS PastEstimateOrders,
       COALESCE(SUM(DeliveredLate),0) AS LateDeliveredOrders,
       ROUND(AVG(ApprovalToCarrierMinutes),1) AS AvgApprovalToCarrierMinutes,
       ROUND(AVG(CarrierToDeliveryMinutes),1) AS AvgCarrierToDeliveryMinutes
FROM vw_DemoOrderCurrent;
