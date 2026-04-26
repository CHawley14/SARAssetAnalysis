# -*- coding: utf-8 -*-
"""
Created on Sun Apr 12 12:25:20 2026

@author: csabr
"""

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# establishing folder paths
os.makedirs(os.path.join('..','output','csvs'), exist_ok=True)
os.makedirs(os.path.join('..','output','figures'), exist_ok=True)
os.makedirs(os.path.join('..','output','geopackages'), exist_ok=True)
os.makedirs(os.path.join('..','data'), exist_ok=True)

# defining a function to compute area covered by all buffers in a single geopackage

def compute_AOR_coverage(filepath:str, layer:str ) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:

    coverage = gpd.read_file(os.path.join('..','output','geopackages',filepath), layer=layer)
    AOR_coverage = coverage.copy()

    # calculating the area of each ring
    AOR_coverage['AOR_area'] = AOR_coverage.area

    # dissolve rings into 1 layer
    AOR_coverage_buffer = AOR_coverage.dissolve()
    AOR_coverage_buffer['nickname'] = AOR_coverage_buffer['nickname'].replace('PA','PACAREA')

    # calculating the area of West Coast (PACAREA) buffer
    AOR_coverage_buffer['AOR_area'] = AOR_coverage_buffer.area
    
    # union of rings to show overlap slices
    ring_slices = AOR_coverage.overlay(AOR_coverage, how='union')

    ring_slices['slices_area'] = ring_slices.area

    # Clean up missing data and create column of sorted_pairs, before filtering
    rscopy = ring_slices.copy()
    
    rscopy['sorted_pairs'] = rscopy.apply(
    lambda row: tuple(sorted([
        row['nickname_1'] if pd.notna(row['nickname_1']) else 'None',
        row['nickname_2'] if pd.notna(row['nickname_2']) else 'None'
    ])), axis=1
    )

    # Only keeping adjacent station pairs
    valid_pairs = {('A', 'NB'), ('A', 'PA'), ('HB', 'NB'), ('HB', 'SF'), ('SF', 'VC'), ('SD', 'VC')}
    rsccopy = rscopy[rscopy['sorted_pairs'].isin(valid_pairs)].drop_duplicates(subset='sorted_pairs')
    
    # dissolving overlapping slices into 1 buffer
    rsccopy = rsccopy.dissolve()
    
    # calculating area of the overlapping slices buffer to calculate area
    # covered by 2 air stations
    dual_cover_area = rsccopy.area
    
    return AOR_coverage, AOR_coverage_buffer, ring_slices, rsccopy, dual_cover_area

#%% Range rings for all three time periods = ['past', 'present', 'future']
infiles = ['past.gpkg', 'present_airstas.gpkg', 'future.gpkg']
response_infiles = ['past.gpkg', 'present_airstas.gpkg', 'future.gpkg']
loiter_30min_infiles = ['loiter_past.gpkg', 'loiter_present_airstas.gpkg', 'loiter_future.gpkg']
range_labels = ['past', 'present', 'future']
response_labels = ['past_response', 'present_response', 'future_response']
loiter_labels = ['past_loiter', 'present_loiter', 'future_loiter']

# empty dictionaries for results
buffer_results = {}
slices_results = {}
rsccopies = {}
dual_cover_results = {}

# Loop to create results for maximum range buffers for all time periods
for i,r in zip(infiles, range_labels):
    AOR_coverage, AOR_coverage_buffer, ring_slices, rsccopy, dual_cover_area = compute_AOR_coverage(i,'rings')
    buffer_results[r] = {'AOR_coverage_buffer': AOR_coverage_buffer}
    slices_results[r] = {'ring_slices': ring_slices}
    rsccopies[r] = {'rsccopy': rsccopy}
    dual_cover_results[r] = {'dual_cover_area': dual_cover_area}

# Loop to create results for response time buffers for all time periods
for r,rl in zip(response_infiles, response_labels):
    AOR_coverage, AOR_coverage_buffer, ring_slices, rsccopy, dual_cover_area = compute_AOR_coverage(r,'response')
    buffer_results[rl] = {'AOR_coverage_buffer': AOR_coverage_buffer}
    slices_results[rl] = {'ring_slices': ring_slices}
    rsccopies[rl] = {'rsccopy': rsccopy}
    dual_cover_results[rl] = {'dual_cover_area': dual_cover_area}

# Loop to create results for 30 min loiter range buffers for all time periods
for l,ll in zip(loiter_30min_infiles, loiter_labels):
    AOR_coverage, AOR_coverage_buffer, ring_slices, rsccopy, dual_cover_area = compute_AOR_coverage(l,'rings')
    buffer_results[ll] = {'AOR_coverage_buffer': AOR_coverage_buffer}
    slices_results[ll] = {'ring_slices': ring_slices}
    rsccopies[ll] = {'rsccopy': rsccopy}
    dual_cover_results[ll] = {'dual_cover_area': dual_cover_area}
    
#%% defining function for building dataframes from results stored in dictionaries

def build_analyze_df(labels, buffer_results, dual_cover_results):
    """Build a summary DataFrame from coverage result dicts."""
    return pd.DataFrame({
        "Time": labels,
        "Area": [buffer_results[r]['AOR_coverage_buffer']['AOR_area'].values[0] for r in labels],
        "Dual": [dual_cover_results[r]['dual_cover_area'].values[0] for r in labels],
    })

analyze_range = build_analyze_df(range_labels,buffer_results, dual_cover_results)

analyze_response = build_analyze_df(response_labels, buffer_results, dual_cover_results)

analyze_loiter = build_analyze_df(loiter_labels, buffer_results, dual_cover_results)

# list of new dataframes
analyze_dfs = [analyze_range, analyze_response, analyze_loiter]

#%% defining a function to build analysis bar graphs 

titles = ['Range','Response','30_Min_Loiter']
present_keys = ['present', 'present_response', 'present_loiter']
double_bar_titles = ['AOR Area Compared to Present & Dual Cover Percents',
                     'Response Area Compared to Present & Dual Cover Percents',
                     '30 Min Loiter Area Compared to Present & Dual Cover Percents']

def build_analysis_graphs(df, title, present_key, title2):
    df = df.copy()
    present_area   = df.loc[df['Time'] == present_key, 'Area'].values[0]
    # normalizing data to present in %
    df['%present'] = df['Area'] / present_area * 100
    print(title,'%present:',df['%present'])
    # normalizing data to present in %
    df['%dual']    = df['Dual'] / df['Area'] * 100
    print(title,'%dual:',df['%dual'])
    
    # single bar chart
    fig, ax = plt.subplots()
    sns.barplot(data=df, x="Time", y="%present", palette="Set1", ax=ax)
    ax.set_title(title)
    plt.show()
    plt.close(fig)
    fig.savefig(os.path.join('..','output','figures',f'{title}.png'))
    
    # double bar chart
    width = 0.4
    x = np.arange(len(df['Time']))
    # Create figure and axis
    fig, ax = plt.subplots()
    # Plot bars side-by-side
    ax.bar(x - width/2, df['%present'], width=width, label='% of present')
    ax.bar(x + width/2, df['%dual'], width=width, label='% dual cover')
    # Customize chart
    ax.set_xticks(x)
    ax.set_xticklabels(df['Time'])
    ax.set_ylabel('Percent')
    ax.set_title(title2)
    ax.legend()
    plt.show()
    fig.savefig(os.path.join('..','output','figures',f'Dual_Area_{title}.png'))

# Loop to great graphs for all ranges capturing all 3 time periods for each
for d, t, pk, dbt in zip(analyze_dfs, titles, present_keys, double_bar_titles):
    build_analysis_graphs(d, t, pk,dbt)

