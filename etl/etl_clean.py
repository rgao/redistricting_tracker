#!/usr/bin/env python
# coding: utf-8

# In[17]:


import os
import glob
import pandas as pd
import geopandas as gpd

file_inputs = [
    {"path": "../data/alabama2026.geojson", "postal": "AL"},
    {"path": "../data/california2026.geojson", "postal": "CA"},
    {"path": "../data/florida2026.geojson", "postal": "FL"},
    {"path": "../data/louisiana2026.geojson", "postal": "LA"},
    {"path": "../data/northcarolina2026.geojson", "postal": "NC"},
    {"path": "../data/ohio2026.geojson", "postal": "OH"},
    {"path": "../data/tennessee2026.geojson", "postal": "TN"},
    {"path": "../data/texas2026.geojson", "postal": "TX"},
    {"path": "../data/utah2026.geojson", "postal": "UT"},
]

# Standard target CRS (EPSG:4326 is standard for GeoJSON)
TARGET_CRS = "EPSG:4326"
all_gdfs = []

for state in file_inputs:
    gdf = gpd.read_file(state["path"])

    if gdf.crs != TARGET_CRS:
        gdf = gdf.to_crs(TARGET_CRS)
        
    # Create matching key for the geojson/csv files with state postal and district number
    gdf["District"] = state["postal"] + gdf["id"].astype(str).str.zfill(2)
    
    gdf = gdf[["id", "District", "DemPct", "RepPct", "WhitePct", "MinorityPct", "BlackPct",
       "HispanicPct", "AsianPct", "Margin","geometry"]]
    
    all_gdfs.append(gdf)

states_gdf = pd.concat(all_gdfs, ignore_index=True)
states_gdf.head(8)


# In[18]:


# 2024 presidential results by Congressional district
pres24 = pd.read_csv("../data/2024_pres.csv")

# Merged desired columns from the csv file into the geojson file
columns_to_keep = ['District', 'Harris', 'Trump 24', 'Total']

pres24 = pres24[columns_to_keep]

# Inner join the datasets on matching District values
merged_gdf = states_gdf.merge(pres24, on='District', how='inner')
merged_gdf.head(8)


# In[19]:


# rename columns
gdf_clean = merged_gdf.rename(columns={
    'id': 'District No.',
    'DemPct': 'Harris New',
    'RepPct': 'Trump New',
    'Margin': 'Partisan Index',
    'Harris': 'Harris 24 Raw',
    'Trump 24': 'Trump 24 Raw',
    'Total': 'Total 24 Raw'
})

gdf_clean.head(8)


# In[20]:


# Create new columns converting the raw votes into percentages, as well as show the percent margin difference
gdf_clean['Harris 24'] = gdf_clean['Harris 24 Raw'] / gdf_clean['Total 24 Raw']
gdf_clean['Trump 24'] = gdf_clean['Trump 24 Raw'] / gdf_clean['Total 24 Raw']

gdf_clean['Margin 24'] = gdf_clean['Harris 24'] - gdf_clean['Trump 24']
gdf_clean['Margin New'] = gdf_clean['Harris New'] - gdf_clean['Trump New']

gdf_clean['Margin Shift'] = gdf_clean['Margin New'] - gdf_clean['Margin 24']

# Remove the columns that we no longer need
# gdf_clean = gdf_clean.drop(columns=['Harris 24 Raw', 'Trump 24 Raw', 'Total 24 Raw'])

gdf_clean.head()


# In[21]:


# 1. Base rule: Districts where winning party flipped
gdf_clean["Targeted"] = (gdf_clean["Margin New"] * gdf_clean["Margin 24"]) < 0
gdf_clean["Targeted"] = gdf_clean["Targeted"].astype(bool)

# 2. Exclude CA09
gdf_clean.loc[gdf_clean["District"] == "CA09", "Targeted"] = False

# 3. Additional targeted districts
targeted_additions = ["NC01", "OH09", "TX28", "TX34"]
gdf_clean.loc[gdf_clean["District"].isin(targeted_additions), "Targeted"] = True

# Reorder columns: race/VAP statistics placed directly after District
reordered_columns = [
    "District No.",
    "District",
    "WhitePct",
    "MinorityPct",
    "BlackPct",
    "HispanicPct",
    "AsianPct",
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

gdf_clean = gdf_clean[reordered_columns]

# Export updated GeoJSON
gdf_clean.to_file("../data/map2026.geojson", driver="GeoJSON")
gdf_clean.head(16)

