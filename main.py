#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
from dotenv import load_dotenv
import branca
import folium
from folium import plugins
import geopandas as gpd
import pandas as pd

load_dotenv()

gdf = gpd.read_file("docs/map2026.geojson")
print(gdf.crs)
gdf.head()


# In[ ]:


# Format partisan margins into human-readable strings (e.g., Trump+7.89 or Harris+4.12)
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


# In[ ]:


# Compute continuous divergent RGB color ramps based on partisan vote margins
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


# In[ ]:


# Filter and aggregate statistics exclusively for targeted or impacted districts
gdf_targeted = gdf[gdf['Targeted'] == True].copy()

# Normalize district identifiers into standard congressional format (e.g., TX34 to TX-34)
def format_district_code(code):
    if not isinstance(code, str) or len(code) < 3:
        return str(code)
    return f"{code[:2]}-{code[2:]}"

# Topline redistricting results
gdf_targeted = gdf[gdf["Targeted"] == True].copy()

favored_dem = int((gdf_targeted["Target_Party"] == "DEM").sum())
favored_rep = int((gdf_targeted["Target_Party"] == "GOP").sum())

harris_new_pct = f"{gdf_targeted['Harris New'].mean() * 100:.1f}%"
trump_new_pct  = f"{gdf_targeted['Trump New'].mean() * 100:.1f}%"
harris_24_pct  = f"{gdf_targeted['Harris 24'].mean() * 100:.1f}%"
trump_24_pct   = f"{gdf_targeted['Trump 24'].mean() * 100:.1f}%"

# Topline related statistics
raw_mean_shift = gdf_targeted['Margin Shift'].abs().mean() * 100
mean_shift = f"{raw_mean_shift:.1f}%"

median_lean = f"{gdf_targeted['Margin New'].abs().median() * 100:.1f}%"

raw_net_shift = gdf_targeted['Margin Shift'].mean() * 100
net_shift = f"{'Harris +' if raw_net_shift > 0 else 'Trump +'}{abs(raw_net_shift):.2f}%"
net_shift_class = "dem" if raw_net_shift > 0 else "rep"

sorted_targeted = gdf_targeted.sort_values(by='Margin New', ascending=True).reset_index(drop=True)
mid_impacted_idx = len(sorted_targeted) // 2
median_impacted_raw = sorted_targeted.loc[mid_impacted_idx, 'District']
median_impacted_dist = format_district_code(median_impacted_raw)

median_impacted_margin_val = sorted_targeted.loc[mid_impacted_idx, 'Margin New'] * 100
median_impacted_class = "dem" if median_impacted_margin_val > 0 else "rep"
median_impacted_lean = f"{'Harris +' if median_impacted_margin_val > 0 else 'Trump +'}{abs(median_impacted_margin_val):.1f}%"
median_impacted_val = f"{median_impacted_dist}, {median_impacted_lean}"

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


# In[ ]:


# Calculate national tipping point seats and congressional generic ballot advantage
house_natl_path = "data/pres2024/house_2024_national.csv"
if not os.path.exists(house_natl_path):
    house_natl_path = "../data/pres2024/house_2024_national.csv"

if os.path.exists(house_natl_path):
    house_natl = pd.read_csv(house_natl_path)
    house_natl = house_natl.merge(gdf[['District', 'Margin New']], on='District', how='left')
    house_natl['Margin_Post'] = house_natl['Margin New'].combine_first(house_natl['Margin_2party'])
    
    sorted_24 = house_natl.sort_values(by='Margin_2party', ascending=False).reset_index(drop=True)
    raw_old_name = sorted_24.loc[217, 'District']
    tipping_old_name = format_district_code(raw_old_name)
    val_24 = sorted_24.loc[217, 'Margin_2party'] * 100
    tipping_old_margin = f"{'D +' if val_24 > 0 else 'R +'}{abs(val_24):.1f}%"
    tipping_old_class = "dem" if val_24 > 0 else "rep"

    sorted_new = house_natl.sort_values(by='Margin_Post', ascending=False).reset_index(drop=True)
    raw_new_name = sorted_new.loc[217, 'District']
    tipping_new_name = format_district_code(raw_new_name)
    val_new = sorted_new.loc[217, 'Margin_Post'] * 100
    tipping_new_margin = f"{'D +' if val_new > 0 else 'R +'}{abs(val_new):.1f}%"
    tipping_new_class = "dem" if val_new > 0 else "rep"

    post_rep_seats = int((house_natl['Margin_Post'] < 0).sum())
    post_dem_seats = int((house_natl['Margin_Post'] > 0).sum())
    total_house_seats = len(house_natl) if len(house_natl) > 0 else 435
    
    mean_national_margin = house_natl['Margin_2party'].mean()
    natl_gop_vote_share = 0.50 - (mean_national_margin / 2.0)
    natl_dem_vote_share = 0.50 + (mean_national_margin / 2.0)
    
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
    tipping_new_name = "CO-08"
    tipping_new_margin = "R +0.8%"
    tipping_new_class = "rep"
    tipping_old_name = "CO-08"
    tipping_old_margin = "R +0.4%"
    tipping_old_class = "rep"
    ballot_adv_display = "R +2.14%"
    ballot_adv_class = "rep"

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


# In[ ]:


# Parse layout component templates and inject dynamic sidebar context data
HEADER_HTML_CONTENT = open('./templates/header.html', encoding='utf-8').read()

with open('./templates/sidebar.html', 'r', encoding='utf-8') as f:
    sidebar_template = f.read()

for key, value in sidebar_context.items():
    sidebar_template = sidebar_template.replace(f"{{{key}}}", str(value))

SIDEBAR_HTML_CONTENT = sidebar_template
FOOTER_HTML_CONTENT = open('./templates/footer.html', encoding='utf-8').read()

LEGEND_BOUNDS = [-0.45, -0.23, -0.01, 0.0, 0.01, 0.23, 0.45]
LEGEND_COLORS = ['#5A0000', '#C82828', '#FF6E6E', '#8C8C8C', '#ADD8E6', '#285AA0', '#050F32']
LEGEND_TICKS  = [-0.40, -0.20, 0.0, 0.20, 0.40]

centroid = gdf.union_all().centroid
center = [centroid.y+3, centroid.x-7]

MAP_OPTIONS = {
    'zoom_start': 5,
    'min_zoom': 5,
    'max_zoom': 8,
    'min_lat': center[0]-25,
    'max_lat': center[0]+25,
    'min_long': center[1]-30,
    'max_long': center[1]+35,
}


# In[ ]:


# Initialize and compile standalone Folium web maps with tile layers and custom UI elements
def compile_map(filename, target_column, tooltip_config, legend_caption):
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
        max_bounds_viscosity=1.0
    )
    m.options['maxZoom'] = MAP_OPTIONS['max_zoom']

    CARTO_KEY = os.getenv("CARTO_API_KEY")

    folium.TileLayer(
        tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{{z}}/{{x}}/{{y}}.png?key={CARTO_KEY}",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>',
        name="Base Map",
        subdomains="abcd",
        control=False,
        min_zoom=MAP_OPTIONS["min_zoom"],
        max_zoom=MAP_OPTIONS["max_zoom"],
    ).add_to(m)

    hatch_pattern = plugins.pattern.StripePattern(
        angle=-45, color='black', space_color='transparent', weight=3, space_weight=5
    ).add_to(m)

    def style_main(feature):
        margin = feature['properties'].get(target_column, 0)
        return {'fillColor': color_scheme(margin), 'color': 'black', 'weight': 1, 'fillOpacity': 0.8}
        
    def style_hatch(feature):
        if feature['properties'].get('Targeted', False):
            return {'fillPattern': hatch_pattern, 'fillOpacity': 0.6, 'color': 'transparent'}
        return {'fillColor': 'transparent', 'color': 'transparent'}

    group = folium.FeatureGroup(name=legend_caption, control=False, show=True).add_to(m)
    folium.GeoJson(gdf, style_function=style_main).add_to(group)
    folium.GeoJson(gdf, style_function=style_hatch, tooltip=tooltip_config).add_to(group)

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

    m.get_root().html.add_child(folium.Element(HEADER_HTML_CONTENT))
    m.get_root().html.add_child(folium.Element(SIDEBAR_HTML_CONTENT))
    m.get_root().html.add_child(folium.Element(FOOTER_HTML_CONTENT))
    
    # Master external assets for deployment to docs/
    m.get_root().header.add_child(folium.Element('<link rel="stylesheet" href="index.css">'))
    m.get_root().html.add_child(folium.Element('<script src="js/main.js"></script>'))
    
    m.save(filename)
    print(f"Successfully compiled: {filename}")

    # Inline style injection specifically for Jupyter notebook iframe rendering
    css_files = [
        "docs/css/map.css",
        "docs/css/header.css",
        "docs/css/sidebar.css",
        "docs/css/legend.css",
        "docs/css/footer.css",
        "docs/css/responsive.css"
    ]
    bundled_css = ""
    for cpath in css_files:
        if os.path.exists(cpath):
            with open(cpath, 'r', encoding='utf-8') as f:
                bundled_css += f.read() + "\n"

    m.get_root().header.add_child(folium.Element(f'<style>{bundled_css}</style>'))

    return m


# In[ ]:


# Configure interactive hover tooltips for the map layers
tooltip_lean = folium.GeoJsonTooltip(
    fields=['District_Hover', 'Margin New Partisan', 'Margin Partisan'], 
    aliases=['District:', 'Pres. Margin (Post-Redistricting):', "Pres. Margin (2024 Boundaries):"],
    style="background-color:rgba(255,255,255,0.95); color:#1a1a1a; font-size:12px; font-weight:bold; border:2px solid #222;",
    localize=True
)

tooltip_shift = folium.GeoJsonTooltip(
    fields=['District_Hover', 'Margin Shift Partisan', 'Margin Partisan'], 
    aliases=['District:', "Shift from 2024 District's Pres. Margin:", "Pres. Margin (2024 Boundaries):"],
    style="background-color:rgba(255,255,255,0.95); color:#1a1a1a; font-size:12px; font-weight:bold; border:2px solid #222; border-radius:4px;",
    localize=True
)


# In[ ]:


# Build and save the main margin lean map interface
compile_map(
    filename="docs/index.html",
    target_column="Margin New",
    tooltip_config=tooltip_lean,
    legend_caption="Harris-Trump Margin (Striped = Targeted District)"
)

# Build and save the margin shift map interface
compile_map(
    filename="docs/shift.html",
    target_column="Margin Shift",
    tooltip_config=tooltip_shift,
    legend_caption="Harris-Trump Margin Shift from 2024 Districts (Striped = Targeted District)"
)

