# Phase 2 — Data Profiling, Cleaning and Data Warehouse Design

## Business rules

- **Delivered order:** `order_status = 'delivered'` and `order_delivered_customer_date` is present.
- **Cancelled order:** `order_status` is `canceled` or `unavailable`.
- **Delivery time (days):** purchase timestamp to customer delivery timestamp.
- **Delay days:** `MAX(0, delivered date - estimated delivery date)`; a delivery is on time when this is zero.
- **GMV:** sum of item `price`; freight is reported separately to avoid mixing merchandise and logistics value.
- **AOV:** GMV divided by distinct orders in the selected filter context.
- **Freight ratio:** total freight divided by GMV; return `NULL` when GMV is zero.
- **Review score:** one latest review per order, selected by answer timestamp and then review id.
- **Multi-seller order:** an order with more than one distinct seller. `FactOrderDelivery` remains one row per order; seller metrics use `FactOrderItem`.
- **Payments:** aggregate all payment rows to order level before joining to an order fact to prevent fan-out.
- **Seller score:** calculated in the semantic layer from on-time rate, average review, cancellation rate and volume; weights must be documented/versioned before publication.

## Declared grain

| Fact | Grain |
|---|---|
| FactOrderDelivery | One row per order |
| FactOrderItem | One row per order item (`order_id`, `order_item_id`) |
| FactPayment | One row per payment sequence |
| FactReview | One row per review |

## Bus matrix

| Business process | Date | Customer | Seller | Product | Category | Geography | Order (degenerate) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Order delivery | ✓ | ✓ |  |  |  | ✓ | ✓ |
| Order item / sales | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Payment | ✓ | ✓ |  |  |  |  | ✓ |
| Review | ✓ | ✓ |  |  |  |  | ✓ |

## Quality handling

ZIP prefixes are left-padded to five characters; city/state are trimmed and upper-cased. When a ZIP exists in geolocation, its most frequent city/state pair is used. Product categories use the English translation when available and otherwise retain the Portuguese value, finally falling back to `unknown`. Invalid dates/numbers become `NULL` via `TRY_CONVERT`. Source staging tables remain unchanged for traceability.

## Load order

1. Run staging ETL packages.
2. Run `04_data_profiling.sql` and resolve all non-zero `ERROR` rows. The script recreates `DataQualityIssues` as a current snapshot on each run; export it first if a prior run must be retained.
3. Create the clean views with `05_create_clean_views.sql`.
4. Create warehouse objects with `06_create_dw_tables.sql`.
5. Load dimensions before facts. Geography/category foreign keys may be `NULL` when a valid mapping is unavailable; fact rows require valid customer/date/seller/product keys, so reject or quarantine unmatched rows during ETL.

The SQL in this phase defines profiling, cleaning and the target schema. These scripts do not populate warehouse rows; use the Phase 3 ETL in `docs/phase-3-etl-powerbi.md` for that step.
