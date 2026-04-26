# -*- coding: utf-8 -*-
"""
Created on Mon Apr  6 16:10:01 2026

@author: csabr
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import os

# establishing folder paths
os.makedirs(os.path.join('..','output','csvs'), exist_ok=True)
os.makedirs(os.path.join('..','output','figures'), exist_ok=True)
os.makedirs(os.path.join('..','output','geopackages'), exist_ok=True)
os.makedirs(os.path.join('..','data'), exist_ok=True)

#%% Building Dataframe of Air Stations with assigned assets' information

# creating dataframe with contiguous west coast USCG Air Stations
locations = pd.read_csv(os.path.join('..','output','csvs','airsta_locations.csv'),
                        dtype={'lat':str,'lon':str})

# creating dataframe with all USCG helicopter assets
aircraft = pd.read_csv(os.path.join('..','data','Aircraft.csv'))

# building dictionary of nicknames
nicknames = {'Coast Guard Air Station Port Angeles':'PA', 
             'Coast Guard Sector Astoria':'A',
             'Coast Guard Air Station North Bend':'NB',
             'Coast Guard Air Station Humboldt Bay':'HB', 
             'Coast Guard Air Station San Francisco':'SF',
             'Coast Guard Air Station Ventura':'VC',
             'Coast Guard Air Station San Diego':'SD',
             'MH-60T':'Jayhawk',
             'MH-65E':'Dolphin'}

# drop 'name' column as it contains more than just the air station name
locations.drop(columns='name',inplace=True)

# creating new column of nicknames for each air station 
locations['nickname'] = locations['query'].map(nicknames)

# renaming column
aircraft = aircraft.rename(columns={'Aircraft Type':'assets'})

# adding fuel limited column 
# the MH-65 helicopter is fuel limited compared to the MH-60 helicopter
aircraft['Fuel_Limited'] = 0
aircraft.loc[aircraft['assets'] == 'MH-65E', 'Fuel_Limited'] = 1

# dictionary of assets at each air station in past
past_asset_assign = {'PA':'MH-65E','A':'MH-60T','NB':'MH-65E','HB':'MH-65E',
                'SF':'MH-65E','VC':'MH-65E','SD':'MH-60T'}

# dictionary of assets at each air station for present
asset_assign = {'PA':'MH-65E','A':'MH-60T','NB':'MH-65E','HB':'MH-65E',
                'SF':'MH-65E','VC':'MH-60T','SD':'MH-60T'}

# dictionary of assets at each air station in future
future_asset_assign = {'PA':'MH-60T','A':'MH-60T','NB':'MH-60T','HB':'MH-60T',
                'SF':'MH-60T','VC':'MH-60T','SD':'MH-60T'}

# list of dictionaries
assignments = [past_asset_assign, asset_assign, future_asset_assign]

# list of time periods
labels = ['past_airstas','present_airstas','future_airstas']

# list of outfiles
outfiles = ['past.gpkg', 'present_airstas.gpkg', 'future.gpkg']

# empty dictionary
airsta_gdfs = {}

#%% Loop to create geopackages

for a, l, o in zip(assignments, labels, outfiles):
    
    # adding assets to each air station in airstas df
    airstas = locations.copy()
    airstas['assets'] = airstas['nickname'].map(a)
    
    # joining aircraft df onto airstas df using assets
    airstas = airstas.merge(aircraft,left_on=['assets'], right_on=['assets'],how='left')

    # replacing assets with dictionary nicknames for aircraft
    airstas['assets'] = airstas['assets'].replace(nicknames)

    # set the 'nickname' column as the index for the airstas df
    airstas.set_index('nickname',inplace=True)

    # Building Points layer for air station locations
    
    # Creating geometry column from lat/lon
    geometry = [Point(lon, lat) for lat, lon in zip(airstas['lat'], airstas['lon'])]

    # Building GeoDataFrame (WGS84 / EPSG:4326)
    airstas_gdf = gpd.GeoDataFrame(airstas, geometry=geometry, crs="EPSG:4326")

    # reprojecting 
    airstas_gdf = airstas_gdf.to_crs(epsg=26910)

    airstas_gdf = airstas_gdf.reset_index()
    
    # store in dictionary and save
    airsta_gdfs[l] = airstas_gdf
    airstas_gdf.to_file(os.path.join('..','output','geopackages',o), layer='points')
    
    print(f"Saved {l}: {o}")