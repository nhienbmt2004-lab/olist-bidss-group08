# RouteOps UI ideas and backup notes

## 2026-11-19 - Route Overview map reference

Use the supplied reference image as the target for screen 1:

- Put a compact, horizontal legend in a white rounded strip above the map.
- Keep a geographic basemap beneath the square delivery cells.
- Color each cell by its seller-state to buyer-state route OTD: green at 90%+, yellow from 85% to below 90%, red below 85%, and light lavender-gray when fewer than 30 deliveries are observed.
- Label cells with the state pair and route OTD; show `<30` for cells whose route lacks the minimum sample.
- On hover, show route OTD over 30 days, completed orders on that route, and orders represented in the cell.
- Keep the priority route list beside the map. Each route should show OTD, delivered count, currently open count, delayed share, and open overdue GMV at risk.

These thresholds and risk amounts are illustrative operational indicators calculated from records observable by the simulated date. They do not identify carriers or establish causal or realized financial impact.

Implementation history and a pre-change source snapshot are recorded in `docs/streamlit-change-log.md` and `backups/streamlit/2026-11-19/priority-routes-card-layout/`.
