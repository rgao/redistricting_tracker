#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import glob
import pandas as pd
import geopandas as gpd

# Resolve base data directory whether executed from root or notebooks/
data_dir = "data" if os.path.exists("data") else "../data"

state_files = [
    {"name": "alabama2026.geojson", "postal": "AL"},
    {"name": "california2026.geojson", "postal": "CA"},
    {"name": "florida2026.geojson", "postal": "FL"},
    {"name": "louisiana2026.geojson", "postal": "LA"},
    {"name": "northcarolina2026.geojson", "postal": "NC"},
    {"name": "ohio2026.geojson", "postal": "OH"},
    {"name": "tennessee2026.geojson", "postal": "TN"},
    {"name": "texas2026.geojson", "postal": "TX"},
    {"name": "utah2026.geojson", "postal": "UT"},
]

TARGET_CRS = "EPSG:4326"
all_gdfs = []

# Standardize projections and district ID format
for item in state_files:
    file_path = os.path.join(data_dir, item["name"])
    gdf = gpd.read_file(file_path)

    if gdf.crs != TARGET_CRS:
        gdf = gdf.to_crs(TARGET_CRS)

    gdf["District"] = item["postal"] + gdf["id"].astype(str).str.zfill(2)

    gdf = gdf[[
        "id", "District", "DemPct", "RepPct", "WhitePct", "MinorityPct", 
        "BlackPct", "HispanicPct", "AsianPct", "Margin", "geometry"
    ]]

    all_gdfs.append(gdf)

states_gdf = pd.concat(all_gdfs, ignore_index=True)
states_gdf.head(8)


# In[2]:


# Load 2024 presidential totals from old boundaries
pres24_path = os.path.join(data_dir, "pres2024", "2024_pres.csv")
pres24 = pd.read_csv(pres24_path)[['District', 'Harris', 'Trump 24', 'Total']]

merged_gdf = states_gdf.merge(pres24, on='District', how='inner')
merged_gdf.head(8)


# In[3]:


# Rename columns to standard analytical schema
gdf_clean = merged_gdf.rename(columns={
    'id': 'District No.',
    'DemPct': 'Harris New',
    'RepPct': 'Trump New',
    'Margin': 'Partisan Index',
    'Harris': 'Harris 24 Raw',
    'Trump 24': 'Trump 24 Raw',
    'Total': 'Total 24 Raw'
})

gdf_clean['Harris 24'] = gdf_clean['Harris 24 Raw'] / gdf_clean['Total 24 Raw']
gdf_clean['Trump 24'] = gdf_clean['Trump 24 Raw'] / gdf_clean['Total 24 Raw']

gdf_clean['Margin 24'] = gdf_clean['Harris 24'] - gdf_clean['Trump 24']
gdf_clean['Margin New'] = gdf_clean['Harris New'] - gdf_clean['Trump New']
gdf_clean['Margin Shift'] = gdf_clean['Margin New'] - gdf_clean['Margin 24']

# Remove rounding noise (< 0.10% shift)
gdf_clean.loc[gdf_clean['Margin Shift'].abs() < 0.001, 'Margin Shift'] = 0.0


# In[4]:


# Ingest re-tabulated 2020 presidential returns for redrawn maps
pres20_dir = os.path.join(data_dir, "pres2020")
csv_2020_files = glob.glob(os.path.join(pres20_dir, "*2020.csv"))

pres_2020_records = []

for filepath in csv_2020_files:
    state_abbr = os.path.basename(filepath)[:2].upper()
    df_st = pd.read_csv(filepath)

    dist_col = [c for c in df_st.columns if 'district' in c.lower() or c.lower() == 'id'][0]
    dem_col = [c for c in df_st.columns if any(k in c.lower() for k in ['dem', 'biden', 'd_'])][0]
    gop_col = [c for c in df_st.columns if any(k in c.lower() for k in ['rep', 'gop', 'trump', 'r_'])][0]

    for _, row in df_st.iterrows():
        raw_dist = str(row[dist_col]).strip()
        dist_num = ''.join(filter(str.isdigit, raw_dist))
        district_id = f"{state_abbr}{int(dist_num):02d}" if dist_num else f"{state_abbr}01"

        dem_val = float(row[dem_col])
        gop_val = float(row[gop_col])

        if dem_val > 1.0 or gop_val > 1.0:
            total_2party = dem_val + gop_val
            margin_2020 = (dem_val - gop_val) / total_2party if total_2party > 0 else 0.0
            dem_pct_2020 = dem_val / total_2party if total_2party > 0 else 0.0
        else:
            margin_2020 = dem_val - gop_val
            dem_pct_2020 = dem_val

        pres_2020_records.append({
            "District": district_id,
            "Biden 20": dem_pct_2020,
            "Trump 20": 1.0 - dem_pct_2020,
            "Margin 20": margin_2020
        })

df_pres_2020 = pd.DataFrame(pres_2020_records)
gdf_clean = gdf_clean.merge(df_pres_2020[['District', 'Margin 20']], on='District', how='left')

# Fall back to 2024 margin if earlier election data is unavailable
gdf_clean['Margin 20'] = gdf_clean['Margin 20'].fillna(gdf_clean['Margin New'])
gdf_clean.head()


# In[5]:


# Load 2024 House summary attributes
house_path = os.path.join(data_dir, "pres2024", "house_2024_summary.csv")

if os.path.exists(house_path):
    house_df = pd.read_csv(house_path)

    state_lookup = {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
        'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
        'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
        'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
        'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
        'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
        'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
        'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
        'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
        'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'
    }

    if 'District_Hover' not in house_df.columns or 'District_Name' not in house_df.columns:
        def make_names(row):
            code = str(row['District']).strip().upper()
            st_abbr = code[:2]
            st_name = state_lookup.get(st_abbr, st_abbr)
            try:
                num = int(code[2:])
            except ValueError:
                num = 1

            if num == 0:
                short = f"{st_name} At-Large"
                full = f"{st_name} At-Large District"
            else:
                j, k = num % 10, num % 100
                suf = "st" if (j == 1 and k != 11) else ("nd" if (j == 2 and k != 12) else ("rd" if (j == 3 and k != 13) else "th"))
                short = f"{st_name} {num}{suf}"
                full = f"{st_name} {num}{suf} District"

            rtype = str(row.get('House_Race_Type', '')).lower()
            is_non_std = (rtype != '') and not ('standard' in rtype and 'non-standard' not in rtype)
            star = " *" if is_non_std else ""
            return pd.Series([short + star, full + star], index=['District_Hover', 'District_Name'])

        house_df[['District_Hover', 'District_Name']] = house_df.apply(make_names, axis=1)

    merge_cols = [c for c in [
        'District', 'House_Winner', 'Current_Rep', 'House_Party', 'House_MOV_Raw', 
        'House_Race_Type', 'Effective_House_Margin', 'District_Hover', 'District_Name'
    ] if c in house_df.columns]

    gdf_clean = gdf_clean.merge(house_df[merge_cols], on='District', how='left')

# National presidential vote
NATL_MARGIN_2020 = 0.0445
NATL_MARGIN_2024 = -0.0147

# Partisan Lean Index: 70% 2024 + 30% 2020, normalized against national vote
gdf_clean['Partisan Index'] = (
    0.70 * (gdf_clean['Margin New'] - NATL_MARGIN_2024) +
    0.30 * (gdf_clean['Margin 20'] - NATL_MARGIN_2020)
)

# Format partisan lean index
def format_lean_number(val):
    if pd.isna(val) or abs(val) < 0.0005:
        return "EVEN"
    num = abs(val) * 100
    return f"D +{num:.1f}" if val > 0 else f"R +{num:.1f}"

gdf_clean['Partisan_Lean_Index'] = gdf_clean['Partisan Index'].apply(format_lean_number)

gdf_clean['Partisan_Lean_Index'] = gdf_clean['Partisan Index'].apply(format_lean_number)
gdf_clean.head()


# In[6]:


# Flag targeted flip seats
gdf_clean["Targeted"] = (gdf_clean["Margin New"] * gdf_clean["Margin 24"]) < 0
gdf_clean["Targeted"] = gdf_clean["Targeted"].astype(bool)

# Specific manual overrides for targeted seats
targeted_removals = ["CA09", "CA13", "FL13"]
gdf_clean.loc[gdf_clean["District"].isin(targeted_removals), "Targeted"] = False

targeted_additions = ["NC01", "OH09", "TX28", "TX34", "CA22"]
gdf_clean.loc[gdf_clean["District"].isin(targeted_additions), "Targeted"] = True

gdf_clean["Target_Party"] = None
mask_targeted = gdf_clean["Targeted"] == True
gdf_clean.loc[mask_targeted, "Target_Party"] = gdf_clean.loc[mask_targeted, "Margin Shift"].apply(
    lambda s: "DEM" if s > 0 else "GOP"
)
gdf_clean.loc[gdf_clean["District"] == "CA22", "Target_Party"] = "DEM"

# =========================================================================
# SYSTEMATIC DILUTED / DONOR SEAT FLAG (FILTERING OUT NOISE)
# =========================================================================
# Rules:
# 1. Must shift > 0.5% towards opposition:
#    - For CA (Dem map): Margin Shift < -0.005 (shifting rightward)
#    - For GOP states: Margin Shift > +0.005 (shifting leftward)
# 2. Must be genuinely exposed: Absolute Partisan Index < 20.0% (|Partisan Index| < 0.20)
# 3. Exclude targeted flip seats
gdf_clean["State_Postal"] = gdf_clean["District"].str[:2].str.upper()

cond_ca_diluted = (
    (gdf_clean["State_Postal"] == "CA") & 
    (gdf_clean["Margin Shift"] < -0.005) & 
    (gdf_clean["Partisan Index"].abs() < 0.20)
)

cond_gop_diluted = (
    (gdf_clean["State_Postal"] != "CA") & 
    (gdf_clean["Margin Shift"] > 0.005) & 
    (gdf_clean["Partisan Index"].abs() < 0.20)
)

gdf_clean["Diluted"] = cond_ca_diluted | cond_gop_diluted
gdf_clean.loc[gdf_clean["Targeted"] == True, "Diluted"] = False

# Open seat / Retirement tracking
retiring_districts = ["CA11", "CA26", "CA48", "FL11", "FL22", "FL16", "FL24", "NC11", "TN09", "TX10", "TX22", "TX33", "TX37"]
gdf_clean["Incumbent_Running"] = ~gdf_clean["District"].isin(retiring_districts)

# Reassign FL-25 incumbent and clarify FL-22 open status
gdf_clean.loc[gdf_clean["District"] == "FL25", "Current_Rep"] = "Jared Moskowitz"
gdf_clean.loc[gdf_clean["District"] == "FL25", "House_Winner"] = "Jared Moskowitz"
gdf_clean.loc[gdf_clean["District"] == "FL25", "House_Party"] = "DEM"
gdf_clean.loc[gdf_clean["District"] == "FL22", "Current_Rep"] = "Open Seat (Frankel in FL-23)"

reordered_columns = [
    "District No.", "District", "District_Hover", "District_Name", "WhitePct", 
    "MinorityPct", "BlackPct", "HispanicPct", "AsianPct", "Partisan_Lean_Index", 
    "House_Winner", "Current_Rep", "House_Party", "House_MOV_Raw", "House_Race_Type", 
    "Harris New", "Trump New", "Margin New", "Margin Shift", "Partisan Index", 
    "Harris 24", "Trump 24", "Margin 24", "Targeted", "Diluted", "Incumbent_Running", 
    "Target_Party", "geometry"
]

export_columns = [col for col in reordered_columns if col in gdf_clean.columns]
gdf_clean = gdf_clean[export_columns]

export_path = "docs/map2026.geojson" if os.path.exists("docs") else "../docs/map2026.geojson"
gdf_clean.to_file(export_path, driver="GeoJSON")
print(f"Exported clean GeoJSON with filtered Diluted flags to {export_path}")


# In[7]:


# # Generate clean, accurately proportioned SVG path strings from the Census shapefile
# import json
# import matplotlib.pyplot as plt
# from shapely.affinity import translate, scale
# from matplotlib.patches import Circle

# data_dir = "data" if os.path.exists("data") else "../data"
# shp_matches = glob.glob(os.path.join(data_dir, "cb_*", "*.shp"))
# if not shp_matches:
#     shp_matches = glob.glob("data/cb_*/*.shp") or glob.glob("../data/cb_*/*.shp")

# states_raw = gpd.read_file(shp_matches[0]).to_crs("EPSG:9311")

# image_output_dir = os.path.join("docs", "images")
# if not os.path.exists("docs") and os.path.exists("../docs"):
#     image_output_dir = os.path.join("../docs", "images")
# os.makedirs(image_output_dir, exist_ok=True)

# # 2. Export party-colored state shapes for Chart 2 (CA = Blue, others = Red)
# state_parties = {
#     "CA": "#2563eb",  # Democratic (Blue)
#     "TX": "#dc2626",  # Republican (Red)
#     "FL": "#dc2626",  # Republican (Red)
#     "OH": "#dc2626",  # Republican (Red)
#     "NC": "#dc2626",  # Republican (Red)
#     "TN": "#dc2626",  # Republican (Red)
#     "AL": "#dc2626",  # Republican (Red)
#     "LA": "#dc2626"   # Republican (Red)
# }

# for abbr, color in state_parties.items():
#     match_row = states_raw[states_raw["STUSPS"] == abbr]
#     if match_row.empty:
#         continue

#     fig, ax = plt.subplots(figsize=(3, 3))
#     match_row.plot(ax=ax, color=color, edgecolor="#0f172a", linewidth=2.0)
#     ax.set_axis_off()
#     plt.tight_layout()

#     out_img_path = os.path.join(image_output_dir, f"{abbr}_shape.png")
#     plt.savefig(out_img_path, dpi=300, transparent=True, bbox_inches='tight')
#     plt.close(fig)
#     print(f"Exported party-colored state shape: {out_img_path}")


# In[8]:


# Generate favicon
# from matplotlib.patches import Circle
# from PIL import Image

# data_dir = "data" if os.path.exists("data") else "../data"
# shp_matches = glob.glob(os.path.join(data_dir, "cb_*", "*.shp"))
# if not shp_matches:
#     shp_matches = glob.glob("data/cb_*/*.shp") or glob.glob("../data/cb_*/*.shp")

# states_raw = gpd.read_file(shp_matches[0]).to_crs("EPSG:9311")

# # 2. Setup output directories
# docs_dir = "docs" if os.path.exists("docs") else "../docs"
# image_output_dir = os.path.join(docs_dir, "images")
# os.makedirs(image_output_dir, exist_ok=True)
# os.makedirs(docs_dir, exist_ok=True)

# # 3. Grab original Texas geometry and its fixed bounds
# tx_geom = states_raw.loc[states_raw["STUSPS"] == "TX", "geometry"].values[0]
# minx, miny, maxx, maxy = tx_geom.bounds

# # Scale down by 0.8 around its centroid for balanced padding inside the circle
# tx_scaled = scale(tx_geom, xfact=0.8, yfact=0.8, origin='centroid')
# tx_row = gpd.GeoDataFrame(geometry=[tx_scaled], crs=states_raw.crs)

# # 4. Plot inside a fixed-limit canvas so scaling shrinks the visual shape cleanly
# fig, ax = plt.subplots(figsize=(2, 2), subplot_kw={'aspect': 'equal'})

# # Lock data limits to the unscaled Texas bounding box to prevent auto-zooming
# ax.set_xlim(minx, maxx)
# ax.set_ylim(miny, maxy)

# # Draw circular badge
# circ = Circle((0.5, 0.5), 0.48, transform=ax.transAxes, facecolor="#ffffff", edgecolor="#2563eb", linewidth=5)
# ax.add_patch(circ)

# # Plot scaled Texas shape
# tx_row.plot(ax=ax, color="#dc2626", edgecolor="#0f172a", linewidth=1.2)
# ax.set_axis_off()
# plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

# # 5. Save to a temporary PNG inside docs/images/
# temp_png = os.path.join(image_output_dir, "temp_favicon.png")
# plt.savefig(temp_png, dpi=300, transparent=True, bbox_inches='tight', pad_inches=0)
# plt.close(fig)

# # 6. Convert and export as a true multi-resolution .ico file directly to docs/ root
# img = Image.open(temp_png).convert("RGBA")
# root_ico_path = os.path.join(docs_dir, "favicon.ico")

# img.save(root_ico_path, format="ICO", sizes=[(32, 32), (64, 64)])

# print("Successfully generated and exported Favicon")

