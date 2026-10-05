#!/usr/bin/env python
# coding: utf-8

# In[11]:


import csv
import os
import numpy as np
import pandas as pd

# 1. Read cleanly using Python's native CSV reader to handle embedded commas
rows = []
with open('../data/rep.csv', mode='r', encoding='utf-8', errors='replace') as f:
  reader = csv.reader(f)
  for row in reader:
    # If the entire row was imported as a single quoted string, unpack it
    if len(row) == 1 and ',' in row[0]:
      row = next(csv.reader([row[0]]))
    rows.append(row)

# Extract and sanitize headers
header = [
    str(col)
    .strip()
    .replace('"', '')
    .replace("'", '')
    .lower()
    for col in rows[0]
]
data_rows = rows[1:]

# Create DataFrame directly from tokenized rows, truncating or padding any stray fields
expected_len = len(header)
aligned_rows = [
    r[:expected_len] + [''] * max(0, expected_len - len(r)) for r in data_rows
]

raw_df = pd.DataFrame(aligned_rows, columns=header)
print("Successfully loaded columns:", list(raw_df.columns))


# In[12]:


# 2. Filter for 2024 general election
raw_df['year'] = pd.to_numeric(raw_df['year'], errors='coerce')

# Filter for 2024; also filter out special elections/primaries if 'stage' exists
if 'stage' in raw_df.columns:
    df_2024 = raw_df[(raw_df['year'] == 2024) & (raw_df['stage'].astype(str).str.lower().str.startswith('gen'))].copy()
else:
    df_2024 = raw_df[raw_df['year'] == 2024].copy()

# 3. Standardize District ID (Handles at-large 0 -> 01)
df_2024['district_num'] = pd.to_numeric(df_2024['district'], errors='coerce').fillna(1).astype(int)
df_2024['district_num'] = df_2024['district_num'].replace(0, 1)
df_2024['District'] = df_2024['state_po'].astype(str).str.upper().str.strip() + df_2024['district_num'].astype(str).str.zfill(2)

# Ensure numeric candidate votes
df_2024['candidatevotes'] = pd.to_numeric(df_2024['candidatevotes'], errors='coerce').fillna(0)
if 'totalvotes' in df_2024.columns:
    df_2024['totalvotes'] = pd.to_numeric(df_2024['totalvotes'], errors='coerce').fillna(0)
    
df_2024.head()


# In[13]:


# 4. Standardize Party Labels
def classify_party(row):
    party = str(row.get('party', '')).upper()
    if 'DEMOCRAT' in party or 'DEMOCRATIC' in party:
        return 'DEM'
    elif 'REPUBLICAN' in party or 'GOP' in party:
        return 'REP'
    return 'OTHER'

df_2024['party_std'] = df_2024.apply(classify_party, axis=1)

# 5. Sum candidate votes within district (collapses fusion tickets like NY)
cand_totals = df_2024.groupby(['District', 'candidate', 'party_std'], as_index=False)['candidatevotes'].sum()

# 6. Rank candidates within each district
cand_totals['rank'] = cand_totals.groupby('District')['candidatevotes'].rank(ascending=False, method='first')

top1 = cand_totals[cand_totals['rank'] == 1].set_index('District')
top2 = cand_totals[cand_totals['rank'] == 2].set_index('District')

districts = sorted(df_2024['District'].unique())
records = []


# In[14]:


# Optional fallback to presidential baseline for uncontested / top-two races
pres24_path = '../data/2024_pres.csv'
pres24_df = pd.read_csv(pres24_path).set_index('District') if os.path.exists(pres24_path) else None

for d in districts:
    c1 = top1.loc[d] if d in top1.index else None
    c2 = top2.loc[d] if d in top2.index else None
    
    v1 = c1['candidatevotes'] if c1 is not None else 0
    p1 = c1['party_std'] if c1 is not None else 'OTHER'
    
    v2 = c2['candidatevotes'] if c2 is not None else 0
    p2 = c2['party_std'] if c2 is not None else 'OTHER'
    
    tot_2party = v1 + v2
    
    is_uncontested = (v2 == 0) or (tot_2party == 0) or (v1 / (v1 + v2) > 0.95)
    is_same_party = (p1 == p2) and (p1 in ['DEM', 'REP'])
    
    if is_same_party or is_uncontested:
        if pres24_df is not None and d in pres24_df.index:
            pres_margin = (pres24_df.loc[d, 'Harris'] - pres24_df.loc[d, 'Trump 24']) / pres24_df.loc[d, 'Total']
            margin = pres_margin
        else:
            margin = (0.35 if p1 == 'DEM' else -0.35) if is_same_party else (0.50 if p1 == 'DEM' else -0.50)
    else:
        if p1 == 'DEM' and p2 == 'REP':
            margin = (v1 - v2) / tot_2party
        elif p1 == 'REP' and p2 == 'DEM':
            margin = (v2 - v1) / tot_2party
        elif p1 == 'DEM':
            margin = (v1 - v2) / tot_2party
        elif p1 == 'REP':
            margin = -(v1 - v2) / tot_2party
        elif p2 == 'DEM':
            margin = -(v1 - v2) / tot_2party
        elif p2 == 'REP':
            margin = (v1 - v2) / tot_2party
        else:
            margin = 0.0

    records.append({
        'District': d,
        'Winner_Party': p1,
        'RunnerUp_Party': p2,
        'Margin_2party': margin,
        'Is_Uncontested': is_uncontested,
        'Is_Same_Party': is_same_party
    })

house_clean = pd.DataFrame(records)


# In[15]:


house_clean.to_csv('../data/house_2024_national.csv', index=False)
print(f"Generated clean national House dataset for {len(house_clean)} districts.")
house_clean.head(10)

