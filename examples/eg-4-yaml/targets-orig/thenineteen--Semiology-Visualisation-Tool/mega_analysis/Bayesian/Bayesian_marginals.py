from mega_analysis.crosstab.file_paths import file_paths
from mega_analysis.semiology import Semiology, Laterality
from mega_analysis.crosstab.mega_analysis.MEGA_ANALYSIS import MEGA_ANALYSIS
from mega_analysis.crosstab.mega_analysis.QUERY_SEMIOLOGY import QUERY_SEMIOLOGY
from mega_analysis.crosstab.all_localisations import all_localisations
from mega_analysis.crosstab.mega_analysis.exclusions import (exclude_ET, exclude_cortical_stimulation, exclude_spontaneous_semiology,
                                                             exclude_postictals)
from mega_analysis.crosstab.lobe_top_level_hierarchy_only import top_level_lobes
from mega_analysis.semiology import recursive_items
from mega_analysis.Sankey_Functions import normalise_top_level_localisation_cols

import pandas as pd
from pandas.testing import assert_frame_equal
# import os
import yaml
import copy
# os.chdir('C:/Users/ali_m/AnacondaProjects/PhD/Semiology-Visualisation-Tool/')


def query_semiology_wrapper_from_scripts(df, semiology_list, semiology_dict_path):
    """
    From scripts/figures.py in kd_figures-v3 branch
    """
    query_results = {}
    for semiology in semiology_list:
        query_inspection, num_query_lat, num_query_loc = QUERY_SEMIOLOGY(df,
                                                                         semiology_term=semiology,
                                                                         ignore_case=True,
                                                                         semiology_dict_path=semiology_dict_path,
                                                                         all_columns_wanted=True)
        # col1=col1, col2=col1)

        one_query_result = {
            'query_inspection': query_inspection,
            'num_query_lat': num_query_lat,
            'num_query_loc': num_query_loc
        }
        query_results[semiology] = one_query_result
    return query_results


def summary_semio_loc_df_from_scripts(normalise=True):
    """
    Lots of copy pasting from scripts/figures.py in kd_figures-v3 branch.

    returns query_results which is a nested dictionary
        full
        spontaneous
        topology
            {semiologies}
                query_inspection
                num_query_loc
                num_query_lat
    """

    # Define paths
    repo_dir, resources_dir, excel_path, semiology_dict_path = file_paths()

    Semio2Brain_Database = excel_path
    with open(semiology_dict_path) as f:
        SemioDict = yaml.load(f, Loader=yaml.FullLoader)

    region_names = all_localisations()
    semiology_list = list(recursive_items(SemioDict))

    (original_df,
     df_ground_truth, df_study_type,
     num_database_articles, num_database_patients, num_database_lat, num_database_loc) = \
        MEGA_ANALYSIS(Semio2Brain_Database,
                      exclude_data=True)

    # -----------------------------------
    redistribution_spec = {
        'FT': ['FL', 'INSULA', 'Lateral Temporal', 'TL'],
        'TO': ['Lateral Temporal', 'TL', 'OL'],
        'TP': ['Lateral Temporal', 'TL', 'PL'],
        'FTP': ['INSULA', 'Lateral Temporal', 'TL', 'FL', 'PL'],
        'TPO Junction': ['Lateral Temporal', 'TL', 'PL', 'OL'],
        'PO': ['PL', 'OL'],
        'FP': ['FL', 'PL'],
        'Perisylvian': ['INSULA', 'Lateral Temporal', 'TL', 'FL', 'PL'],
        'Sub-Callosal Cortex': ['Ant Cing (frontal, genu)', 'CING']
    }
    redistributed_df = copy.deepcopy(original_df)
    # probably not needed as used exclude_data True when calling M_A
    redistributed_df = exclude_postictals(redistributed_df)

    for from_region, destination_regions in redistribution_spec.items():
        for destination in destination_regions:
            redistributed_df[destination] = original_df[destination].fillna(
                0) + original_df[from_region].fillna(0)
    redistributed_df = redistributed_df.drop(redistribution_spec.keys(), 'columns')
    # -----------------------------------

    # region_names_re = region_names
    # region_names_re['top_level'] = ['TL',
    #                                 'FL',
    #                                 'CING',
    #                                 'PL',
    #                                 'OL',
    #                                 'INSULA',
    #                                 'Hypothalamus',
    #                                 'Cerebellum', ]
    # region_names_re['top_level_all_other'] = ['Cerebellum']

    df = copy.deepcopy(redistributed_df)
    df_SS = exclude_ET(df)
    df_SS = exclude_cortical_stimulation(df_SS)
    df_TS = exclude_spontaneous_semiology(df)

    all_dfs = {
        'full': df,
        'spontaneous': df_SS,
        'topology':  df_TS,
    }

    query_results = {}
    for key, df in all_dfs.items():
        if normalise:
            df, _ = normalise_top_level_localisation_cols(df, Bayesian=True)
        query_results[key] = query_semiology_wrapper_from_scripts(df, semiology_list, semiology_dict_path)


    return query_results


def marginal_GIF_probabilities(all_combined_gifs):
    """
    Input the DataFrame of GIF Parcellations and values for all semiologies.
        all_combined_gifs: GIF values
            all_combined_gifs is a heatmap df i.e. from patient.get_num_datapoints_dict()  # for all data not for single semiology
            remember the cols of all_combined_gifs are "Gif Parcellations" and "pt #s"

    Returns the marginal_probabilities (row DataFrame)

    Future: As sensitivity analyses, should check the variance of marginal prob when using different filters
        concretely: marginal_p should be using all the data without filters, but then when using filters, see if we
        had used a filtered df using one of the exclusions (e.g. EZ only or based on age),
        how much would the marginal_p differ and Bayesian inference vary by?

    Alim-Marvasti Feb 2021
    """

    all_comb_gifs = all_combined_gifs.copy()

    # total of gif
    gif_total = 0
    for k,v in all_comb_gifs.items():
        gif_total += v

    # now again for the marginal probabilities
    for k,v in all_comb_gifs.items():
        all_comb_gifs[k] = v/gif_total

    # make this a DataFrame
    marginal_GIF_prob = pd.DataFrame.from_dict(all_comb_gifs, orient='index', columns=['probability'])
    return marginal_GIF_prob.T


def wrapper_marginal_L_S(publication_prior, marginal_semio_df, marginal_loc_df, Lobes, normalise=True,
                        skip_L=False):
    """ wrapper for marginal_Localisation_and_Semiology_probabilities"""
    query_results = summary_semio_loc_df_from_scripts(normalise=normalise)
    for semio, v in query_results[publication_prior].items():
        # avoid postictals as they are empty dataframes (ictal manifestations only)
        if semio.startswith('Post'):
            continue
        if semio.startswith('No Semiology'):
            continue
        # semio
        marginal_semio_df.loc[semio, 'num_query_loc'] = query_results[publication_prior][semio]['num_query_loc']
        # locs: first replace any non existing locs e.g. Hypothalamus for fear-anxiety

        marginal_loc_df = None
        if not skip_L:
            for ind_lobe in Lobes:
                try:
                    query_inspection = query_results[publication_prior][semio]['query_inspection']
                    query_inspection[ind_lobe]
                except:
                    query_inspection.loc[:, ind_lobe] = 0
            temp_df = query_inspection[Lobes]
            temp_df.fillna(0, inplace=True)
            marginal_loc_df = marginal_loc_df.add(temp_df, fill_value=0)
            marginal_loc_df.fillna(0, inplace=True)

    return marginal_semio_df, marginal_loc_df


def marginal_Localisation_and_Semiology_probabilities(df=None,
                                                    normalised=True,
                                                    global_loc_normalisation=False,
                                                    publication_prior='full',
                                                    test=False,
                                                    skip_L=False):
    """ Returns the marginal localisation and semiology probabilities

    > df (optional): preprocessed Semio2Brain DataFrame obtained from MEGA_ANALYSIS after hierarchy reversal.
        df = MEGA_ANALYSIS()  # for all-data
        also used SemioDict
        df = hierarchy_reversal()
            Assume df is the fully cleaned and hierarchy reversed Semio2Brain descriptions
            (or if not hierarchy reveresed, then top-level regions only)

        I.e. Use summary_semio_loc_df_from_scripts() to get df of semiology by localisation
            as uses top-level regions only without hierarchy_reversal.
            rows: semiologies
            columns: localisations
            can be normalised or not normalised

    > publication_prior: 'full', 'spontaneous', or 'topological'

    > global normalisation gets all the localisations, then normalises to localising values
    > normalised (micronormalisation) is the regular normalisation row by row (by semiology)

    returns:
        marginal_semio_prob: DataFrame with index of semiologies, and single column of marginal 'probability' (col df)
        marginal_loc_prob
    """
    # useful for both semio and unnormalised locs:
    Lobes = top_level_lobes(Bayesian=True)

    # make the df in the form of semiology/locs
    marginal_semio_df = pd.DataFrame()
    marginal_semio_df_long_test = pd.DataFrame()
    temp_df = pd.DataFrame()
    marginal_loc_df = pd.DataFrame()

    if normalised:
        if test==True:
        # long test semio way
            query_results = summary_semio_loc_df_from_scripts(normalise=True)
            for semio, v in query_results[publication_prior].items():
                # avoid postictals as they are empty dataframes (ictal manifestations only)
                if semio.startswith('Post'):
                    continue
                if semio.startswith('No Semiology'):
                    continue
                # for e.g. Fear-Anxiety throws a no Hypothalamus in index error so set to zero first
                for ind_lobe in Lobes:
                    try:
                        query_results[publication_prior][semio]['query_inspection'][ind_lobe]
                    except:
                        query_results[publication_prior][semio]['query_inspection'].loc[:, ind_lobe] = 0
                semio_top_level_sum = query_results[publication_prior][semio]['query_inspection'][Lobes].sum()
                marginal_semio_df_long_test.loc[semio, 'norm'] = semio_top_level_sum.sum()

        # quick semio way
        marginal_semio_df, marginal_loc_df = wrapper_marginal_L_S(publication_prior, marginal_semio_df, marginal_loc_df, Lobes, skip_L=skip_L)
        # query_results = summary_semio_loc_df_from_scripts()
        # for semio, v in query_results[publication_prior].items():
        #     # avoid postictals as they are empty dataframes (ictal manifestations only)
        #     if semio.startswith('Post'):
        #         continue
        #     if semio.startswith('No Semiology'):
        #         continue
        #     # semio
        #     marginal_semio_df.loc[semio, 'num_query_loc'] = query_results[publication_prior][semio]['num_query_loc']
        #     # locs: first replace any non existing locs e.g. Hypothalamus for fear-anxiety
        #     for ind_lobe in Lobes:
        #         try:
        #             query_results[publication_prior][semio]['query_inspection'][ind_lobe]
        #         except:
        #             query_results[publication_prior][semio]['query_inspection'].loc[:, ind_lobe] = 0
        #     temp_df = query_results[publication_prior][semio]['query_inspection'][Lobes]
        #     temp_df.fillna(0, inplace=True)
        #     marginal_loc_df = marginal_loc_df.add(temp_df, fill_value=0)
        #     marginal_loc_df.fillna(0, inplace=True)
        if test==True:
            assert_frame_equal(
                marginal_semio_df_long_test.rename(columns={'norm':'assert_test'}),
                marginal_semio_df.rename(columns={'num_query_loc':'assert_test'}),
                                        check_exact=False, check_dtype=False,
                                        rtol=0.351)

    elif not normalised:
        marginal_semio_df, marginal_loc_df = wrapper_marginal_L_S(publication_prior, marginal_semio_df, marginal_loc_df, Lobes, normalise=False, skip_L=skip_L)
        # query_results = summary_semio_loc_df_from_scripts(normalise=False)
        # for semio, v in query_results[publication_prior].items():
        #     # semio
        #     semio_top_level_sum = query_results[publication_prior][semio]['query_inspection'][Lobes].sum()
        #     marginal_semio_df.loc[semio, 'not_norm'] = semio_top_level_sum.sum()
        #     # locs
        #     temp_df = query_results[publication_prior][semio]['query_inspection'][Lobes]
        #     temp_df.fillna(0, inplace=True)
        #     marginal_loc_df = marginal_loc_df.add(temp_df, fill_value=0)
        #     marginal_loc_df.fillna(0, inplace=True)
    # for each semiology, divide by the total, to get the marginal probability of that semiology i.e.
    marginal_semio_prob = marginal_semio_df / marginal_semio_df.sum()
    marginal_semio_prob.rename(columns={'num_query_loc':'probability',
                                        'not_norm':'probability'},
                                        inplace=True, errors='ignore')


    if global_loc_normalisation:  # redo without micro normalisation first
        query_results = summary_semio_loc_df_from_scripts(normalise=False)
        for semio, v in query_results[publication_prior].items():
            temp_df = query_results[publication_prior][semio]['query_inspection'][Lobes]
            temp_df.fillna(0, inplace=True)
            temp_df, _ = normalise_top_level_localisation_cols(temp_df, Bayesian=True, Localising=marginal_semio_df.loc[semio, 'num_query_loc'])
            marginal_loc_df = (marginal_loc_df.add(temp_df, fill_value=0))
            marginal_loc_df.fillna(0, inplace=True)

    # for each loc, divide by total to get marginal probabilities
    if skip_L:
        marginal_loc_prob = None
    else:
        marginal_loc_prob = marginal_loc_df.sum(axis=0) / marginal_loc_df.sum().sum()

    return marginal_semio_prob, marginal_loc_prob


def p_GIFs(global_lateralisation=False,
           include_paeds_and_adults=True,
           include_only_postictals=False,
           symptom_laterality='NEUTRAL',
           dominance='NEUTRAL',
           hierarchy_reversal: bool =True,
           include_spontaneous_semiology: bool=False,  # TS only
           ):
    """
    Return the normalised/unnormalised marginal probabilities for each GIF parcellation.
        for ictal semiologies only (excluding postictals)

    see marginal_GIF_probabilities() for sensitivity analyses
        e.g. by adding include_concordance=False for data queries excluding concordance
            or changing laterality or age
    """

    # normalised
    patient_all_semiology_norm = Semiology(
                                            ".*",
                                            symptoms_side=Laterality.NEUTRAL,
                                            dominant_hemisphere=Laterality.NEUTRAL,
                                            include_postictals=False,
                                            include_paeds_and_adults=include_paeds_and_adults,
                                            normalise_to_localising_values=True,
                                            global_lateralisation=global_lateralisation,
                                            include_spontaneous_semiology=include_spontaneous_semiology,
                                        )

    if symptom_laterality == 'left':
        patient_all_semiology_norm.symptoms_side = Laterality.LEFT
    if dominance == 'left':
        patient_all_semiology_norm.dominant_hemisphere = Laterality.LEFT

    patient_all_semiology_norm.include_only_postictals = include_only_postictals
    patient_all_semiology_norm.granular = hierarchy_reversal
    all_combined_gifs_norm, _  = patient_all_semiology_norm.get_num_datapoints_dict()
    p_GIF_norm = marginal_GIF_probabilities(all_combined_gifs_norm)

    # now not normalised version
    patient_all_semiology_notnorm = Semiology(
                                                ".*",
                                                symptoms_side=Laterality.NEUTRAL,
                                                dominant_hemisphere=Laterality.NEUTRAL,
                                                include_postictals=False,
                                                include_paeds_and_adults=include_paeds_and_adults,
                                                normalise_to_localising_values=False,
                                                global_lateralisation=global_lateralisation,
                                            )

    if symptom_laterality == 'left':
        patient_all_semiology_notnorm.symptoms_side = Laterality.LEFT
    if dominance == 'left':
        patient_all_semiology_notnorm.dominant_hemisphere = Laterality.LEFT

    patient_all_semiology_notnorm.include_only_postictals = include_only_postictals
    patient_all_semiology_notnorm.granular = hierarchy_reversal
    all_combined_gifs_notnorm, _ = patient_all_semiology_notnorm.get_num_datapoints_dict()
    p_GIF_notnorm = marginal_GIF_probabilities(all_combined_gifs_notnorm)

    return p_GIF_norm, p_GIF_notnorm


def p_Semiology_and_Localisation(publication_prior='full', test=False, skip_L=False):
    """
    Return the normalised and unnormalised marginal probabilities for ictal semiologies.
    Returned marginal probabilities for Semiologies are pd.DataFrame; with index {Semiology} and a 'probability' column.
    Returned marginal probabilities for Localisations are pd.Series; with index {Top level lobe}.


    """
    p_S_norm, p_Loc_norm = marginal_Localisation_and_Semiology_probabilities(normalised=True, publication_prior=publication_prior, test=test, skip_L=skip_L)
    p_S_notnorm, p_Loc_notnorm = marginal_Localisation_and_Semiology_probabilities(normalised=False, publication_prior=publication_prior, test=test, skip_L=skip_L)

    return p_S_norm, p_Loc_norm, p_S_notnorm, p_Loc_notnorm
