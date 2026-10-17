USE Olist_DW;
GO

/* Phase 2 schema. Run once on a new, empty Olist_DW database. */
CREATE TABLE dbo.DimDate (
    DateKey int NOT NULL PRIMARY KEY,
    FullDate date NOT NULL UNIQUE,
    DayNumber tinyint NOT NULL,
    MonthNumber tinyint NOT NULL,
    QuarterNumber tinyint NOT NULL,
    YearNumber smallint NOT NULL,
    DayOfWeekNumber tinyint NOT NULL,
    IsWeekend bit NOT NULL
);
CREATE TABLE dbo.DimGeography (
    GeographyKey int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    ZipCodePrefix char(5) NOT NULL UNIQUE,
    City nvarchar(100) NULL,
    StateCode char(2) NULL,
    Latitude decimal(18,15) NULL,
    Longitude decimal(18,15) NULL
);
CREATE TABLE dbo.DimCustomer (
    CustomerKey int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    CustomerId char(32) NOT NULL UNIQUE,
    CustomerUniqueId char(32) NOT NULL,
    GeographyKey int NULL REFERENCES dbo.DimGeography(GeographyKey)
);
CREATE TABLE dbo.DimSeller (
    SellerKey int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    SellerId char(32) NOT NULL UNIQUE,
    GeographyKey int NULL REFERENCES dbo.DimGeography(GeographyKey)
);
CREATE TABLE dbo.DimCategory (
    CategoryKey int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    CategoryName nvarchar(100) NOT NULL UNIQUE
);
CREATE TABLE dbo.DimProduct (
    ProductKey int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    ProductId char(32) NOT NULL UNIQUE,
    CategoryKey int NULL REFERENCES dbo.DimCategory(CategoryKey),
    ProductWeightG decimal(12,2) NULL,
    ProductLengthCm decimal(12,2) NULL,
    ProductHeightCm decimal(12,2) NULL,
    ProductWidthCm decimal(12,2) NULL
);
GO

CREATE TABLE dbo.FactOrderDelivery (
    OrderDeliveryKey bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    OrderId char(32) NOT NULL UNIQUE,
    CustomerKey int NOT NULL REFERENCES dbo.DimCustomer(CustomerKey),
    PurchaseDateKey int NOT NULL REFERENCES dbo.DimDate(DateKey),
    ApprovedDateKey int NULL REFERENCES dbo.DimDate(DateKey),
    CarrierDateKey int NULL REFERENCES dbo.DimDate(DateKey),
    DeliveredDateKey int NULL REFERENCES dbo.DimDate(DateKey),
    EstimatedDeliveryDateKey int NULL REFERENCES dbo.DimDate(DateKey),
    OrderStatus nvarchar(20) NULL,
    DeliveryDays int NULL,
    DelayDays int NULL,
    IsDelivered bit NOT NULL,
    IsCancelled bit NOT NULL,
    IsOnTime bit NULL,
    ItemCount int NOT NULL,
    SellerCount int NOT NULL,
    GMV decimal(18,2) NOT NULL,
    FreightValue decimal(18,2) NOT NULL,
    PaymentValue decimal(18,2) NULL,
    ReviewScore decimal(4,2) NULL
);
CREATE TABLE dbo.FactOrderItem (
    OrderItemKey bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    OrderId char(32) NOT NULL,
    OrderItemId int NOT NULL,
    PurchaseDateKey int NOT NULL REFERENCES dbo.DimDate(DateKey),
    CustomerKey int NOT NULL REFERENCES dbo.DimCustomer(CustomerKey),
    SellerKey int NOT NULL REFERENCES dbo.DimSeller(SellerKey),
    ProductKey int NOT NULL REFERENCES dbo.DimProduct(ProductKey),
    Price decimal(12,2) NOT NULL,
    FreightValue decimal(12,2) NOT NULL,
    ShippingLimitDate datetime2(0) NULL,
    CONSTRAINT UQ_FactOrderItem UNIQUE(OrderId,OrderItemId)
);
CREATE TABLE dbo.FactPayment (
    PaymentKey bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    OrderId char(32) NOT NULL,
    PaymentSequential int NOT NULL,
    PurchaseDateKey int NOT NULL REFERENCES dbo.DimDate(DateKey),
    CustomerKey int NOT NULL REFERENCES dbo.DimCustomer(CustomerKey),
    PaymentType nvarchar(30) NULL,
    Installments int NULL,
    PaymentValue decimal(12,2) NOT NULL,
    CONSTRAINT UQ_FactPayment UNIQUE(OrderId,PaymentSequential)
);
CREATE TABLE dbo.FactReview (
    ReviewKey bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    ReviewId char(32) NOT NULL,
    OrderId char(32) NOT NULL,
    CustomerKey int NOT NULL REFERENCES dbo.DimCustomer(CustomerKey),
    ReviewDateKey int NULL REFERENCES dbo.DimDate(DateKey),
    ReviewScore tinyint NULL CHECK(ReviewScore BETWEEN 1 AND 5),
    HasComment bit NOT NULL,
    ResponseHours int NULL,
    CONSTRAINT UQ_FactReview UNIQUE(ReviewId,OrderId)
);
GO

CREATE INDEX IX_FOD_PurchaseDate ON dbo.FactOrderDelivery(PurchaseDateKey);
CREATE INDEX IX_FOI_DateSeller ON dbo.FactOrderItem(PurchaseDateKey,SellerKey);
CREATE INDEX IX_FOI_Product ON dbo.FactOrderItem(ProductKey);
CREATE INDEX IX_FP_Date ON dbo.FactPayment(PurchaseDateKey);
CREATE INDEX IX_FR_Date ON dbo.FactReview(ReviewDateKey);
GO
