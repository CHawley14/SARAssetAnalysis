# -*- coding: utf-8 -*-
"""
Created on Sun Apr 12 11:41:12 2026

@author: csabr
"""
import geopandas as gpd
import os

# establishing folder paths
os.makedirs(os.path.join('..','output','csvs'), exist_ok=True)
os.makedirs(os.path.join('..','output','figures'), exist_ok=True)
os.makedirs(os.path.join('..','output','geopackages'), exist_ok=True)

#%% Defining Functions

infiles = ['past.gpkg', 'present_airstas.gpkg', 'future.gpkg']
labels = ['past', 'present', 'future']

def build_range_rings(infiles:str, loiter:int, labels:str, out:str):
    airstas_gdf = gpd.read_file(os.path.join('..','output','geopackages',infiles),layer='points')

    # Renaming columns 
    airstas_gdf = airstas_gdf.rename(columns={'Range (nm)':'Range_NM','Cruise Speed (kts)':'Speed_kts'})

    
    # formula to calculate maximum range radius 
    # assumes 10% safety factor in range for fuel, takeoff, and landing
    # allows for loitering time option (abilitiy to remain in one place for a period of time)
    # assumes more fuel will be burned by loitering, therefore reducing range
    airstas_gdf['radius_nm'] = ((airstas_gdf['Range_NM']*.9) - (((loiter/60)*airstas_gdf['Speed_kts']*.85)*1.5))/2
    
    print(labels, airstas_gdf['radius_nm'])
    
    # converting nautical miles to meters for projection: 1 NM = 1852 m
    airstas_gdf['radius_m'] = airstas_gdf['radius_nm']*1852

    radius_m = airstas_gdf['radius_m']
    
    # creating buffer using calculated radii for each air station
    rings = airstas_gdf.buffer(radius_m)

    ring_layer = airstas_gdf[['nickname','geometry']].copy()

    ring_layer['geometry'] = rings
    
    # saving buffers to a geopackage
    ring_layer.to_file(os.path.join('..','output','geopackages',out), layer='rings')
    
def build_response_rings(infiles:str, fuel:int, labels:str, out:str):
    airstas_gdf = gpd.read_file(os.path.join('..','output','geopackages',infiles),layer='points')

    # renaming columns
    airstas_gdf = airstas_gdf.rename(columns={'Range (nm)':'Range_NM','Cruise Speed (kts)':'Speed_kts'})

    # Building response time range ring for each air station based on asset
    # FAR/AIM - 30 min fuel reserve for helicopters
    # Assumes max cruise airspeed will not be maintained for entire flight due
    # to takeoff, landing, airspace speed regulations, and a few knots of wind.
    # Response time requirement for CG is 2 hours: 30 min asset prep and departure
    # + 1.5 hours to reach location of call. 3 in formula represents 1.5 * 2 
    # (asset trip to and from location of call).
    # Fuel is a limiting factor for the MH-65 here, but not the MH-60.  
    airstas_gdf['time_radius_nm'] = ((airstas_gdf['Speed_kts']*.85) * (3 - ((fuel/60)*airstas_gdf['Fuel_Limited']*1.2)))/2
    
    print(labels, airstas_gdf['time_radius_nm'])
    
    # converting nautical miles to meters for projection: 1 NM = 1852 m
    airstas_gdf['time_radius_m'] = airstas_gdf['time_radius_nm']*1852

    time_radius_m = airstas_gdf['time_radius_m']
    
    # creating buffer using calculated radii for each air station
    response = airstas_gdf.buffer(time_radius_m)

    response_layer = airstas_gdf[['nickname','geometry']].copy()

    response_layer['geometry'] = response

    # saving buffers to a geopackage
    response_layer.to_file(os.path.join('..','output','geopackages',out), layer='response')

#%% Loop to create geopackages

outfiles = ['past.gpkg', 'present_airstas.gpkg', 'future.gpkg']


for i,l,o in zip(infiles, labels, outfiles):
    # using 0 min for loitering to build max range rings
    build_range_rings(i,0,l,o)
    # using 30 min of fuel reserve per FAR/AIM requirements noted above
    build_response_rings(i,30,l,o)
    
loiter_30min_outfiles = ['loiter_past.gpkg', 'loiter_present_airstas.gpkg', 'loiter_future.gpkg']

for i,l,o in zip(infiles, labels, loiter_30min_outfiles):
    # using 30 min of loitering, can be changed 
    build_range_rings(i,30,l,o)