# Mid-Decade Redistricting Visualization

The primary goal of this project is to visualize the partisan shift of Congressional districts affected by the 2025–2026 mid-decade redistricting cycle. The targeted districts are highlighted with hatch (striped) color shading, while surrounding districts show how much the dominant party in the state had to dilute their own maps to sustain these gerrymanders.

Deployed at <https://rgao.github.io/redistricting_tracker>

### Features

#### Map Pages (Margin Lean Map & Margin Shift Map)
* **Interactive Leaflet Web Maps:** Custom dual-view maps toggling between post-redistricting partisan lean and shift from previous boundaries.
* **Bipartisan Divergent Color Ramps:** Continuous gradient styling representing vote margins dynamically from safe Democratic blue to safe Republican red.
* **Hatch Pattern Overlays:** Distinct striped visual overlay highlighting specifically targeted or altered districts.
* **Interactive Tooltips & Hover States:** Real-time popups on-hover showing district identifiers, presidential margins, and shifts.
* **Click-to-Lock Sidebar Panels:** Clicking any district locks the sidebar context view to display deep-dive analytics for that specific area.
* **Responsive Collapsible Sidebar:** Mobile-friendly sliding and toggleable metrics panel featuring statewide seat balance, presidential vote share breakdowns, and national tipping point trackers.

#### Analysis Page
* **Gerrymandering Effectiveness Metrics:** Evaluates the efficiency, seat share bias, and deviation from popular vote baselines resulting from mid-decade cycle adjustments.
* **Methodology Breakdowns:** Detailed explanations of blended partisan index formulas, vote-share aggregations, and national baseline comparisons.

### Tools and Technology

* **AI Assistance:** Google Gemini
* **Languages & Core Web:** Python, Jupyter Notebook, HTML5, CSS3, JavaScript
* **Spatial & Data Analysis Libraries:** pandas, geopandas, folium
* **Basemaps & Tile Styling:** CartoDB Raster Tiles (Voyager labels and base layers)

### Data Sources

* **Post-Redistricting Maps & Boundaries:** Collected using Dave's Redistricting: <https://davesredistricting.org/>
* **2024 House Election Results:** Sourced from MIT Election Lab: <https://electionlab.mit.edu>
* **Louisiana Custom GeoJSON:** Created manually using Congressional district and precinct block files from Louisiana's state government portal (<https://redist.legis.la.gov>) prior to official update integration on DRA.

---

### Licensing & Usage

Code released under the [MIT License](https://opensource.org). Map visualizations, refined spatial assets, and calculated data products are licensed under [CC BY 4.0](https://creativecommons.org).

&copy; 2026 Xin "Ryan" Gao &bull; [View Repository on GitHub](https://github.com/rgao/redistricting_tracker)