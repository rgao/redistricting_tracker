#!/usr/bin/env python
# coding: utf-8

# In[7]:


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


# In[8]:


# Load 2024 presidential totals from old boundaries
pres24_path = os.path.join(data_dir, "pres2024", "2024_pres.csv")
pres24 = pd.read_csv(pres24_path)[['District', 'Harris', 'Trump 24', 'Total']]

merged_gdf = states_gdf.merge(pres24, on='District', how='inner')
merged_gdf.head(8)


# In[9]:


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

# Calculate two-party presidential vote shares and margin shift
gdf_clean['Harris 24'] = gdf_clean['Harris 24 Raw'] / gdf_clean['Total 24 Raw']
gdf_clean['Trump 24'] = gdf_clean['Trump 24 Raw'] / gdf_clean['Total 24 Raw']

gdf_clean['Margin 24'] = gdf_clean['Harris 24'] - gdf_clean['Trump 24']
gdf_clean['Margin New'] = gdf_clean['Harris New'] - gdf_clean['Trump New']
gdf_clean['Margin Shift'] = gdf_clean['Margin New'] - gdf_clean['Margin 24']

gdf_clean.head()


# In[10]:


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


# In[11]:


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
        'District', 'House_Winner', 'House_Party', 'House_MOV_Raw', 
        'House_Race_Type', 'Effective_House_Margin', 'District_Hover', 'District_Name'
    ] if c in house_df.columns]
    
    gdf_clean = gdf_clean.merge(house_df[merge_cols], on='District', how='left')

# National two-party presidential baseline shifts
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


# In[12]:


# Flag districts flipped by redistricting
gdf_clean["Targeted"] = (gdf_clean["Margin New"] * gdf_clean["Margin 24"]) < 0
gdf_clean["Targeted"] = gdf_clean["Targeted"].astype(bool)

# Specific competitive district overrides
gdf_clean.loc[gdf_clean["District"] == "CA09", "Targeted"] = False

targeted_additions = ["NC01", "OH09", "TX28", "TX34"]
gdf_clean.loc[gdf_clean["District"].isin(targeted_additions), "Targeted"] = True

reordered_columns = [
    "District No.",
    "District",
    "District_Hover",
    "District_Name",
    "WhitePct",
    "MinorityPct",
    "BlackPct",
    "HispanicPct",
    "AsianPct",
    "Partisan_Lean_Index",
    "House_Winner",
    "House_Party",
    "House_MOV_Raw",
    "House_Race_Type",
    "Harris New",
    "Trump New",
    "Margin New",
    "Margin Shift",
    "Partisan Index",
    "Harris 24",
    "Trump 24",
    "Margin 24",
    "Targeted",
    "geometry",
]

export_columns = [col for col in reordered_columns if col in gdf_clean.columns]
gdf_clean = gdf_clean[export_columns]

export_path = os.path.join(data_dir, "map2026.geojson")
gdf_clean.to_file(export_path, driver="GeoJSON")
print(f"Exported compiled district map layer to {export_path}")
gdf_clean.head(10)

