CREATE TABLE ETLRun (
  RunId BIGINT AUTO_INCREMENT PRIMARY KEY,
  StartedAtUtc DATETIME(6) NOT NULL,
  FinishedAtUtc DATETIME(6),
  Status VARCHAR(20) NOT NULL,
  SourceDirectory VARCHAR(500) NOT NULL,
  ErrorMessage TEXT
) ENGINE=InnoDB;
CREATE TABLE ETLStepLog (
  StepId BIGINT AUTO_INCREMENT PRIMARY KEY,
  RunId BIGINT NOT NULL,
  StepName VARCHAR(100) NOT NULL,
  RowCount BIGINT,
  FinishedAtUtc DATETIME(6) NOT NULL,
  FOREIGN KEY (RunId) REFERENCES ETLRun(RunId)
) ENGINE=InnoDB;
CREATE TABLE ETLReconciliation (
  ReconciliationId BIGINT AUTO_INCREMENT PRIMARY KEY,
  RunId BIGINT NOT NULL,
  Metric VARCHAR(80) NOT NULL,
  SourceValue DECIMAL(20,2) NOT NULL,
  TargetValue DECIMAL(20,2) NOT NULL,
  Difference DECIMAL(20,2) NOT NULL,
  Passed TINYINT NOT NULL,
  FOREIGN KEY (RunId) REFERENCES ETLRun(RunId)
) ENGINE=InnoDB;
CREATE TABLE DataQualityIssues (
  IssueId INT AUTO_INCREMENT PRIMARY KEY,
  IssueCode VARCHAR(80) NOT NULL UNIQUE,
  IssueCount BIGINT NOT NULL,
  Severity VARCHAR(10) NOT NULL,
  Treatment VARCHAR(500) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE stg_Customers (customer_id CHAR(32),customer_unique_id CHAR(32),customer_zip_code_prefix VARCHAR(10),customer_city VARCHAR(100),customer_state CHAR(2)) ENGINE=InnoDB;
CREATE TABLE stg_Geolocation (geolocation_zip_code_prefix VARCHAR(10),geolocation_lat VARCHAR(40),geolocation_lng VARCHAR(40),geolocation_city VARCHAR(100),geolocation_state CHAR(2)) ENGINE=InnoDB;
CREATE TABLE stg_Orders (order_id CHAR(32),customer_id CHAR(32),order_status VARCHAR(20),order_purchase_timestamp VARCHAR(32),order_approved_at VARCHAR(32),order_delivered_carrier_date VARCHAR(32),order_delivered_customer_date VARCHAR(32),order_estimated_delivery_date VARCHAR(32)) ENGINE=InnoDB;
CREATE TABLE stg_OrderItems (order_id CHAR(32),order_item_id VARCHAR(10),product_id CHAR(32),seller_id CHAR(32),shipping_limit_date VARCHAR(32),price VARCHAR(30),freight_value VARCHAR(30)) ENGINE=InnoDB;
CREATE TABLE stg_Payments (order_id CHAR(32),payment_sequential VARCHAR(10),payment_type VARCHAR(30),payment_installments VARCHAR(10),payment_value VARCHAR(30)) ENGINE=InnoDB;
CREATE TABLE stg_Reviews (review_id CHAR(32),order_id CHAR(32),review_score VARCHAR(10),review_comment_title TEXT,review_comment_message TEXT,review_creation_date VARCHAR(32),review_answer_timestamp VARCHAR(32)) ENGINE=InnoDB;
CREATE TABLE stg_Products (product_id CHAR(32),product_category_name VARCHAR(100),product_name_lenght VARCHAR(20),product_description_lenght VARCHAR(20),product_photos_qty VARCHAR(20),product_weight_g VARCHAR(30),product_length_cm VARCHAR(30),product_height_cm VARCHAR(30),product_width_cm VARCHAR(30)) ENGINE=InnoDB;
CREATE TABLE stg_Sellers (seller_id CHAR(32),seller_zip_code_prefix VARCHAR(10),seller_city VARCHAR(100),seller_state CHAR(2)) ENGINE=InnoDB;
CREATE TABLE stg_CategoryTranslation (product_category_name VARCHAR(100),product_category_name_english VARCHAR(100)) ENGINE=InnoDB;

CREATE TABLE DimDate (
  DateKey INT PRIMARY KEY,FullDate DATE NOT NULL UNIQUE,DayNumber TINYINT NOT NULL,
  MonthNumber TINYINT NOT NULL,QuarterNumber TINYINT NOT NULL,YearNumber SMALLINT NOT NULL,
  DayOfWeekNumber TINYINT NOT NULL,IsWeekend TINYINT NOT NULL
) ENGINE=InnoDB;
CREATE TABLE DimGeography (
  GeographyKey INT AUTO_INCREMENT PRIMARY KEY,ZipCodePrefix CHAR(5) NOT NULL UNIQUE,
  City VARCHAR(100),StateCode CHAR(2),Latitude DECIMAL(18,15),Longitude DECIMAL(18,15)
) ENGINE=InnoDB;
CREATE TABLE DimCustomer (
  CustomerKey INT AUTO_INCREMENT PRIMARY KEY,CustomerId CHAR(32) NOT NULL UNIQUE,
  CustomerUniqueId CHAR(32),GeographyKey INT,
  FOREIGN KEY (GeographyKey) REFERENCES DimGeography(GeographyKey)
) ENGINE=InnoDB;
CREATE TABLE DimSeller (
  SellerKey INT AUTO_INCREMENT PRIMARY KEY,SellerId CHAR(32) NOT NULL UNIQUE,
  GeographyKey INT,FOREIGN KEY (GeographyKey) REFERENCES DimGeography(GeographyKey)
) ENGINE=InnoDB;
CREATE TABLE DimCategory (
  CategoryKey INT AUTO_INCREMENT PRIMARY KEY,CategoryName VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;
CREATE TABLE DimProduct (
  ProductKey INT AUTO_INCREMENT PRIMARY KEY,ProductId CHAR(32) NOT NULL UNIQUE,
  CategoryKey INT,ProductWeightG DECIMAL(12,2),ProductLengthCm DECIMAL(12,2),
  ProductHeightCm DECIMAL(12,2),ProductWidthCm DECIMAL(12,2),
  FOREIGN KEY (CategoryKey) REFERENCES DimCategory(CategoryKey)
) ENGINE=InnoDB;

CREATE TABLE FactOrderDelivery (
  OrderDeliveryKey BIGINT AUTO_INCREMENT PRIMARY KEY,OrderId CHAR(32) NOT NULL UNIQUE,
  CustomerKey INT NOT NULL,PurchaseDateKey INT NOT NULL,ApprovedDateKey INT,
  CarrierDateKey INT,DeliveredDateKey INT,EstimatedDeliveryDateKey INT,
  OrderStatus VARCHAR(20),DeliveryDays INT,DelayDays INT,IsDelivered TINYINT NOT NULL,
  IsCancelled TINYINT NOT NULL,IsOnTime TINYINT,ItemCount INT NOT NULL,SellerCount INT NOT NULL,
  GMV DECIMAL(18,2) NOT NULL,FreightValue DECIMAL(18,2) NOT NULL,
  PaymentValue DECIMAL(18,2),ReviewScore DECIMAL(4,2),
  FOREIGN KEY (CustomerKey) REFERENCES DimCustomer(CustomerKey),
  FOREIGN KEY (PurchaseDateKey) REFERENCES DimDate(DateKey),
  FOREIGN KEY (ApprovedDateKey) REFERENCES DimDate(DateKey),
  FOREIGN KEY (CarrierDateKey) REFERENCES DimDate(DateKey),
  FOREIGN KEY (DeliveredDateKey) REFERENCES DimDate(DateKey),
  FOREIGN KEY (EstimatedDeliveryDateKey) REFERENCES DimDate(DateKey),
  INDEX IX_FOD_Date(PurchaseDateKey),INDEX IX_FOD_Customer(CustomerKey)
) ENGINE=InnoDB;
CREATE TABLE FactOrderItem (
  OrderItemKey BIGINT AUTO_INCREMENT PRIMARY KEY,OrderId CHAR(32) NOT NULL,
  OrderItemId INT NOT NULL,PurchaseDateKey INT NOT NULL,CustomerKey INT NOT NULL,
  SellerKey INT NOT NULL,ProductKey INT NOT NULL,Price DECIMAL(12,2) NOT NULL,
  FreightValue DECIMAL(12,2) NOT NULL,ShippingLimitDate DATETIME,
  UNIQUE KEY UQ_FOI(OrderId,OrderItemId),
  FOREIGN KEY (PurchaseDateKey) REFERENCES DimDate(DateKey),
  FOREIGN KEY (CustomerKey) REFERENCES DimCustomer(CustomerKey),
  FOREIGN KEY (SellerKey) REFERENCES DimSeller(SellerKey),
  FOREIGN KEY (ProductKey) REFERENCES DimProduct(ProductKey),
  INDEX IX_FOI_DateSeller(PurchaseDateKey,SellerKey),INDEX IX_FOI_Product(ProductKey)
) ENGINE=InnoDB;
CREATE TABLE FactPayment (
  PaymentKey BIGINT AUTO_INCREMENT PRIMARY KEY,OrderId CHAR(32) NOT NULL,
  PaymentSequential INT NOT NULL,PurchaseDateKey INT NOT NULL,CustomerKey INT NOT NULL,
  PaymentType VARCHAR(30),Installments INT,PaymentValue DECIMAL(12,2) NOT NULL,
  UNIQUE KEY UQ_FP(OrderId,PaymentSequential),
  FOREIGN KEY (PurchaseDateKey) REFERENCES DimDate(DateKey),
  FOREIGN KEY (CustomerKey) REFERENCES DimCustomer(CustomerKey),
  INDEX IX_FP_Date(PurchaseDateKey)
) ENGINE=InnoDB;
CREATE TABLE FactReview (
  ReviewKey BIGINT AUTO_INCREMENT PRIMARY KEY,ReviewId CHAR(32) NOT NULL,
  OrderId CHAR(32) NOT NULL,CustomerKey INT NOT NULL,ReviewDateKey INT,
  ReviewScore TINYINT,HasComment TINYINT NOT NULL,ResponseHours INT,
  UNIQUE KEY UQ_FR(ReviewId,OrderId),
  FOREIGN KEY (CustomerKey) REFERENCES DimCustomer(CustomerKey),
  FOREIGN KEY (ReviewDateKey) REFERENCES DimDate(DateKey),
  INDEX IX_FR_Date(ReviewDateKey)
) ENGINE=InnoDB;

CREATE INDEX IX_STG_Items_Order ON stg_OrderItems(order_id);
CREATE INDEX IX_STG_Orders_Order ON stg_Orders(order_id);
CREATE INDEX IX_STG_Payments_Order ON stg_Payments(order_id);
CREATE INDEX IX_STG_Reviews_Order ON stg_Reviews(order_id);
