import os
import shutil
import subprocess

import pandas as pd
from oemof.tools.logger import define_logging
from pandas.testing import assert_frame_equal
import yaml


def setup_logging(log_path):
    define_logging(logpath=log_path, logfile="oemoflex.log")


def load_yaml(file_path):
    with open(file_path, "r") as yaml_file:
        yaml_data = yaml.safe_load(yaml_file)

    return yaml_data


def read_csv_file(filepath):
    r"""
    Reads a CSV file into a DataFrame. Considers some codes for NA values.

    (FlexMex-specific function)

    Parameters
    ----------
    filepath : str
        Path to the CSV file

    Returns
    -------
    DataFrame
    """

    dataframe = pd.read_csv(
        filepath,
        header=0,
        na_values=["not considered", "no value"],
        sep=",",
        encoding="unicode_escape",  # for TimeSeries.csv (ISO-8859-1 encoded)
    )

    return dataframe


def read_scalar_input_data(path_to_dir, experiment_name, identifier_columns=None):
    r"""
    Reads all CSV files resembling a Scalars.csv file and concatenates them into a DataFrame.
    No check for duplicates.

    (FlexMex-specific function)

    Parameters
    ----------
    path : str
        Path to the CSV-file-containing directory.

    experiment_name : str
        File name part to pre-filter the files (e.g. 'FlexMex1' or 'FlexMex2')
        TODO: Necessary as long as FlexMex "Data_In" contains two versions of Scalars.csv

    identifier_columns : str
        List of column names to filter the proper type of CSV file

    Returns
    -------
    DataFrame
    """

    if identifier_columns is None:
        identifier_columns = [
            "Scenario",
            "Region",
            "Year",
            "Parameter",
            "Unit",
            "Value",
        ]

    def is_scalars_data(df):
        r"""
        Checks if 'df' has a number of indentifier columns that show it as a
        FlexMex Scalars.csv input file.
        """
        return set(identifier_columns).issubset(df.columns)

    scalars_df = pd.DataFrame()

    for filepath in find_csv_filenames(path_to_dir, pattern=experiment_name):
        next_csv_df = read_csv_file(filepath)
        if is_scalars_data(next_csv_df):
            scalars_df = pd.concat([scalars_df, next_csv_df])

    return scalars_df


def find_csv_filenames(path_to_dir, pattern, suffix=".csv"):
    r"""
    Reads all CSV (or other) files in a directory (non-recursive)

    TODO: 'pattern' necessary as long as FlexMex "Data_In" contains two versions of Scalars.csv
    """
    filenames = os.listdir(path_to_dir)

    csv_filepaths = []
    for filename in filenames:
        if filename.endswith(suffix) and pattern in filename:
            csv_filepaths.append(os.path.join(path_to_dir, filename))

    return csv_filepaths


def has_duplicates(df, columns):
    r"""
    Checks DataFrame for duplicates in a given column subset.
    """
    duplicates = df.duplicated(columns)

    if any(duplicates):
        return True

    return False


def filter_scalar_input_data(scalars_in, scenario_select, scenario_overwrite):
    r"""
    Updates Scalars.csv DataFrame to contain only scenario-specific values of parameters.

    Needed to properly process Scalars.csv rows starting with something like 'FlexMex1UC2'.

    (FlexMex-specific function)

    Parameters
    ----------
    scalars_in : pandas.DataFrame
        Scalars.csv DataFrame from input data

    scenario_select : list of str
        'Scenario' values of parameters to keep, drop everything else

    scenario_overwrite : list of str
        'Scenario' values who's parameter values will overwrite those in 'scenario_select'

    Returns
    -------
    Scalars.csv DataFrame
    """

    scalars = scalars_in.copy()

    scalars_overwrite = scalars_in.copy()

    scalars_overwrite = scalars_overwrite.loc[
        scalars_overwrite["Scenario"] == scenario_overwrite
    ]

    scalars = scalars.loc[scalars["Scenario"].isin(scenario_select), :]

    # Save column order before setting and resetting index
    columns = scalars.columns

    scalars.set_index(["Region", "Parameter"], inplace=True)

    scalars_overwrite.set_index(["Region", "Parameter"], inplace=True)

    scalars.update(scalars_overwrite)

    scalars = scalars.reset_index()

    # Restore column order
    scalars = scalars[columns]

    return scalars


def load_scalar_input_data(scenario_specs, path_to_input_data):
    r"""
    Reads, filters and checks FlexMex Scalars.csv input data

    (FlexMex-specific function)

    Parameters
    ----------
    scenario_specs : dict
        Special dict with scenario settings

    path_to_input_data : str
        Path to scalar input data

    Returns
    -------
    Scalars.csv DataFrame
    """

    # Get experiment name - necessary as long as "Data_In" contains two versions of Scalars.csv
    experiment_name = scenario_specs["scenario"].split("_")[0]

    # Load common input parameters
    scalars = read_scalar_input_data(path_to_input_data, experiment_name)

    # Filter out only scenario-related input parameters
    scalars = filter_scalar_input_data(
        scalars,
        scenario_select=scenario_specs["scenario_select"],
        scenario_overwrite=scenario_specs["scenario_overwrite"],
    )

    # After filtering there musn't be any duplicates left.
    if has_duplicates(scalars, ["Scenario", "Region", "Parameter"]):
        raise ValueError(
            "Found duplicates in Scalars data. Check input data and filtering."
        )

    return scalars


def get_all_file_paths(dir):
    r"""
    Finds all paths of files in a directory.

    Parameters
    ----------
    dir : str
        Directory

    Returns
    -------
    file_paths : list
        list of str
    """
    # pylint: disable=unused-variable
    file_paths = []
    for dir_path, dir_names, file_names in os.walk(dir):
        for file_name in file_names:
            file_paths.append(os.path.join(dir_path, file_name))

    return file_paths


def check_if_csv_files_equal(csv_file_a, csv_file_b):
    r"""
    Compares two csv files.

    Parameters
    ----------
    csv_file_a
    csv_file_b

    """
    df1 = pd.read_csv(csv_file_a)
    df2 = pd.read_csv(csv_file_b)

    assert_frame_equal(df1, df2)


def check_if_csv_dirs_equal(dir_a, dir_b):
    r"""
    Compares the csv files in two directories and asserts that
    they are equal.

    The function asserts that:

    1. The file names of csv files found in the directories are the same.
    2. The file contents are the same.

    Parameters
    ----------
    dir_a : str
        Path to first directory containing csv files

    dir_b : str
        Path to second directory containing csv files

    """
    files_a = get_all_file_paths(dir_a)
    files_b = get_all_file_paths(dir_b)

    files_a = [file for file in files_a if file.split(".")[-1] == "csv"]
    files_b = [file for file in files_b if file.split(".")[-1] == "csv"]

    files_a.sort()
    files_b.sort()

    f_names_a = [os.path.split(f)[-1] for f in files_a]
    f_names_b = [os.path.split(f)[-1] for f in files_b]

    diff = list(set(f_names_a).symmetric_difference(set(f_names_b)))

    assert not diff, f"Lists of filenames are not the same." f" The diff is: {diff}"

    for file_a, file_b in zip(files_a, files_b):
        try:
            check_if_csv_files_equal(file_a, file_b)
        except AssertionError:
            diff.append([file_a, file_b])

    if diff:
        error_message = ""
        for pair in diff:
            short_name_a, short_name_b = (
                os.path.join(*f.split(os.sep)[-4:]) for f in pair
            )
            line = " - " + short_name_a + " and " + short_name_b + "\n"
            error_message += line

        raise AssertionError(
            f" The contents of these file are different:\n{error_message}"
        )


def get_dir_diff(dir_a, dir_b, ignore_list=None):
    r"""
    Diff's two directories recursively and returns stdout or stderr

    Parameters
    ----------
    dir_a   Directory left-hand side
    dir_b   Directory right-hand side
    ignore_list  list of patterns to ignore in file names, default: .log

    Returns
    -------
    the STDOUT string of the 'diff' system call
    """

    if ignore_list is None:
        ignore_list = ["*.log"]

    # Concatenate patterns to a list of diff args of the form "-x PATTERN"
    exclusions = []
    for pattern in ignore_list:
        # Different from a terminal call, it doesn't work with quotes here:
        # -x "*.log" OR -x '*.log' won't work!
        exclusions.append("-x")
        exclusions.append("{}".format(pattern))

    # Set working directory to the common path for the diff output to be trimmed to what is relevant
    working_directory = os.path.commonpath([dir_a, dir_b])

    # Trim directory path names accordingly to the relative paths
    rel_dir_a = os.path.relpath(dir_a, working_directory)
    rel_dir_b = os.path.relpath(dir_b, working_directory)

    # Call 'diff' recursively (-r), with brief output (-b), ignore exclusion patterns (-x),
    # with relative path names, instead of capture_output=True combine STDOUT and STDERR into one
    diff_process = subprocess.run(
        ["diff", "-rq", *exclusions, rel_dir_a, rel_dir_b],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=working_directory,
        check=False,
    )

    return diff_process.stdout.decode("UTF-8")


def delete_empty_subdirs(path):
    r"""Deletes empty subdirectories in path"""
    while True:
        to_delete = []
        for root, dirs, _ in os.walk(path):
            for d in dirs:
                full_path = os.path.join(root, d)
                if not os.listdir(full_path):
                    to_delete.append(full_path)

        if to_delete:
            for p in to_delete:
                shutil.rmtree(p)
        else:
            break


def get_name_path_dict(dir):
    r"""
    Returns a dictionary with all the csv files in
    a given directory as keys and their paths as
    values.

    Parameters
    ----------
    dir : path

    Returns
    -------
    name_path_dict : dict
    """
    name_path_dict = {
        file.split(".")[0]: os.path.join(dir, file)
        for file in os.listdir(dir)
        if file.endswith(".csv")
    }

    return name_path_dict


def load_elements(dir):
    r"""

    Parameters
    ----------
    dir : path

    Returns
    -------
    name_dataframe_dict : dict
    """
    name_path_dict = get_name_path_dict(dir)

    name_dataframe_dict = {}
    for name, path in name_path_dict.items():
        name_dataframe_dict[name] = pd.read_csv(path)

    return name_dataframe_dict
