# -*- coding: utf-8 -*-
"""
Created on Sun Apr 12 13:42:10 2026

@author: csabr
"""
import os
import time
import requests
import pandas as pd
import geopandas as gpd

# establishing folder paths
os.makedirs(os.path.join('..','output','geopackages'), exist_ok=True)
os.makedirs(os.path.join('..','output','water'), exist_ok=True)
 
#%% Webscraping Configuration
 
BASE_URL = ("https://www2.census.gov/geo/tiger/TIGER2025/AREAWATER/"
    "tl_2025_{fips}_areawater.zip")
 
# State FIPS → (abbreviation, county count for progress display)
STATES = {
    "06": "CA",   # California  – 58 counties
    "41": "OR",   # Oregon      – 36 counties
    "53": "WA",   # Washington  – 39 counties
}

# setting output directory for downloaded zip files and geopackage name 
OUTPUT_DIR = "water"
OUTPUT_GPKG = "water_tristate.gpkg"

# pausing 0.5 seconds between requests to Census server since pulling 133 files
PAUSE_BETWEEN_REQUESTS = 0.5        

# County FIPS codes (state FIPS + county FIPS = 5-digit GEOID) - dictionary
# Full county FIPS for CA (06), OR (41), WA (53)
# Source: Census Bureau county FIPS tables
COUNTY_FIPS = {
    "06": [
        "001","003","005","007","009","011","013","015","017","019",
        "021","023","025","027","029","031","033","035","037","039",
        "041","043","045","047","049","051","053","055","057","059",
        "061","063","065","067","069","071","073","075","077","079",
        "081","083","085","087","089","091","093","095","097","099",
        "101","103","105","107","109","111","113","115",
    ],
    "41": [
        "001","003","005","007","009","011","013","015","017","019",
        "021","023","025","027","029","031","033","035","037","039",
        "041","043","045","047","049","051","053","055","057","059",
        "061","063","065","067","069","071",
    ],
    "53": [
        "001","003","005","007","009","011","013","015","017","019",
        "021","023","025","027","029","031","033","035","037","039",
        "041","043","045","047","049","051","053","055","057","059",
        "061","063","065","067","069","071","073","075","077",
    ],
}
 
# defining function to build list of FIPS from COUNTY_FIPS dictionary
def build_fips_list() -> list[tuple[str, str, str]]:
    """Return list of (state_fips, county_fips, full_5digit_fips) tuples."""
    records = []
    for state_fp, counties in COUNTY_FIPS.items():
        for county_fp in counties:
            records.append((state_fp, county_fp, state_fp + county_fp))
    return records

# Defining function to download the tiger line 2025 area water zip files for 
# each FIPS code. Download tl_2025_<fips5>_areawater.zip to dest_dir.
# Returns local path on success, None if the file doesn't exist on server
# (some counties have no water features).
def download_zip(fips5: str, dest_dir: str, session: requests.Session) -> str | None:
    
    url = BASE_URL.format(fips=fips5)
    local_path = os.path.join('..','output','water', f"tl_2025_{fips5}_areawater.zip")
 
    # Skip if already cached
    if os.path.exists(local_path):
        return local_path
 
    try:
        response = session.get(url, timeout=60)
        if response.status_code == 404:
            # No water features for this county – not an error
            return None
        response.raise_for_status()
        with open(local_path, "wb") as fh:
            fh.write(response.content)
        return local_path
    except requests.RequestException as exc:
        print(f"  WARNING: could not download {fips5}: {exc}")
        return None
 
#%% Defining function to take the FIPS list, query the Census, download the 
# requested area water tiger line files (printing an "OK" statement if the
# download is successful for each FIPS code), merging all of the 133 zip files
# together into one geodataframe, and then creating a single geopackage with 
# the area water for all counties in CA, OR, and WA. 
 
def main():
 
    fips_list = build_fips_list()
    total = len(fips_list)
    print(f"Downloading area water shapefiles for {total} counties "
          f"across CA, OR, and WA …\n")
 
    session = requests.Session()
    session.headers.update({"User-Agent": "ch"})
 
    # Download phase 
    downloaded: dict[str, list[str]] = {"06": [], "41": [], "53": []}
    skipped = 0
 
    for i, (state_fp, county_fp, fips5) in enumerate(fips_list, start=1):
        state_abbr = STATES[state_fp]
        print(f"  [{i:3d}/{total}] {state_abbr} county {fips5} … ", end="", flush=True)
 
        path = download_zip(fips5, OUTPUT_DIR, session)
        if path:
            downloaded[state_fp].append(path)
            print("OK")
        else:
            skipped += 1
            print("(no water features)")
 
        time.sleep(PAUSE_BETWEEN_REQUESTS)
 
    print(f"\nDownload complete. "
          f"Files retrieved: {total - skipped}  |  Skipped (no data): {skipped}\n")
 
    # Merge phase
    print("Reading shapefiles and merging …")
 
    state_gdfs: dict[str, gpd.GeoDataFrame] = {}
 
    for state_fp, paths in downloaded.items():
        if not paths:
            print(f"  {STATES[state_fp]}: no files – skipping.")
            continue
 
        gdfs = []
        for path in paths:
            try:
                gdf = gpd.read_file(f"zip://{path}")
                # Tag each feature with its source county FIPS
                county_fips5 = os.path.basename(path).split("_")[2]
                gdf["COUNTY_GEOID"] = county_fips5
                gdf["STATE_FIPS"]   = state_fp
                gdf["STATE_ABBR"]   = STATES[state_fp]
                gdfs.append(gdf)
            except Exception as exc:
                print(f"  WARNING: could not read {path}: {exc}")
 
        if gdfs:
            state_gdf = pd.concat(gdfs, ignore_index=True)
            state_gdf = gpd.GeoDataFrame(state_gdf, crs=gdfs[0].crs)
            state_gdfs[state_fp] = state_gdf
            print(f"  {STATES[state_fp]}: {len(state_gdf):,} water features "
                  f"from {len(gdfs)} counties")
 
    # Write GeoPackage 
    print(f"\nWriting {OUTPUT_GPKG} …")
 
    all_gdfs = []
    for state_fp, gdf in state_gdfs.items():
        layer_name = STATES[state_fp].lower()
        gdf.to_file(os.path.join('..','output', OUTPUT_GPKG), layer=layer_name, driver="GPKG")
        print(f"  Layer '{layer_name}' written ({len(gdf):,} features)")
        all_gdfs.append(gdf)
 
    if all_gdfs:
        combined = pd.concat(all_gdfs, ignore_index=True)
        combined = gpd.GeoDataFrame(combined, crs=all_gdfs[0].crs)
        combined.to_file(os.path.join('..','output',OUTPUT_GPKG), layer="tri_state", driver="GPKG")
        print(f"  Layer 'tri_state' written ({len(combined):,} total features)")
 
    print(f"\nDone!  Output saved to: {OUTPUT_GPKG}")
    print(f"Raw zip files cached in: {OUTPUT_DIR}/")
 
# running the script
if __name__ == "__main__":
    main()