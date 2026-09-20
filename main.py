#!/usr/bin/env python
# coding: utf-8

# In[48]:


import geopandas as gpd
import folium
from folium import plugins
import branca

gdf = gpd.read_file("data/map2026.geojson")
# Check for EPSG 4326 for folium compatibility
print(gdf.crs)
gdf.head()


# In[49]:


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


# In[50]:


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


# In[51]:


# Sidebar default value calculations
favored_dem = int((gdf['Margin New'] > 0).sum())
favored_rep = int((gdf['Margin New'] < 0).sum())

mean_shift = f"{gdf['Margin Shift'].abs().mean() * 100:.1f}%"
mean_lean  = f"{gdf['Margin New'].abs().mean() * 100:.1f}%"

harris_new_pct = f"{gdf['Harris New'].mean() * 100:.1f}%"
trump_new_pct  = f"{gdf['Trump New'].mean() * 100:.1f}%"
harris_24_pct  = f"{gdf['Harris 24'].mean() * 100:.1f}%"
trump_24_pct   = f"{gdf['Trump 24'].mean() * 100:.1f}%"

median_margin = gdf['Margin New'].median()
mean_margin   = gdf['Margin New'].mean()
bias_val      = (median_margin - mean_margin) * 100
gop_bias      = f"{'R +' if bias_val < 0 else 'D +'}{abs(bias_val):.1f}%"

# Tipping Point District Calculation
sorted_new = gdf.sort_values(by='Margin New', ascending=True).reset_index(drop=True)
mid_new = len(sorted_new) // 2
tipping_new_name = sorted_new.loc[mid_new, 'District']
val_new = sorted_new.loc[mid_new, 'Margin New'] * 100
tipping_new_margin = f"{'Harris +' if val_new > 0 else 'Trump +'}{abs(val_new):.1f}%"

sorted_24 = gdf.sort_values(by='Margin 24', ascending=True).reset_index(drop=True)
mid_24 = len(sorted_24) // 2
tipping_old_name = sorted_24.loc[mid_24, 'District']
val_24 = sorted_24.loc[mid_24, 'Margin 24'] * 100
tipping_old_margin = f"{'Harris +' if val_24 > 0 else 'Trump +'}{abs(val_24):.1f}%"

sidebar_context = {
    "favored_dem": favored_dem,
    "favored_rep": favored_rep,
    "harris_new_pct": harris_new_pct,
    "trump_new_pct": trump_new_pct,
    "harris_24_pct": harris_24_pct,
    "trump_24_pct": trump_24_pct,
    "mean_shift": mean_shift,
    "mean_lean": mean_lean,
    "gop_bias": gop_bias,
    "maj_min_count": 5,
    "tipping_new_name": tipping_new_name,
    "tipping_new_margin": tipping_new_margin,
    "tipping_old_name": tipping_old_name,
    "tipping_old_margin": tipping_old_margin
}


# In[52]:


# Define static assets and variable
# Title card and navigation
HEADER_HTML_CONTENT = open('./components/header.html', encoding='utf-8').read()

# Sidebar
with open('./components/sidebar.html', 'r', encoding='utf-8') as f:
    sidebar_template = f.read()

for key, value in sidebar_context.items():
    sidebar_template = sidebar_template.replace(f"{{{key}}}", str(value))

SIDEBAR_HTML_CONTENT = sidebar_template

# Footer / copyright
FOOTER_HTML_CONTENT = open('./components/footer.html', encoding='utf-8').read()

# Scripts and styling
with open('./docs/static/style.css', 'r', encoding='utf-8') as f:
    css = f.read()
with open('./docs/static/scripts.js', 'r', encoding='utf-8') as f:
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

    # Map geometry
    folium.TileLayer(
        tiles="cartodbpositron", 
        name="Base Map", 
        control=False, 
        min_zoom=MAP_OPTIONS['min_zoom'], 
        max_zoom=MAP_OPTIONS['max_zoom'],
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

    # Top layer: city labels
    folium.map.CustomPane("labels_top", z_index=450).add_to(m)
    folium.TileLayer(
        tiles="cartodbpositrononlylabels", 
        pane="labels_top", 
        control=False, 
        min_zoom=MAP_OPTIONS['min_zoom'], 
        max_zoom=MAP_OPTIONS['max_zoom']
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


# In[53]:


# Tooltips on hover
tooltip_lean = folium.GeoJsonTooltip(
    fields=['District No.', 'Margin New Partisan'], 
    aliases=['2026 District No.:', '2024 Presidential Margin:'],
    style="background-color:rgba(255,255,255,0.95); color:#1a1a1a; font-size:12px; font-weight:bold; border:2px solid #222;",
    localize=True
)

tooltip_shift = folium.GeoJsonTooltip(
    fields=['District No.', 'Margin Shift Partisan', 'Margin Partisan'], 
    aliases=['2026 District No.:', "Shift from 2024 District's Margin:", "Old District's 2024 Margin:"],
    style="background-color:rgba(255,255,255,0.95); color:#1a1a1a; font-size:12px; font-weight:bold; border:2px solid #222; border-radius:4px;",
    localize=True
)


# In[54]:


# Compile margin lean map
compile_map(
    filename="docs/index.html",
    target_column="Margin New",
    tooltip_config=tooltip_lean,
    legend_caption="Harris-Trump Margin (Striped = Targeted District)"
)


# In[55]:


# Compile margin shift map
compile_map(
    filename="docs/shift.html",
    target_column="Margin Shift",
    tooltip_config=tooltip_shift,
    legend_caption="Harris-Trump Margin Shift from 2024 Districts (Striped = Targeted District)"
)

