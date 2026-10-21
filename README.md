# Mid-Decade Redistricting Visualization

The primary goal of this project is to visualize the partisan shift of Congressional districts affected by the 2025–2026 mid-decade redistricting cycle. The targeted districts are highlighted with hatch (striped) color shading. Visitors directly view exactly how all the districts in an affected state were altered or diluted in order to sustain the gerrymanders. The analysis page includes visualizations displaying the effectiveness of each instance of redistricting, as well as the expected net seat changes of the relevant states due to gerrymandering. Explanations for metrics and methods are also in that page.

Deployed at <https://rgao.github.io/redistricting_tracker>

### Features

#### Map Pages (Margin Lean Map & Margin Shift Map)
* **Interactive Leaflet Web Maps:** Custom dual-view maps toggling between post-redistricting partisan lean and shift from previous boundaries.
* **Bipartisan Divergent Color Ramps:** Continuous gradient styling representing vote margins dynamically from safe Democratic blue to safe Republican red.
* **Hatch Pattern Overlays:** Stripe pattern indicate districts specifically targeted to flip.
* **Interactive Tooltips & Hover States:** Real-time popups on-hover showing district identifiers, presidential margins, and shifts.
* **Click-to-Lock Sidebar Panels:** Clicking any district locks the sidebar context view to display statistics for that specific district.
* **Responsive Collapsible Sidebar:** Mobile-friendly sliding and toggleable metrics panel featuring statewide seat balance, presidential vote share breakdowns, and national tipping point districts.

###### Work in Progress
* **Incorporate Polling and Systematic Data Pull:** Include polling into the model, and write a script to pull polling aggregates instead of hard-coding the 2026 environment.
* **Candidate Quality:** Incorporate candidate quality into the model to reflect more accurate results.

#### Analysis Page
* **Gerrymandering Effectiveness Metrics:** Chart visualizations display the effectiveness of each district's gerrymandering in successfully flipping, as well as the expected net seat changes of the state's delegation. 
* **National Environment Toggle:** Feature to change between the 2026 midterm environment (likely blue wave) and a theoretical neutral environment to see effectiveness of redistricting under different scenarios.
* **Methodology Breakdowns:** Detailed explanations of metrics and calculations, including the partisan index, redistricting effectiveness, expected value of net seat changes, and tipping point districts.

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