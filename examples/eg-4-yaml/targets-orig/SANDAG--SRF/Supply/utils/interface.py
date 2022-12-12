from __future__ import print_function
import os
import sys
import shutil
import yaml
import matplotlib.pyplot as plt
from simpledbf import Dbf5
import psycopg2
import pandas
from envyaml import EnvYAML


def load_yaml(filename):
    with open(filename, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as error:
            print(error)
    return None


def create_folder_if_needed(folder):
    """
        returns true if folder needed to be created
    """
    if os.path.isdir(folder):
        return False
    else:
        os.mkdir(folder)
        return True


def empty_folder(folder):
    # trying to avoid emptying an important folder by accident
    # if the folder name is somewhat reasonable, go ahead and empty it.
    if not create_folder_if_needed(folder):
        if folder != os.getcwd() and \
                (folder.__contains__('out') or folder.__contains__('temp')):
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print('Failed to delete %s. Reason: %s' %
                          (file_path, e))
                    return 1
            return 0
        else:
            if "do_not_empty" not in folder:
                print('Did not empty folder \"{}\", check parameter naming'
                      .format(folder))
            return 2


def save_to_file(printable, output_directory, filename,
                 as_yaml=False, output_status=True, force=False):
    if(output_status):
        print('saving {} to {} folder'.format(filename, output_directory))
    filepath = os.path.join(output_directory, filename)
    if(os.path.isfile(filepath) and not force):
        if(output_status):
            print('file exists, skipping')
        return
    create_folder_if_needed(output_directory)
    # use pandas to_csv function if available
    if hasattr(printable, 'to_csv'):
        printable.to_csv(filepath, index=False)
    else:
        if as_yaml:
            printable = yaml.dump(printable)
        print(printable, file=open(filepath, 'w'), end='')
    if(output_status):
        print('saved')




def plot_data(data, output_dir='data/output', image_name='plot.png'):
    plt.plot(data, 'ro')
    plt.savefig(os.path.join(output_dir, image_name))
    plt.close()

input_filename = "data/SRF_Input_Base_V4.1.csv"
sites_filename = "data/Sites_MGRAs.dbf"


schema = "srf"
database_info_filename = "../dbparams.yaml"
input_table = "_supply_input"
scheduled_development_table = "_supply_scheduled_sites"

def open_dbf(filepath):
    dbf = Dbf5(filepath)
    return dbf.to_dataframe()


def open_sites_file(from_database=True):
    if from_database:
        return open_database_file(
            schema, scheduled_development_table
        )
    else:
        return open_dbf(sites_filename)


def connect_to_db(db_param_filename):
    # Set up database connection
    connection_info = EnvYAML(db_param_filename)
    return psycopg2.connect(
        database=connection_info['database'],
        host=connection_info['host'],
        port=connection_info['port'],
        user=connection_info['user'],
        password=connection_info['password'])


def open_database_file(schema, table):
    print('connecting to database...')
    with connect_to_db(
        database_info_filename
    ) as connection:
        print(connection)
        sql_statement = 'select * from {}.\"{}\"'.format(
            schema,
            table
        )
        print(sql_statement)
        print('reading from database...')
        return pandas.read_sql(sql_statement, connection)


def extract_csv_from_database(schema, table, output_dir, filename):
    dataframe = open_database_file(schema, table)
    save_to_file(dataframe, output_dir, filename)


def open_mgra_io_file(from_database=False, filename=None):
    if from_database:
        return open_database_file(
        schema, input_table)
    elif filename is not None:  # load from file
        return pandas.read_csv(filename)
    else:
        print('could not load file')