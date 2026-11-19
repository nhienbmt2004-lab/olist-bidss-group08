# Streamlit snapshot check · 15/03/2018

This folder contains CSV exports from MySQL for checking the RouteOps demo at the simulated date 15 March 2018.

Operational calculations exclude orders whose final Olist status is `canceled`; `invoiced` orders remain included. Olist does not provide a cancellation timestamp, so this is a final-status exclusion and cannot reconstruct when cancellation happened.

## Files

- `backend_reconciliation.csv`: as-of row counts, including how many canceled rows were excluded and invoiced orders retained.
- `route_summary.csv`: one row per seller-state → buyer-state route, with 30-day OTD, open orders, transit counts, overdue counts and GMV at risk.
- `map_geohash_cells.csv`: customer-location cells colored using route OTD, not a separate cell-level OTD.
- `rescue_queue_selected_route.csv`: open-order queue for the default route.
- `what_if_scenarios.csv`: arithmetic scenarios for delivered orders; these are not realized savings or causal effects.
- `seller_handover_selected_route.csv`: seller handover results for the default route.
- `excluded_canceled_orders.csv`: canceled orders removed from the operational queue.
- `open_orders_after_cancel_filter.csv`: the remaining open-order cohort for audit.

## Example: SP → RJ at 15/03/2018

- Delivered in the rolling 30-day window: 498; on time: 402; late: 96; OTD: 80.72%.
- Open at the simulated date: 724; handed to carrier: 640; no handover timestamp yet: 84.
- Open orders overdue by at least 3 days: 189; open GMV at risk: R$27,216.11; in-transit portion: R$18,675.42.

The delivered cohort used for OTD and the open queue are separate groups. An order can be in the open queue at the simulated date even if its eventual final status is `delivered`, when its delivery timestamp is after that simulated date.
