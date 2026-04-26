# -*- coding: utf-8 -*-
"""
Created on Sun Apr 12 13:46:21 2026

@author: csabr
"""

import requests
import pandas as pd
import geopandas as gpd
import os

# establishing folder paths
os.makedirs(os.path.join('..','output','csvs'), exist_ok=True)
os.makedirs(os.path.join('..','output','figures'), exist_ok=True)
os.makedirs(os.path.join('..','output','geopackages'), exist_ok=True)
os.makedirs(os.path.join('..','data'), exist_ok=True)

# Reading API key 
with open(os.path.join('..','apikey.txt')) as fh:
    apikey = fh.readline().strip()

# setting the api to the American Community Survey 5-Year API endpoint for 2024
api = 'https://api.census.gov/data/2024/acs/acs5'

# Setting up Census query "for" clause to return geographic counties and data
# for all eligible zip codes in those counties. 
for_clause = 'county:*'

# Setting "in" clause for Censsus query to limit selection of counties to those
# that only fall in 06 - CA, 41 - OR, and 53 - WA. 
in_clause = 'state:06,41,53'

payload = {'get':"B01001_001E", 'for':for_clause, 'in':in_clause,'key':apikey}

# Setting up the call to build an Https query string, send it to the API 
# endpoint, and collect the response. 
response = requests.get(api,payload)

# Establishing whether the HTTP status code does not = 200 (code for success) 
if response.status_code != 200:
    print(response.status_code)
    print( response.text )
    # This will cause the script to stop if the statement is reached
    assert False
    
# parsing the JSON returned by the Census server and returning a list of rows
row_list = response.json()

# setting column names = to the first row in row_list
colnames = row_list[0]

# setting data rows to the remaining rows in row_list
datarows = row_list[1:]

# converting the data into a Pandas dataframe
pop = pd.DataFrame(columns=colnames, data=datarows)

pop['pop'] = pop["B01001_001E"].astype(float)

# creating GEOID
pop['GEOID'] = pop['state'] + pop['county']

# setting index for dataframe and then sorting by zip code
pop = pop.set_index('GEOID').sort_index()

# saving to csv
pop.to_csv(os.path.join('..','output','csvs','pop.csv'))

#%% Reading in cartographic boundary shapefile for US counties
geodata = gpd.read_file(os.path.join('..','data','cb_2024_us_county_500k.zip'))

# filtering data down to just CA, OR, and WA counties
geodata = geodata[geodata['STATEFP'].isin(['06', '41', '53'])]

# merging population data onto the shapefile
geodata = geodata.merge(pop,on='GEOID',validate='1:1',indicator=True)

# verifying all 133 counties matched and then dropping merge column
print( geodata['_merge'].value_counts() )
geodata.drop(columns='_merge',inplace=True)

# Writing out as a geopackage file with layer as "pop"
geodata.to_file(os.path.join('..','output','geopackages','pop.gpkg'),layer='pop')
