#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
from dotenv import load_dotenv
import branca
import folium
from folium import plugins
import geopandas as gpd
import pandas as pd

load_dotenv()

gdf = gpd.read_file("data/map2026.geojson")
# Check for EPSG 4326 for folium compatibility
print(gdf.crs)
gdf.head()


# In[2]:


# Create new columns that shows partisan lean (e.g. D+7.89) for visualization tooltips
def partisan_text(val):
    if val is None or str(val).strip() in ['', 'nan', 'None']: 
        return "EVEN"
    try:
        num = val * 100
        if abs(num) < .01: return "EVEN"
        elif num < 0: return f"Trump+{abs(num):.2f}"
        elif num > 0: return f"Harris+{num:.2f}"
        return "EVEN"
    except ValueError: 
        return str(val)

gdf['Margin Partisan'] = gdf['Margin 24'].apply(partisan_text)
gdf['Margin New Partisan'] = gdf['Margin New'].apply(partisan_text)
gdf['Margin Shift Partisan'] = gdf['Margin Shift'].apply(partisan_text)


# In[3]:


# Color scheme
def color_scheme(margin):
    COLOR_MIDPOINT   = (140, 140, 140)
    COLOR_RED_START  = (255, 165, 165)
    COLOR_BLUE_START = (173, 216, 230)
    COLOR_RED_MID    = (200,  40,  40)
    COLOR_BLUE_MID   = ( 40,  90,  160)
    COLOR_DARKRED    = ( 90,   0,   0)
    COLOR_NAVYBLUE   = (  5,  15,   50)

    def interpolate(val, min_val, max_val, color_start, color_end):
        fraction = (val - min_val) / (max_val - min_val)
        fraction = max(0.0, min(1.0, fraction))
        r = int(color_start[0] + (color_end[0] - color_start[0]) * fraction)
        g = int(color_start[1] + (color_end[1] - color_start[1]) * fraction)
        b = int(color_start[2] + (color_end[2] - color_start[2]) * fraction)
        return f"rgb({r},{g},{b})"

    if abs(margin) < 0.0005:
        return f"rgb({COLOR_MIDPOINT[0]},{COLOR_MIDPOINT[1]},{COLOR_MIDPOINT[2]})"
    elif margin >= 0.0005:
        if margin <= 0.01: return interpolate(margin, 0.00, 0.01, COLOR_MIDPOINT, COLOR_BLUE_START)
        elif margin <= 0.23: return interpolate(margin, 0.01, 0.23, COLOR_BLUE_START, COLOR_BLUE_MID)
        else: return interpolate(margin, 0.23, 0.45, COLOR_BLUE_MID, COLOR_NAVYBLUE)
    else:
        if margin >= -0.01: return interpolate(margin, 0.00, -0.01, COLOR_MIDPOINT, COLOR_RED_START)
        elif margin >= -0.23: return interpolate(margin, -0.01, -0.23, COLOR_RED_START, COLOR_RED_MID)
        else: return interpolate(margin, -0.23, -0.45, COLOR_RED_MID, COLOR_DARKRED)


# In[4]:


# --- Filter Targeted / Impacted Districts ---
gdf_targeted = gdf[gdf['Targeted'] == True].copy()

# Helper to format district codes (e.g., "TX34" -> "TX-34")
def format_district_code(code):
    if not isinstance(code, str) or len(code) < 3:
        return str(code)
    return f"{code[:2]}-{code[2:]}"

# 1. Flip / Direction Counts for Targeted Districts
favored_dem = int((gdf_targeted['Margin New'] > 0).sum())
favored_rep = int((gdf_targeted['Margin New'] < 0).sum())

# 2. Mean Presidential Vote Share of Impacted Districts
harris_new_pct = f"{gdf_targeted['Harris New'].mean() * 100:.1f}%"
trump_new_pct  = f"{gdf_targeted['Trump New'].mean() * 100:.1f}%"
harris_24_pct  = f"{gdf_targeted['Harris 24'].mean() * 100:.1f}%"
trump_24_pct   = f"{gdf_targeted['Trump 24'].mean() * 100:.1f}%"

# 3. Topline Redistricting Stats
# Box 1: Mean Partisan Shift
raw_mean_shift = gdf_targeted['Margin Shift'].abs().mean() * 100
mean_shift = f"{raw_mean_shift:.1f}%"

# Box 2: Median Partisan Lean
median_lean = f"{gdf_targeted['Margin New'].abs().median() * 100:.1f}%"

# Box 3: Mean Partisan Shift (Net) with dynamic color class
raw_net_shift = gdf_targeted['Margin Shift'].mean() * 100
net_shift = f"{'Harris +' if raw_net_shift > 0 else 'Trump +'}{abs(raw_net_shift):.2f}%"
net_shift_class = "dem" if raw_net_shift > 0 else "rep"

# Box 4: Median Impacted District with hyphenated format
sorted_targeted = gdf_targeted.sort_values(by='Margin New', ascending=True).reset_index(drop=True)
mid_impacted_idx = len(sorted_targeted) // 2
median_impacted_raw = sorted_targeted.loc[mid_impacted_idx, 'District']
median_impacted_dist = format_district_code(median_impacted_raw)

median_impacted_margin_val = sorted_targeted.loc[mid_impacted_idx, 'Margin New'] * 100
median_impacted_class = "dem" if median_impacted_margin_val > 0 else "rep"
median_impacted_lean = f"{'Harris +' if median_impacted_margin_val > 0 else 'Trump +'}{abs(median_impacted_margin_val):.1f}%"
median_impacted_val = f"{median_impacted_dist}, {median_impacted_lean}"

# Initialize the base dictionary so Cell 5 can update it safely
sidebar_context = {
    "favored_dem": favored_dem,
    "favored_rep": favored_rep,
    "harris_new_pct": harris_new_pct,
    "trump_new_pct": trump_new_pct,
    "harris_24_pct": harris_24_pct,
    "trump_24_pct": trump_24_pct,
    "mean_shift": mean_shift,
    "median_lean": median_lean,
    "net_shift": net_shift,
    "net_shift_class": net_shift_class,
    "median_impacted_val": median_impacted_val,
    "median_impacted_dist": median_impacted_dist,
    "median_impacted_lean": median_impacted_lean,
    "median_impacted_class": median_impacted_class
}


# In[5]:


# ==============================================================================
# TIPPING POINT DISTRICT & GENERIC CONGRESSIONAL BALLOT (SEAT BIAS) ADVANTAGE 
# ==============================================================================
house_natl_path = "data/house_2024_national.csv"
if not os.path.exists(house_natl_path):
    alt_path = "../data/house_2024_national.csv"
    if os.path.exists(alt_path):
        house_natl_path = alt_path

if os.path.exists(house_natl_path):
    house_natl = pd.read_csv(house_natl_path)
    
    # Merge national dataset with newly redrawn district margins
    house_natl = house_natl.merge(gdf[['District', 'Margin New']], on='District', how='left')
    house_natl['Margin_Post'] = house_natl['Margin New'].combine_first(house_natl['Margin_2party'])
    
    # 1. Prior Tipping Point (2024 General Election)
    # Sorted descending from Dem advantage to GOP advantage; 218th seat is index 217
    sorted_24 = house_natl.sort_values(by='Margin_2party', ascending=False).reset_index(drop=True)
    raw_old_name = sorted_24.loc[217, 'District']
    tipping_old_name = format_district_code(raw_old_name)
    val_24 = sorted_24.loc[217, 'Margin_2party'] * 100
    tipping_old_margin = f"{'D +' if val_24 > 0 else 'R +'}{abs(val_24):.1f}%"
    tipping_old_class = "dem" if val_24 > 0 else "rep"

    # 2. Post-Redistricting Tipping Point
    sorted_new = house_natl.sort_values(by='Margin_Post', ascending=False).reset_index(drop=True)
    raw_new_name = sorted_new.loc[217, 'District']
    tipping_new_name = format_district_code(raw_new_name)
    val_new = sorted_new.loc[217, 'Margin_Post'] * 100
    tipping_new_margin = f"{'D +' if val_new > 0 else 'R +'}{abs(val_new):.1f}%"
    tipping_new_class = "dem" if val_new > 0 else "rep"

    # 3. Dynamic Generic Congressional Ballot Advantage (Seat Bias)
    # Formula: (Post-redistricting seats won / 435) - National Popular Vote Share
    post_rep_seats = int((house_natl['Margin_Post'] < 0).sum())
    post_dem_seats = int((house_natl['Margin_Post'] > 0).sum())
    total_house_seats = len(house_natl) if len(house_natl) > 0 else 435
    
    # Two-party national popular vote estimate derived from district margins
    mean_national_margin = house_natl['Margin_2party'].mean()
    natl_gop_vote_share = 0.50 - (mean_national_margin / 2.0)
    natl_dem_vote_share = 0.50 + (mean_national_margin / 2.0)
    
    # Calculate seat bias for whichever party holds the post-redistricting seat majority
    if post_rep_seats >= post_dem_seats:
        seat_share = post_rep_seats / total_house_seats
        advantage_val = (seat_share - natl_gop_vote_share) * 100
        ballot_adv_party = "R"
        ballot_adv_class = "rep"
    else:
        seat_share = post_dem_seats / total_house_seats
        advantage_val = (seat_share - natl_dem_vote_share) * 100
        ballot_adv_party = "D"
        ballot_adv_class = "dem"
        
    ballot_adv_display = f"{ballot_adv_party} +{abs(advantage_val):.2f}%"

else:
    # Fallback placeholders if house_2024_national.csv has not been compiled yet
    tipping_new_name = "CO-08"
    tipping_new_margin = "R +0.8%"
    tipping_new_class = "rep"
    tipping_old_name = "CO-08"
    tipping_old_margin = "R +0.4%"
    tipping_old_class = "rep"
    ballot_adv_display = "R +2.14%"
    ballot_adv_class = "rep"

# Update sidebar_context dictionary with tipping point & seat bias values
sidebar_context.update({
    "tipping_new_name": tipping_new_name,
    "tipping_new_margin": tipping_new_margin,
    "tipping_new_class": tipping_new_class,
    "tipping_old_name": tipping_old_name,
    "tipping_old_margin": tipping_old_margin,
    "tipping_old_class": tipping_old_class,
    "ballot_adv_display": ballot_adv_display,
    "ballot_adv_class": ballot_adv_class
})


# In[6]:


# Define static assets and variable
# Title card and navigation
HEADER_HTML_CONTENT = open('./src/components/header.html', encoding='utf-8').read()

# Sidebar
with open('./src/components/sidebar.html', 'r', encoding='utf-8') as f:
    sidebar_template = f.read()

for key, value in sidebar_context.items():
    sidebar_template = sidebar_template.replace(f"{{{key}}}", str(value))

SIDEBAR_HTML_CONTENT = sidebar_template

# Footer / copyright
FOOTER_HTML_CONTENT = open('./src/components/footer.html', encoding='utf-8').read()

# Scripts and styling
with open('./src/static/style.css', 'r', encoding='utf-8') as f:
    css = f.read()
with open('./src/static/scripts.js', 'r', encoding='utf-8') as f:
    scripts = f.read()

# Legend parameters 
LEGEND_BOUNDS = [-0.45, -0.23, -0.01, 0.0, 0.01, 0.23, 0.45]
LEGEND_COLORS = ['#5A0000', '#C82828', '#FF6E6E', '#8C8C8C', '#ADD8E6', '#285AA0', '#050F32']
LEGEND_TICKS  = [-0.40, -0.20, 0.0, 0.20, 0.40]

centroid = gdf.unary_union.centroid
center = [centroid.y+3, centroid.x-7]

# Map boundary controls
MAP_OPTIONS = {
    'zoom_start': 5,
    'min_zoom': 5,
    'max_zoom': 8,
    'min_lat': center[0]-25,
    'max_lat': center[0]+25,
    'min_long': center[1]-30,
    'max_long': center[1]+35,
}


# In[7]:


# Main function for map initialization and compilation
def compile_map(filename, target_column, tooltip_config, legend_caption):
    # Base canvas
    m = folium.Map(
        location=center,
        zoom_start=MAP_OPTIONS['zoom_start'], 
        tiles=None, 
        min_zoom=MAP_OPTIONS['min_zoom'], 
        max_zoom=MAP_OPTIONS['max_zoom'],
        min_lat=MAP_OPTIONS['min_lat'],
        max_lat=MAP_OPTIONS['max_lat'],
        min_lon=MAP_OPTIONS['min_long'],
        max_lon=MAP_OPTIONS['max_long'],
        max_bounds=True,
        max_bounds_viscosity=1.0         # Prevents user from moving past boundaries
    )
    m.options['maxZoom'] = MAP_OPTIONS['max_zoom']

    CARTO_KEY = os.getenv("CARTO_API_KEY")

    # 1. Base Map Layer: CARTO Voyager (Richer OSM features, soft natural colors, no labels)
    folium.TileLayer(
        tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{{z}}/{{x}}/{{y}}.png?key={CARTO_KEY}",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>',
        name="Base Map",
        subdomains="abcd",
        control=False,
        min_zoom=MAP_OPTIONS["min_zoom"],
        max_zoom=MAP_OPTIONS["max_zoom"],
    ).add_to(m)

    # Hatch pattern to show targeted districts
    hatch_pattern = plugins.pattern.StripePattern(
        angle=-45, color='black', space_color='transparent', weight=3, space_weight=5
    ).add_to(m)

    # Styling functions
    def style_main(feature):
        margin = feature['properties'].get(target_column, 0)
        return {'fillColor': color_scheme(margin), 'color': 'black', 'weight': 1, 'fillOpacity': 0.8}
        
    def style_hatch(feature):
        if feature['properties'].get('Targeted', False):
            return {'fillPattern': hatch_pattern, 'fillOpacity': 0.6, 'color': 'transparent'}
        return {'fillColor': 'transparent', 'color': 'transparent'}

    # Compile data feature layers
    group = folium.FeatureGroup(name=legend_caption, control=False, show=True).add_to(m)
    folium.GeoJson(gdf, style_function=style_main).add_to(group)
    folium.GeoJson(gdf, style_function=style_hatch, tooltip=tooltip_config).add_to(group)

    # 2. Labels overlay: Voyager Labels (Richer typography and city markers above polygons)
    folium.map.CustomPane("labels_top", z_index=450).add_to(m)
    folium.TileLayer(
        tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{{z}}/{{x}}/{{y}}.png?key={CARTO_KEY}",
        attr='&copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>',
        pane="labels_top",
        subdomains="abcd",
        control=False,
        min_zoom=MAP_OPTIONS["min_zoom"],
        max_zoom=MAP_OPTIONS["max_zoom"],
    ).add_to(m)
    
    # Render legend
    legend = branca.colormap.LinearColormap(
        colors=LEGEND_COLORS, 
        index=LEGEND_BOUNDS, 
        vmin=min(LEGEND_BOUNDS), 
        vmax=max(LEGEND_BOUNDS), 
        caption=legend_caption
    )
    legend.tick_labels = LEGEND_TICKS
    legend.height = 45
    m.add_child(legend)

    # Append header, CSS, scripts, and footer
    m.get_root().html.add_child(folium.Element(HEADER_HTML_CONTENT))
    m.get_root().html.add_child(folium.Element(SIDEBAR_HTML_CONTENT))
    m.get_root().html.add_child(folium.Element(FOOTER_HTML_CONTENT))
    m.get_root().header.add_child(folium.Element(f"<style>{css}</style>"))
    m.get_root().html.add_child(folium.Element(f"<script>{scripts}</script>"))

    m.save(filename)
    print(f"Successfully compiled: {filename}")
    # Views map in notebook
    return m


# In[8]:


# Tooltips on hover
tooltip_lean = folium.GeoJsonTooltip(
    fields=['District No.', 'Margin New Partisan', 'Margin Partisan'], 
    aliases=['2026 District No.:', 'Pres. Margin (Post-Redistricting):', "Pres. Margin (2024 Boundaries):"],
    style="background-color:rgba(255,255,255,0.95); color:#1a1a1a; font-size:12px; font-weight:bold; border:2px solid #222;",
    localize=True
)

tooltip_shift = folium.GeoJsonTooltip(
    fields=['District No.', 'Margin Shift Partisan', 'Margin Partisan'], 
    aliases=['2026 District No.:', "Shift from 2024 District's Pres. Margin:", "Pres. Margin (2024 Boundaries):"],
    style="background-color:rgba(255,255,255,0.95); color:#1a1a1a; font-size:12px; font-weight:bold; border:2px solid #222; border-radius:4px;",
    localize=True
)


# In[9]:


# Compile margin lean map
compile_map(
    filename="docs/index.html",
    target_column="Margin New",
    tooltip_config=tooltip_lean,
    legend_caption="Harris-Trump Margin (Striped = Targeted District)"
)


# In[10]:


# Compile margin shift map
compile_map(
    filename="docs/shift.html",
    target_column="Margin Shift",
    tooltip_config=tooltip_shift,
    legend_caption="Harris-Trump Margin Shift from 2024 Districts (Striped = Targeted District)"
)

