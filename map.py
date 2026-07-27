#!/usr/bin/env python
# coding: utf-8

# In[63]:


import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import folium
from folium import plugins
from folium.elements import MacroElement
import branca.colormap as cm
from branca.element import Element

gdf = gpd.read_file("data/map2026.geojson")

# Check for EPSG 4326 for folium compatibility
print(gdf.crs)
gdf.head(8)


# In[64]:


# Finding map center
centroid = gdf.unary_union.centroid
center = [centroid.y, centroid.x]

# Initiate folium map. Tilelayer is initiated separately to prevent it as a toggle option
m = folium.Map(
    location=center, 
    zoom_start=5, 
    tiles=None,
    min_zoom=5,
    max_zoom=8,
)

m.options['maxZoom'] = 8

# Base map layer
folium.TileLayer(
    tiles="cartodbpositron", 
    name="Base Map", 
    control=False,
    min_zoom=5,
    max_zoom=8
).add_to(m)


# In[65]:


# Define styling for targeted districts
hatch_pattern = plugins.pattern.StripePattern(
    angle=-45,
    color='black',
    space_color='transparent',
    weight=3,
    space_weight=5
).add_to(m)

# Define function for hatch styling to avoid browser ordering issues when rendering
def style_hatch(feature):
    targeted = feature['properties'].get('Targeted', False)
    if targeted:
        return {'fillPattern': hatch_pattern, 'fillOpacity': 0.6, 'color': 'transparent'}
    return {'fillColor': 'transparent', 'color': 'transparent'}


# In[66]:


# Color scheme function for both maps to show margin lean and shift
def color_scheme(margin):
    """
    Maps political margins with linear gradients
    - Exactly 0: Gray
    - 0% to  1%: Gray to LightBlue
    - 1% to 23%: LightBlue to Steel Blue
    - 23% to 45%: Steel Blue to Midnight Blue (caps past 45%)
    
    - 0% to -1%: Gray to Salmon
    - -1% to -23%: Salmon to Soft Crimson Red
    - -23% to -45%: Soft Crimson Red to Deep Maroon (caps past -45%)
    """
    COLOR_MIDPOINT   = (140, 140, 140)  # Gray
    
    # Color gradient within 1% to highlight partisan lean/shift tilts
    COLOR_RED_START  = (255, 165, 165)  # Light Salmon
    COLOR_BLUE_START = (173, 216, 230)  # Light Blue
    
    # Color gradient midpoints at +-23%
    COLOR_RED_MID    = (200,  40,  40)  # Soft Crimson Red 
    COLOR_BLUE_MID   = ( 40,  90, 160)  # Steel Blue 
    
    # Color gradient caps at +-45%
    COLOR_DARKRED    = ( 90,   0,   0)  # Deep Maroon 
    COLOR_NAVYBLUE   = (  5,  15,  50)  # Midnight Blue

    def interpolate(val, min_val, max_val, color_start, color_end):
        """Calculates a smooth fractional shift between two color points."""
        fraction = (val - min_val) / (max_val - min_val)
        fraction = max(0.0, min(1.0, fraction)) # Bounds check safety clamp
        
        r = int(color_start[0] + (color_end[0] - color_start[0]) * fraction)
        g = int(color_start[1] + (color_end[1] - color_start[1]) * fraction)
        b = int(color_start[2] + (color_end[2] - color_start[2]) * fraction)
        return f"rgb({r},{g},{b})"

    # Neutral
    if abs(margin) < 0.0005:
        return f"rgb({COLOR_MIDPOINT[0]},{COLOR_MIDPOINT[1]},{COLOR_MIDPOINT[2]})"

    # Democratic margins
    elif margin >= 0.0005:
        if margin <= 0.01:
            return interpolate(margin, 0.00, 0.01, COLOR_MIDPOINT, COLOR_BLUE_START)
        elif margin <= 0.23:
            return interpolate(margin, 0.01, 0.23, COLOR_BLUE_START, COLOR_BLUE_MID)
        else:
            return interpolate(margin, 0.23, 0.45, COLOR_BLUE_MID, COLOR_NAVYBLUE)

    # Republican margins
    else:
        if margin >= -0.01:
            return interpolate(margin, 0.00, -0.01, COLOR_MIDPOINT, COLOR_RED_START)
        elif margin >= -0.23:
            return interpolate(margin, -0.01, -0.23, COLOR_RED_START, COLOR_RED_MID)
        else:
            return interpolate(margin, -0.23, -0.45, COLOR_RED_MID, COLOR_DARKRED)


# In[67]:


# Create new columns that shows partisan lean (e.g. D+7.89) for visualization tooltips
def partisan_text(val):
    if val is None or str(val).strip() in ['', 'nan', 'None']:
        return "EVEN"
        
    try:
        num = val * 100
        
        if abs(num) < .01:
            return "EVEN"
        
        elif num < 0:
            return f"Trump+{abs(num):.2f}"
            
        elif num > 0:
            return f"Harris+{num:.2f}"
            
        return "EVEN"
    except ValueError:
        return str(val)

gdf['Margin Partisan'] = gdf['Margin 24'].apply(partisan_text)
gdf['Margin New Partisan'] = gdf['Margin New'].apply(partisan_text)
gdf['Margin Shift Partisan'] = gdf['Margin Shift'].apply(partisan_text)

gdf.head(8)


# In[68]:


# Styling function for margin lean map
def style_left(feature):
    margin = feature['properties'].get('Margin New', 0)
        
    style_dict = {
        'fillColor': color_scheme(margin),
        'color': 'black',   
        'weight': 1,
        'fillOpacity': 0.8
    }
        
    return style_dict

# Styling function for margin shift map
def style_right(feature):
    margin = feature['properties'].get('Margin Shift', 0)

    style_dict = {
        'fillColor': color_scheme(margin),
        'color': 'black',   
        'weight': 1,
        'fillOpacity': 0.8
    }
        
    return style_dict


# In[69]:


# Tooltip styling
tooltip_left = folium.GeoJsonTooltip(
    fields=['District No.', 'Margin New Partisan'], 
    aliases=['New District:', '2024 Presidential Margin:'],
    style=(
        "background-color: rgba(255, 255, 255, 0.95); "  
        "color: #1a1a1a; "                               
        "font-size: 12px; "                              
        "font-weight: bold; "
        "border: 2px solid #222222; "                    
        "box-shadow: 3px 3px 10px rgba(0,0,0,0.25);"     
    ),
    localize=True
)

tooltip_right = folium.GeoJsonTooltip(
    fields=['District No.', 'Margin Shift Partisan', 'Margin Partisan'], 
    aliases=['New District:', "Shift from 2024 District's Margin:", "Old District's 2024 Margin:"],
    style=(
        "background-color: rgba(255, 255, 255, 0.95); "
        "color: #1a1a1a; "
        "font-size: 12px; "
        "font-weight: bold; "
        "border: 2px solid #222222; "
        "border-radius: 4px; "
        "box-shadow: 3px 3px 10px rgba(0,0,0,0.25);"
    ),
    localize=True
)


# In[70]:


# Create a feature group for each map to be toggled
group_lean = folium.FeatureGroup(name="Margin LEAN of 2026 Districts", overlay=False, show=True).add_to(m)
group_shift = folium.FeatureGroup(name="Margin SHIFT from 2024 Districts", overlay=False, show=False).add_to(m)

# Bind data to their respective feature groups
folium.GeoJson(
    gdf,
    style_function=style_left,
).add_to(group_lean)

folium.GeoJson(
    gdf,
    style_function=style_hatch,
    tooltip=tooltip_left
).add_to(group_lean)

folium.GeoJson(
    gdf,
    style_function=style_right,
).add_to(group_shift)

folium.GeoJson(
    gdf,
    style_function=style_hatch,
    tooltip=tooltip_right
).add_to(group_shift)


# In[71]:


# Add a custom city label layer on top of the maps
pane_labels = folium.map.CustomPane("labels_top", z_index=450).add_to(m)

folium.TileLayer(
    tiles="cartodbpositrononlylabels", 
    pane="labels_top", 
    name="City Labels",
    control=False,
    min_zoom=5,
    max_zoom=8
).add_to(m)

# Toggle box
folium.LayerControl(position='topleft', collapsed=False).add_to(m)


# In[72]:


# Indicate gradient breakpoints for the legend
legend_bounds = [-0.45, -0.23, -0.01, 0.0, 0.01, 0.23, 0.45]

legend_colors = [
    '#5A0000',  # -45% Deep Maroon
    '#C82828',  # -23% Soft Crimson Red
    '#FF6E6E',  # -1%  Salmon
    '#8C8C8C',  #  0%  Gray
    '#ADD8E6',  #  +1% LightBlue
    '#285AA0',  # +23% Steel Blue
    '#050F32'   # +45% Midnight Blue
]

# Initiate a legend using linear gradients
legend = cm.LinearColormap(
    colors=legend_colors,
    index=legend_bounds,
    vmin=min(legend_bounds),
    vmax=max(legend_bounds),
    caption="Harris-Trump Margin / Margin Shift (Striped = Redistricted to Flip)"
)

legend.tick_labels = [-0.40, -0.20, 0.0, 0.20, 0.40]
legend.width = 650
legend.height = 45

# Append layout node to the final folium canvas map object instance
m.add_child(legend);


# In[73]:


Read and drop the HTML header layout into the document body
m.get_root().html.add_child(folium.Element(open('./header.html', encoding='utf-8').read()))
m.get_root().header.add_child(folium.CssLink('./style.css'))
m.get_root().html.add_child(folium.JavascriptLink('./scripts.js'))

m.save("index.html")
m

