#!/usr/bin/env python
# coding: utf-8

# In[316]:


import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import folium
from folium.plugins import DualMap
from folium.plugins import pattern
from folium.elements import MacroElement
import branca.colormap as cm
from branca.element import Element

gdf = gpd.read_file("data/map2026.geojson")

# Check for EPSG 4326 for folium compatibility
print(gdf.crs)
gdf.head(8)


# In[317]:


# Test data visualization with matplotlib
# Plot 2024 Pres. margin and shift under new maps 
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

gdf.plot(
    column='Margin New', 
    cmap='RdBu',
    vmin=-0.5,
    vmax=0.5,
    legend=True,              
    legend_kwds={'label': 'Harris-Trump % Margin',
                 'orientation': 'horizontal',
                 'shrink': 0.7,
                 'pad': 0.05},
    edgecolor='black',        
    ax=ax1
)

ax1.axis('off')
ax1.set_title(
    "2024 Pres. Margin Under New Boundaries", 
    fontsize=16, 
    fontweight='bold'
)

# Change legend markers to percentage
fig.axes[2].xaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))

gdf.plot(
    column='Margin Shift',      
    cmap='RdBu',
    vmin=-0.5,
    vmax=0.5,
    legend=True,              
    legend_kwds={'label': 'Harris-Trump % Margin',
                 'orientation': 'horizontal',
                 'shrink': 0.7,
                 'pad': 0.05},
    edgecolor='black',        
    ax=ax2
)

ax2.axis('off')
ax2.set_title(
    "2024 Pres. Margin Shift from Old Boundaries",
    fontsize=16,
    fontweight='bold'
) 

fig.axes[3].xaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))

plt.tight_layout()
plt.show()


# In[318]:


# Create new columns that shows partisan lean (e.g. D+7.89) for visualization tooltips
def partisan_text(val):
    if val is None or str(val).strip() in ['', 'nan', 'None']:
        return "EVEN"
        
    try:
        num = val * 100
        
        if num < 0:
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


# In[319]:


# Finding map center
centroid = gdf.unary_union.centroid
center = [centroid.y, centroid.x]

# Initiate dual maps for folium
m = DualMap(location=center, zoom_start=5, tiles="CartoDB positron")

# Set minimum and maximum zoom distance
for sub_map in [m.m1, m.m2]:
    sub_map.options['minZoom'] = 4
    sub_map.options['maxZoom'] = 8


# In[320]:


# Define styling for targeted districts
hatch_pattern = pattern.StripePattern(
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


# In[321]:


# Color scheme for partisan lean of new districts
def style_left(feature):
    margin = feature['properties'].get('Margin New', 0)
    
    if margin >= 0.30:     color = '#084594'  
    elif margin >= 0.15:   color = 'steelblue'  
    elif margin > 0:       color = 'lightblue' 
    elif margin >= -0.15:  color = 'lightcoral' 
    elif margin >= -0.30:  color = 'indianred'  
    else:                  color = 'firebrick' 
        
    style_dict = {
        'fillColor': color,
        'color': 'black',   
        'weight': 1,
        'fillOpacity': 0.8
    }
        
    return style_dict

# Color scheme for partisan shift for new boundaries
def style_right(feature):
    margin = feature['properties'].get('Margin Shift', 0)
    
    if margin >= 0.30:     color = '#084594'  
    elif margin >= 0.15:   color = 'steelblue'  
    elif margin > 0:       color = 'lightblue' 
    elif margin >= -0.15:  color = 'lightcoral' 
    elif margin >= -0.30:  color = 'indianred'  
    else:                  color = 'firebrick' 
        
    style_dict = {
        'fillColor': color,
        'color': 'black',   
        'weight': 1,
        'fillOpacity': 0.8
    }
        
    return style_dict


# In[322]:


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
    aliases=['New District:', "Shift from Old District's Margin:", "Old District's 2024 Margin:"],
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


# In[323]:


# Bind maps and their styling schemes
folium.GeoJson(
    gdf,
    style_function=style_left,
).add_to(m.m1)

folium.GeoJson(
    gdf,
    style_function=style_hatch,
    tooltip=tooltip_left
).add_to(m.m1)

folium.GeoJson(
    gdf,
    style_function=style_right,
).add_to(m.m2)

folium.GeoJson(
    gdf,
    style_function=style_hatch,
    tooltip=tooltip_right
).add_to(m.m2)

# Put city labels on the top layer
pane_left = folium.map.CustomPane("labels_left", z_index=450).add_to(m.m1)
pane_right = folium.map.CustomPane("labels_right", z_index=450).add_to(m.m2)

folium.TileLayer("cartodbpositrononlylabels", pane="labels_left").add_to(m.m1)
folium.TileLayer("cartodbpositrononlylabels", pane="labels_right").add_to(m.m2)


# In[324]:


# Instantiate a legend
bounds = [-0.45, -0.30, -0.15, 0, 0.15, 0.30, 0.45]
colors = ['firebrick', 'indianred', 'lightcoral', 'lightblue', 'steelblue', '#084594']

legend = cm.StepColormap(
    colors=colors,
    index=bounds,
    vmin=min(bounds),
    vmax=max(bounds),
    caption="Harris-Trump Margin / Margin Shift (Striped = Redistricted to Flip)"
)

legend.width = 650
legend.height = 45

# Custom CSS for legend styling
m.get_root().header.add_child(folium.Element("""
<style>
    /* Container */
    .legend {
        background-color: white !important;        
        border: 1px solid #222222 !important;       
        border-radius: 5px !important;              
        padding: 10px !important;
    }
    
    /* Expand the SVG container so elements moving down do not get clipped */
    .legend svg {
        height: 55px !important; /* Increase this if elements still look clipped */
        overflow: visible !important;
    }
    
    /* Title */
    .legend .caption {
        color: black !important;                  
        font-size: 14px !important;
        font-weight: bold;
        transform: translateY(10px);
    }
    
    /* Ticks */
    .legend text {
        fill: black !important;                   
        font-size: 11px !important;
    }
</style>
"""))

# javascript to convert ticks from decimals to percentages
percentage_formatter_js = """
<script>
document.addEventListener("DOMContentLoaded", function() {
    // Array matching your 7 explicit tick bounds sequentially
    var customLabels = ['-45%', '-30%', '-15%', '0%', '+15%', '+30%', '+45%'];
    
    var ticks = document.querySelectorAll('div.legend g.tick text');
    
    // Explicitly overwrite the text of each generated tick position
    for (var i = 0; i < ticks.length; i++) {
        if (i < customLabels.length) {
            ticks[i].textContent = customLabels[i];
        }
    }
});
</script>
"""
m.get_root().html.add_child(folium.Element(percentage_formatter_js))

# The semicolon prevents automatic visual rendering; alternatively, assign this to a dummy variable
m.m1.add_child(legend);

m.save("index.html")
m

