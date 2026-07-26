#!/usr/bin/env python
# coding: utf-8

# In[37]:


import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import folium
from folium import plugins
from folium.elements import MacroElement
import branca.colormap as cm
from branca.element import Element
# import streamlit as st
# from streamlit_folium import st_folium

gdf = gpd.read_file("data/map2026.geojson")

# Check for EPSG 4326 for folium compatibility
print(gdf.crs)
gdf.head(8)


# In[38]:


# Test data visualization with matplotlib
# Plot 2024 Pres. margin and shift under new maps 
# fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

# gdf.plot(
#     column='Margin New', 
#     cmap='RdBu',
#     vmin=-0.5,
#     vmax=0.5,
#     legend=True,              
#     legend_kwds={'label': 'Harris-Trump % Margin',
#                  'orientation': 'horizontal',
#                  'shrink': 0.7,
#                  'pad': 0.05},
#     edgecolor='black',        
#     ax=ax1
# )

# ax1.axis('off')
# ax1.set_title(
#     "2024 Pres. Margin Under New Boundaries", 
#     fontsize=16, 
#     fontweight='bold'
# )

# Change legend markers to percentage
# fig.axes[2].xaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))

# gdf.plot(
#     column='Margin Shift',      
#     cmap='RdBu',
#     vmin=-0.5,
#     vmax=0.5,
#     legend=True,              
#     legend_kwds={'label': 'Harris-Trump % Margin',
#                  'orientation': 'horizontal',
#                  'shrink': 0.7,
#                  'pad': 0.05},
#     edgecolor='black',        
#     ax=ax2
# )

# ax2.axis('off')
# ax2.set_title(
#     "2024 Pres. Margin Shift from Old Boundaries",
#     fontsize=16,
#     fontweight='bold'
# ) 

# fig.axes[3].xaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))

# plt.tight_layout()
# plt.show()


# In[39]:


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


# In[40]:


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


# In[41]:


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


# In[42]:


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


# In[43]:


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

# Make the 3rd field in the shift map tooltip normal font to indicate less importance
normal_font = """
<style>
.leaflet-tooltip tr:nth-child(3) th,
.leaflet-tooltip tr:nth-child(3) td {
    font-weight: normal !important;
}
</style>
"""

# Append the above font rule to the map head layout
m.get_root().header.add_child(folium.Element(normal_font))


# In[44]:


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


# In[45]:


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


# In[46]:


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

# Tailored legend layout overrides matching your light title card theme
legend_css = """
<style>
    /* Absolute layout tracking for the floating container block */
    .legend {
        position: fixed !important;
        bottom: 20px !important;
        left: 20px !important;
        z-index: 9999 !important;
        background-color: rgba(255, 255, 255, 0.95) !important;        
        border: 2px solid #222222 !important;       
        border-radius: 6px !important;              
        padding: 12px 14px !important;
        box-shadow: 3px 3px 12px rgba(0,0,0,0.15);
    }
    
    .legend svg {
        height: 55px !important; 
        overflow: visible !important;
    }
    
    .legend .caption {
        color: #1a1a1a !important;                  
        font-size: 13px !important;
        font-weight: bold !important;
        transform: translateY(10px);
        font-family: 'Helvetica Neue', Arial, sans-serif !important;
    }
    
    .legend text {
        fill: #1a1a1a !important;                   
        font-size: 10px !important;
        font-weight: bold !important;
        font-family: 'Helvetica Neue', Arial, sans-serif !important;
    }
</style>
"""
m.get_root().header.add_child(folium.Element(legend_css))

# Re-engineered JavaScript formatter mapping labels to your 7 new threshold markers
percentage_formatter_js = """
<script>
document.addEventListener("DOMContentLoaded", function() {
    var checkTicksInterval = setInterval(function() {
        var ticks = document.querySelectorAll('div.legend g.tick text');
        
        // Check if graphics have loaded
        if (ticks.length > 0) {
            clearInterval(checkTicksInterval);
            
            // Explicitly map string representation arrays sequentially to match index stops
            var customLabels = ['-40%', '-20%', '0%', '+20%', '+40%'];
            
            for (var i = 0; i < ticks.length; i++) {
                if (i < customLabels.length) {
                    ticks[i].textContent = customLabels[i];
                }
            }
        }
    }, 100);
});
</script>
"""
m.get_root().html.add_child(folium.Element(percentage_formatter_js))

# Append layout node to the final folium canvas map object instance
m.add_child(legend)


# In[47]:


# JS and CSS injection for header, including title and toggle box
unified_header_html = """
<div id="header-wrapper">
    <div class="title-card">
        <h1 style="margin: 0; font-size: 20px; font-weight: bold;">
            Mid-Decade Redistricting Visualized
        </h1>
        <p style="margin: 3px 0 0 0; font-size: 12px; font-weight: bold;">
            Partisan Lean and Shift of New Districts based on the 2024 Presidential Margin
        </p>
    </div>
    
    <!-- Empty anchor destination where our CSS will inject and position the native toggle box -->
    <div id="toggle-anchor-zone"></div>
</div>

<style>
    /* Master Flex wrapper to structurally stack components without fixed overlapping gaps */
    #header-wrapper {
        position: fixed;
        top: 15px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;               
        width: 90%;             
        max-width: 650px;
        pointer-events: none;    /* Allows dragging map through empty gap spaces */
    }
    
    .title-card {
        pointer-events: auto;    /* Enables interaction over text fields */
        /* The 4th value is opacity */
        background: linear-gradient(
            to right, 
            rgba(240, 128, 128, 0.85), 
            rgba(245, 245, 245, 0.85), 
            rgba(135, 206, 250, 0.85)  
        );
        color: #1a1a1a; 
        border: 2px solid #222222;
        border-radius: 6px;
        padding: 10px 20px;
        box-shadow: 3px 3px 12px rgba(0,0,0,0.15);
        text-align: center;
        font-family: 'Helvetica Neue', Arial, sans-serif;
        width: 80%;
        box-sizing: border-box;
    }
    
    .leaflet-top.leaflet-left {
        display: block !important; 
    }
    
    .leaflet-control-layers {
        pointer-events: auto;
        position: static !important; /* Strips original fixed overlay behaviors */
        margin: 0 auto !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
        border: 2px solid #222222 !important;
        border-radius: 6px !important;
        box-shadow: 3px 3px 12px rgba(0,0,0,0.15) !important;
        padding: 6px 12px !important;
        font-family: 'Helvetica Neue', Arial, sans-serif !important;
        display: inline-block !important;
    }
    
    /* Change toggles from vertical to horizontal list */
    .leaflet-control-layers-list,
    .leaflet-control-layers-base {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 16px !important;
        flex-wrap: wrap !important; /* Wraps items cleanly on extra small screens */
    }
    
    .leaflet-control-layers-base label {
        display: flex !important;
        align-items: center !important;
        gap: 6px !important;
        margin: 0 !important;
        font-size: 13px !important;
        font-weight: bold !important;
        color: #1a1a1a !important;
        cursor: pointer !important;
        white-space: nowrap !important; /* Keeps individual labels on a single line */
    }
    
    .leaflet-control-layers-base input[type="radio"] {
        margin: 0 !important;
        cursor: pointer !important;
    }
</style>
"""
m.get_root().html.add_child(folium.Element(unified_header_html))

# Moves the toggle box from its native left-side positioning to within our header container
append_control_js = """
<script>
document.addEventListener("DOMContentLoaded", function() {
    // Checks for element loads every 100ms
    var checkControlInterval = setInterval(function() {
        var nativeControl = document.querySelector('.leaflet-control-layers');
        var targetAnchor = document.getElementById('toggle-anchor-zone');
        
        if (nativeControl && targetAnchor) {
            // If elements have loaded, stop the timer check and reposition the toggle box
            clearInterval(checkControlInterval);
            targetAnchor.appendChild(nativeControl);
        }
    }, 100);
});
</script>
"""
m.get_root().html.add_child(folium.Element(append_control_js))

# Initiate the toggle box
folium.LayerControl(position='topleft', collapsed=False).add_to(m)

m.save("index.html")
m

