# Mid-Decade Redistricting Visualization

The primary goal of this project is to visualize the partisan shift of Congressional districts affected by the 2025-2026 mid-decade redistricting cycle. The targeted districts are shown with hatch (striped) color shading. Most other districts surrounding the targeted districts shift towards the opposition, indicating how much the dominant party in the state had to dilute their own districts to sustain these gerrymanders.

Deployed at rgao.github.io/redistricting_tracker

### Features

* Maps showing both the partisan lean and shift of the relevant states
* Default sidebar info on redistricting overview and stats
* Interactivity to show in-depth info on affected districts on-hover and on-click
* Analysis page to show the effectiveness of the gerrymanders (in-progress)

### Tools and Technology

* Google Gemini
* Python, jupyter notebook, HTML/CSS/javascript
* pandas, geopandas, folium, CartoDB

##### Data Sources

Post-redistricting maps and data are collected using Dave's Redistricting: https://davesredistricting.org/
2024 House election results sourced from MIT Election Lab: https://electionlab.mit.edu

Before DRA updated their data to include Louisiana, Alabama, and Tennessee, I created my own .geojson file for Louisiana using Congressional district and precinct block files from Louisiana's government website:

https://redist.legis.la.gov/