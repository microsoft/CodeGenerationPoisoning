#!/usr/bin/env python
# coding: utf-8

import pcrglobwb_utils
import xarray as xr
import pandas as pd
import numpy as np
import geopandas as gpd
import rioxarray as rio
import rasterio
import yaml
import click
import glob
import os
import shutil

def print_versions():

    print('pcrglobwb_utils version {}'.format(pcrglobwb_utils.__version__))
    print('pandas version {}'.format(pd.__version__))
    print('xarray version {}'.format(xr.__version__))
    print('numpy version {}'.format(np.__version__))
    print('geopandas version {}'.format(gpd.__version__))
    print('rasterio version {}'.format(rasterio.__version__))
    print('rioxarray version {}'.format(rio.__version__))

def get_idx_as_strftime(df, strftime_format='%Y-%m-%d'):

    idx = df.index.strftime(strftime_format)

    return idx

def check_mode(yaml_file, folder):
    """Checks whether GRDC data is read via a yml-file or all files within a folder are used.
    Also checks that not both options are specified at once.
    """

    if (yaml_file != None) and (folder != None):
        raise ValueError('ERROR: not possible to specify both yaml-file and folder - only one option posssible!')

    if yaml_file != None:
        click.echo(click.style('INFO -- reading GRDC data via yml-file.', fg='red'))
        mode = 'yml'
    if folder != None:
        click.echo(click.style('INFO -- reading GRDC data from folder.', fg='red'))
        mode = 'fld'

    return mode

def read_yml(yaml_file):
    """Loads and parses a yaml-file and returns its content as well root.
    """

    # get path to yml-file containing GRDC station info
    yaml_file = os.path.abspath(yaml_file)
    click.echo(click.style('INFO -- parsing GRDC station information from file {}'.format(yaml_file), fg='red'))
    # get content of yml-file
    with open(yaml_file, 'r') as file:
        data = yaml.safe_load(file)
    # get location of yml-file
    yaml_root = os.path.dirname(yaml_file)

    return data, yaml_root

def glob_folder(folder, grdc_column, verbose=False, encoding='ISO-8859-1'):
    """Collects and reads all files within a folder.
    Assumes all files are GRDC files and retrieves station properties and values from file.
    Returns all of this info as dictionary.
    """

    folder = os.path.abspath(folder)
    click.echo('INFO -- folder with GRDC data is {}'.format(folder))
    files = sorted(glob.glob(os.path.join(folder,'*')))

    dd = dict()

    for f in files:
        if verbose: click.echo('VERBOSE -- loading GRDC file {} with encoding {}.'.format(f, encoding))
        grdc_data = pcrglobwb_utils.obs_data.grdc_data(f)
        # if verbose: click.echo('VERBOSE -- retrieving GRDC station properties.')
        plot_title, props = grdc_data.get_grdc_station_properties(encoding=encoding)

        # retrieving values from GRDC file
        df_obs, props = grdc_data.get_grdc_station_values(col_name=grdc_column, var_name='OBS', encoding=encoding, verbose=verbose)

        df_obs.set_index(pd.to_datetime(df_obs.index), inplace=True)

        dd[str(props['station'])] = [props, df_obs]

    return dd, files

def create_out_dir(out_dir):

    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    
    os.makedirs(out_dir)
    click.echo('INFO -- saving output to folder {}'.format(out_dir))

    return

def get_data_from_yml(yaml_root, data, station, var_name, encoding, verbose):
    """[summary]

    Args:
        yaml_root ([type]): [description]
        data ([type]): [description]
        station ([type]): [description]
        var_name ([type]): [description]
        encoding ([type]): [description]
        verbose ([type]): [description]

    Returns:
        [type]: [description]
    """    

    # construct path to GRDC-file
    grdc_file = os.path.join(yaml_root, data[str(station)]['file'])           
    click.echo('INFO -- reading observations from file {}.'.format(grdc_file))

    grdc_data = pcrglobwb_utils.obs_data.grdc_data(grdc_file)

    if verbose: click.echo('VERBOSE -- retrieving GRDC station properties.')
    plot_title, props = grdc_data.get_grdc_station_properties(encoding=encoding)

    # retrieving values from GRDC file
    if 'column' in data[str(station)].keys():
        df_obs, props = grdc_data.get_grdc_station_values(col_name=data[str(station)]['column'], var_name=var_name, encoding=encoding, verbose=verbose)
    else:
        df_obs, props = grdc_data.get_grdc_station_values(var_name=var_name, verbose=verbose, encoding=encoding)
    df_obs.set_index(pd.to_datetime(df_obs.index), inplace=True)

    # if 'lat' or 'lon' are specified for a station in yml-file,
    # use this instead of GRDC coordinates
    if 'lat' in data[str(station)].keys():
        if verbose: click.echo('VERBOSE -- overwriting GRDC latitude information {} with user input {}.'.format(props['latitude'], data[str(station)]['lat']))
        props['latitude'] = data[str(station)]['lat']
    if 'lon' in data[str(station)].keys():
        if verbose: click.echo('VERBOSE -- overwriting GRDC longitude information {} with user input {}.'.format(props['longitude'], data[str(station)]['lon']))
        props['longitude'] = data[str(station)]['lon']

    if ('lon' in data[str(station)].keys()) or ('lat' in data[str(station)].keys()):
        lat_lon_flag = True
    else:
        lat_lon_flag = False

    return df_obs, props, lat_lon_flag

def align_geo(ds, crs_system='epgs:4326', verbose=False):

    # align spatial settings of nc-files to be compatible with geosjon-file or ply-file
    if verbose: click.echo('VERBOSE -- setting spatial dimensions and crs of nc-files')
    
    try:
        ds.rio.set_spatial_dims(x_dim='lon', y_dim='lat', inplace=True)
    except:
        ds.rio.set_spatial_dims(x_dim='longitude', y_dim='latitude', inplace=True)

    ds.rio.write_crs(crs_system, inplace=True)

    return ds

def concat_dataframes(obs_data_c, sim_data_c, obs_var_name, sim_var_name, obs_idx, sim_idx, time_step, anomaly, verbose):

    # initiate output lists
    mean_val_timestep_obs = list()
    mean_val_timestep_sim = list()

    # compute mean per time step in clipped data-array and append to array
    for i in range(len(obs_data_c.time.values)):
        time = obs_data_c.time[i]
        t = pd.to_datetime(time.values)
        mean = float(obs_data_c.sel(time=t).mean(skipna=True))
        mean_val_timestep_obs.append(mean)
    for i in range(len(sim_data_c.time.values)):
        time = sim_data_c.time[i]
        t = pd.to_datetime(time.values)
        mean = float(sim_data_c.sel(time=t).mean(skipna=True))
        mean_val_timestep_sim.append(mean)

    # determine anomalies is specified
    if anomaly:
        if verbose: click.echo('VERBOSE -- determine anomalies of SIM data.')
        # mean_val_timestep_obs = mean_val_timestep_obs - np.mean(mean_val_timestep_obs)
        mean_val_timestep_sim = mean_val_timestep_sim - np.mean(mean_val_timestep_sim)

    obs_df = pd.DataFrame(data=mean_val_timestep_obs, index=obs_idx, columns=[obs_var_name])
    sim_df = pd.DataFrame(data=mean_val_timestep_sim, index=sim_idx, columns=[sim_var_name])

    # accounting for missing values in time series (and thus missing index values!)
    if time_step == 'monthly':
        if verbose: click.echo('VERBOSE -- covering missing months in observation or simulation data.')
        obs_df = obs_df.resample('D').mean().fillna(np.nan).resample('M').mean()
        sim_df = sim_df.resample('D').mean().fillna(np.nan).resample('M').mean()  
    if time_step == 'annual':
        if verbose: click.echo('VERBOSE -- covering missing years in observation or simulation data.')
        obs_df = obs_df.resample('D').mean().fillna(np.nan).resample('Y').mean()
        sim_df = sim_df.resample('D').mean().fillna(np.nan).resample('Y').mean()  

    # concatenating both dataframes to drop rows with missing values in one of the columns
    # dropping rows with missing values is import because time extents of both files probably do not match
    if verbose: click.echo('VERBOSE -- concatenating observed and simulated data.')
    final_df = pd.concat([obs_df, sim_df], axis=1).dropna()

    return final_df
