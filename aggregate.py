import json
import os

# Define current top-line aggregates from RCP and FiftyPlusOne
# (You can update these manually when you pull fresh numbers or parse them via API/downloads)
rcp_dem = 50.5
rcp_rep = 42.4
rcp_margin = rcp_dem - rcp_rep  # +8.1

# FiftyPlusOne Generic Ballot Top-Line Average
fpo_dem = 52.0
fpo_rep = 42.9
fpo_margin = fpo_dem - fpo_rep  # +9.0

# Compute the meta-aggregate (Average of the Aggregates)
meta_dem_avg = (rcp_dem + fpo_dem) / 2
meta_rep_avg = (rcp_rep + fpo_rep) / 2
meta_margin_avg = meta_dem_avg - meta_rep_avg

environment_data = {
    "sources": [
        {
            "name": "RealClearPolling Aggregate",
            "dem": rcp_dem,
            "rep": rcp_rep,
            "margin": round(rcp_margin, 2),
        },
        {
            "name": "FiftyPlusOne Aggregate",
            "dem": fpo_dem,
            "rep": fpo_rep,
            "margin": round(fpo_margin, 2),
        },
    ],
    "meta_aggregate": {
        "dem_share": round(meta_dem_avg, 2),
        "rep_share": round(meta_rep_avg, 2),
        "gcb_margin": round(meta_margin_avg, 2),
        "formatted_margin": (
            f"D+{round(meta_margin_avg, 1)}"
            if meta_margin_avg > 0
            else f"R+{round(abs(meta_margin_avg), 1)}"
        ),
    },
}

# Ensure output directory exists inside docs/
os.makedirs("docs", exist_ok=True)
output_path = "docs/environment.json"

with open(output_path, "w") as f:
  json.dump(environment_data, f, indent=2)

print(
    f"Successfully updated environment model to:"
    f" {environment_data['meta_aggregate']['formatted_margin']}"
)
print(f"Saved to {output_path}")
