#!/usr/bin/env python
# coding: utf-8

# In[1]:


import csv
import os
import numpy as np
import pandas as pd

# Load and align 2024 congressional candidate returns
data_dir = "data" if os.path.exists("data") else "../data"
rep_path = os.path.join(data_dir, "pres2024", "rep.csv")

rows = []
with open(rep_path, mode='r', encoding='utf-8', errors='replace') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) == 1 and ',' in row[0]:
            row = next(csv.reader([row[0]]))
        rows.append(row)

header = [
    str(col).strip().replace('"', '').replace("'", '').lower()
    for col in rows[0]
]
data_rows = rows[1:]
expected_len = len(header)
aligned_rows = [
    r[:expected_len] + [''] * max(0, expected_len - len(r)) for r in data_rows
]

raw_df = pd.DataFrame(aligned_rows, columns=header)

# Filter for 2024 House general and primary contests
raw_df['year'] = pd.to_numeric(raw_df['year'], errors='coerce')
raw_df['office_clean'] = raw_df['office'].astype(str).str.upper()

df_2024 = raw_df[
    (raw_df['year'] == 2024) & 
    (raw_df['office_clean'].str.contains('HOUSE', na=False))
].copy()

df_2024['district_num'] = pd.to_numeric(df_2024['district'], errors='coerce').fillna(1).astype(int)
df_2024['district_num'] = df_2024['district_num'].replace(0, 1)
df_2024['District'] = (
    df_2024['state_po'].astype(str).str.upper().str.strip() + 
    df_2024['district_num'].astype(str).str.zfill(2)
)

df_2024['candidatevotes'] = pd.to_numeric(df_2024['candidatevotes'], errors='coerce').fillna(0)
df_2024['stage_std'] = df_2024['stage'].astype(str).str.lower().str.strip()

print(f"Loaded {len(df_2024)} records across {df_2024['District'].nunique()} districts.")
df_2024.head()


# In[2]:


# Classify major-party affiliations
def classify_party(p):
    p_str = str(p).upper().strip()
    if 'DEMOCRAT' in p_str:
        return 'DEM'
    elif 'REPUBLICAN' in p_str or 'GOP' in p_str:
        return 'REP'
    elif 'LIBERTARIAN' in p_str:
        return 'LIB'
    elif 'GREEN' in p_str:
        return 'GRN'
    return 'OTHER'

df_2024['party_std'] = df_2024['party'].apply(classify_party)

# Benchmark primary two-party margins for jungle primary contests
primaries = df_2024[df_2024['stage_std'].str.startswith('pri')].copy()
pri_totals = primaries.groupby(['District', 'party_std'])['candidatevotes'].sum().unstack(fill_value=0)

pri_totals['Dem_Pri'] = pri_totals['DEM'] if 'DEM' in pri_totals.columns else 0.0
pri_totals['Rep_Pri'] = pri_totals['REP'] if 'REP' in pri_totals.columns else 0.0
pri_totals['Two_Party_Pri'] = pri_totals['Dem_Pri'] + pri_totals['Rep_Pri']
pri_totals['Pri_Margin'] = np.where(
    pri_totals['Two_Party_Pri'] > 0,
    (pri_totals['Dem_Pri'] - pri_totals['Rep_Pri']) / pri_totals['Two_Party_Pri'],
    np.nan
)

# Consolidate candidate vote totals across minor-party fusion lines
general = df_2024[df_2024['stage_std'].str.startswith('gen')].copy()

cand_totals = general.groupby(
    ['District', 'candidate', 'party_std'], 
    as_index=False
)['candidatevotes'].sum()

# Rank leading candidates by general election vote share
cand_totals['rank'] = cand_totals.groupby('District')['candidatevotes'].rank(
    ascending=False, 
    method='first'
)

top1 = cand_totals[cand_totals['rank'] == 1].set_index('District')
top2 = cand_totals[cand_totals['rank'] == 2].set_index('District')

print(f"Ranked candidates for {len(top1)} districts with general elections.")


# In[3]:


# Build district-level winner profiles and classify race dynamics
districts = sorted(df_2024['District'].unique())
records = []

for d in districts:
    c1 = top1.loc[d] if d in top1.index else None
    c2 = top2.loc[d] if d in top2.index else None

    v1 = float(c1['candidatevotes']) if c1 is not None else 0.0
    p1 = str(c1['party_std']) if c1 is not None else 'OTHER'
    name1 = str(c1['candidate']) if c1 is not None else 'Uncontested / Vacant'

    v2 = float(c2['candidatevotes']) if c2 is not None else 0.0
    p2 = str(c2['party_std']) if c2 is not None else 'OTHER'
    name2 = str(c2['candidate']) if c2 is not None else ''

    tot_gen = v1 + v2
    raw_mov = ((v1 - v2) / tot_gen) if tot_gen > 0 else 1.0

    is_same_party = (p1 == p2) and (p1 in ['DEM', 'REP'])
    is_uncontested = (v2 == 0) or (p2 not in ['DEM', 'REP']) or (v1 / tot_gen > 0.95 if tot_gen > 0 else True)

    effective_house_margin = np.nan
    race_type = 'Standard Contest'

    # Same-party general contest: leverage top-two primary benchmark
    if is_same_party:
        if d in pri_totals.index and not np.isnan(pri_totals.loc[d, 'Pri_Margin']):
            effective_house_margin = pri_totals.loc[d, 'Pri_Margin']
            race_type = f"Top-Two Benchmark ({p1} vs {p2})"
        else:
            race_type = f"Same-Party General ({p1} vs {p2})"

    # Standard two-party contest (+ Dem, - Rep)
    elif not is_uncontested and {p1, p2} == {'DEM', 'REP'}:
        effective_house_margin = (v1 - v2) / tot_gen if p1 == 'DEM' else -(v1 - v2) / tot_gen
        race_type = 'Standard General Contest'

    # Uncontested or non-major party challenger
    else:
        race_type = 'Unopposed / Third-Party Challenger'

    records.append({
        'District': d,
        'House_Winner': name1.title(),
        'House_Party': p1,
        'House_RunnerUp': name2.title(),
        'House_RunnerUp_Party': p2,
        'House_MOV_Raw': raw_mov,
        'House_Race_Type': race_type,
        'Effective_House_Margin': effective_house_margin
    })

house_summary = pd.DataFrame(records)

# Ingesting data of current sitting Representatives
try:
    print("Fetching live current representative directory...")
    current_reps_url = "https://theunitedstates.io/congress-legislators/legislators-current.csv"
    cur_df = pd.read_csv(current_reps_url)
    
    # Filter for House of Representatives only
    cur_house = cur_df[cur_df['type'] == 'rep'].copy()
    cur_house['district_clean'] = pd.to_numeric(cur_house['district'], errors='coerce').fillna(1).astype(int)
    cur_house['District'] = cur_house['state'].astype(str).str.upper() + cur_house['district_clean'].astype(str).str.zfill(2)
    
    cur_house['Current_Rep'] = cur_house['first_name'].fillna('') + ' ' + cur_house['last_name'].fillna('')
    cur_house['Current_Rep'] = cur_house['Current_Rep'].str.strip()
    
    # Merge live representative; fall back to 2024 general winner if empty
    house_summary = house_summary.merge(cur_house[['District', 'Current_Rep']], on='District', how='left')
    house_summary['Current_Rep'] = house_summary['Current_Rep'].fillna(house_summary['House_Winner'])
    
    # Update House_Winner so downstream charts pick up the incumbent immediately
    house_summary['House_Winner'] = house_summary['Current_Rep']
    print(f"Successfully integrated {len(cur_house)} live sitting representatives.")
except Exception as e:
    print(f"Warning: Live congress-legislators fetch failed ({e}). Retaining 2024 winners.")
    house_summary['Current_Rep'] = house_summary['House_Winner']

summary_out = os.path.join(data_dir, "pres2024", "house_2024_summary.csv")
house_summary.to_csv(summary_out, index=False)
print(f"Generated House summary table for {len(house_summary)} districts.")
house_summary.head(10)


# In[4]:


# Calculate two-party presidential baseline and export processed summary
pres24_path = os.path.join(data_dir, "pres2024", "2024_pres.csv")
pres24_df = pd.read_csv(pres24_path)

pres24_df['Margin 24'] = (pres24_df['Harris'] - pres24_df['Trump 24']) / pres24_df['Total']

final_df = house_summary.merge(pres24_df[['District', 'Margin 24']], on='District', how='left')

# Fallback to presidential margin if House race was uncontested
mask_impute = final_df['Effective_House_Margin'].isna()
final_df.loc[mask_impute, 'Effective_House_Margin'] = final_df.loc[mask_impute, 'Margin 24']

# Format display strings for baseline ratings
def format_lean(val):
    if pd.isna(val) or abs(val) < 0.005:
        return "EVEN"
    pct = abs(val) * 100
    return f"D +{pct:.1f}%" if val > 0 else f"R +{pct:.1f}%"

final_df['Blended_Index_Raw'] = (0.65 * final_df['Margin 24']) + (0.35 * final_df['Effective_House_Margin'])
final_df['Blended_PVI'] = final_df['Blended_Index_Raw'].apply(format_lean)

processed_out = os.path.join(data_dir, "pres2024", "house_2024_processed.csv")
final_df.to_csv(processed_out, index=False)
print("ETL complete. house_2024_processed.csv is ready to merge into map2026.geojson.")
final_df.head(10)

