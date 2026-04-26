# -*- coding: utf-8 -*-
"""
Created on Sun Apr 12 07:26:59 2026

@author: csabr
"""

import requests
import json
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import os

# Create output folders

os.makedirs(os.path.join('..','output','csvs'), exist_ok=True)
os.makedirs(os.path.join('..','output','figures'), exist_ok=True)
os.makedirs(os.path.join('..','output','geopackages'), exist_ok=True)

# projection type
wgs84 = 4326

#  List of air stations to geocode. Pulled from searches of 
#  https://www.dcms.uscg.mil/

units = [
    "Coast Guard Air Station Port Angeles",
    "Coast Guard Sector Astoria",
    "Coast Guard Air Station North Bend",
    "Coast Guard Air Station Humboldt Bay",
    "Coast Guard Air Station San Francisco",
    "Coast Guard Air Station Ventura",
    "Coast Guard Air Station San Diego"
    ]

# API endpoint
api = "https://nominatim.openstreetmap.org/search"

#  Loop through the air stations and build a list of results.
locations = []

for a in units:

    #  Building the payload, setting up header to identify self, and make
    #  the query. 

    payload = { 'q':f'<{a}>', 'format':'json' }
    headers = { 'user-agent': 'ch' }

    response = requests.get(api,payload,headers=headers)

    assert response.status_code == 200

    #  Parse the result
    result = response.json()

    #  Print it for reference
    print( json.dumps(result, indent=4) )

    #  Pull out key information, specifically lat/long, & append it to the list
    for r in result:
        newloc = {
            'query':a,
            'name':r['display_name'],
            'lat':r['lat'],
            'lon':r['lon']
            }
        locations.append(newloc)

#%% Build a dataframe and write it out

adds = pd.DataFrame(locations)
adds.to_csv(os.path.join('..','output','csvs','airsta_locations.csv'),index=False)

#%% Visualization

#  Read US map from U.S. Census for reference
us = gpd.read_file("https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_us_state_20m.zip")

# only keeping map of contiguous US 
us = us[~us['STUSPS'].isin(['AK', 'HI', 'PR', 'VI', 'GU', 'MP', 'AS'])]

# saving as geopackage
us.to_file(os.path.join('..','output','geopackages','units.gpkg'),layer='us')

#  Build GeoDataFrame of the geocoded points
geom = gpd.points_from_xy(adds['lon'], adds['lat'])
geo = gpd.GeoDataFrame(data=adds, geometry=geom, crs=wgs84)

# reprojecting 
geo = geo.to_crs(us.crs)
# saving to geopackage under a new layer
geo.to_file(os.path.join('..','output','geopackages','units.gpkg'),layer='locations')

#  Drawing a quick map for reference
fig,ax = plt.subplots(dpi=300)
us.boundary.plot(color='black', linewidth=0.4, ax=ax)
geo.plot(color='red', marker='D', markersize=20, ax=ax)
ax.axis('off')
fig.savefig(os.path.join('..','output','figures','units.png'))


