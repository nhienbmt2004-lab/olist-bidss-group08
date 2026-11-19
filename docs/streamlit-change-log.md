# Streamlit change log and recovery points

## Current snapshot — 2026-11-19, Route Overview map rules

**Specification source:** `document/Demo (3).pdf` map legend and insufficient-sample rule.

**Current behavior in `scripts/streamlit_dss_app.py`:**
- OpenStreetMap base map shows a Brazil-wide overview and the geohash-inspired cell grid.
- Floating legend is placed inside the map at the upper left.
- Route status is decided in this order: fewer than 30 delivered orders → gray; otherwise OTD ≥90% → green; 85% to <90% → yellow; OTD <85% → red.
- Cell text shows `<30` for insufficient samples and whole-number route OTD for qualified routes.
- The map only colors by the seller-state → buyer-state route OTD; current open-order delays do not change a cell's OTD color.
- Selecting a route outlines its cells. Selecting a cell zooms into that geohash.
- The map and Priority Routes panel remain side by side.

**Verification:** `py_compile` passed; Streamlit AppTest rendered Route Overview with zero exceptions; localhost:8501 returned HTTP 200.

**Current recovery snapshot:** [`backups/streamlit/2026-11-19/document-color-rule-v2/streamlit_dss_app.py`](../backups/streamlit/2026-11-19/document-color-rule-v2/streamlit_dss_app.py)

Restore this snapshot from the repository root:
```powershell
Copy-Item -LiteralPath 'backups/streamlit/2026-11-19/document-color-rule-v2/streamlit_dss_app.py' -Destination 'scripts/streamlit_dss_app.py' -Force
```

**Previous map draft snapshot:** `backups/streamlit/2026-11-19/pre-document-color-fix/streamlit_dss_app.py` (before correcting the insufficient-sample color from purple to document gray).



## Update - 2026-11-19, Route Overview map reference layout

**Request/reference:** User supplied a screenshot for screen 1 and asked to match its map style. The reference has a horizontal legend above the map, colored geohash cells labeled with seller/buyer state and route OTD, and a hover card showing route OTD, delivered route count, and orders in the cell.

**Changes in `scripts/streamlit_dss_app.py`:**
- Moved the four-category legend out of the Leaflet canvas into a horizontal bordered strip above the map, matching the reference hierarchy.
- Changed the insufficient-sample fill to a light lavender-gray to match the reference while retaining its gray / not-enough-data meaning.
- Increased map height slightly to give the grid more room.
- Hovering a cell now shows a sticky detail card with the route, rolling 30-day OTD, completed order count on the route, and order count in that cell; click behavior and selected-cell zoom remain available.
- Kept route color rules tied to route OTD and the existing <30 delivered sample rule. This is a visual adjustment; operational calculations are unchanged.
- Priority route detail is displayed as a compact two-part metric line under each route button for readability.

**Recovery snapshot before this update:** [`backups/streamlit/2026-11-19/priority-routes-card-layout/streamlit_dss_app.py`](../backups/streamlit/2026-11-19/priority-routes-card-layout/streamlit_dss_app.py)

**Design idea saved:** [`document/RouteOps-ideas.md`](../document/RouteOps-ideas.md)
