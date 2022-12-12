from scipy.sparse import save_npz, load_npz
from scipy.sparse import csr_matrix
from tqdm import tqdm

import ast
import numpy as np
import os
import pandas as pd
import pickle
import stat
import yaml


def save_dataframe_csv(df, path, name):
    df.to_csv(path+name, index=False)


def load_dataframe_csv(path, name=None, delimiter=None, names=None):
    if not name:
        return pd.read_csv(path, delimiter=delimiter, names=names)
    else:
        return pd.read_csv(path+name, delimiter=delimiter, names=names)


def save_dataframe_latex(df, path, model):
    with open('{0}{1}_parameter_tuning.tex'.format(path, model), 'w') as handle:
        handle.write(df.to_latex(index=False))


def save_numpy(matrix, path, model):
    save_npz('{0}{1}'.format(path, model), matrix)


def save_array(array, path, model):
    np.save('{0}{1}'.format(path, model), array)


def load_numpy(path, name):
    return load_npz(path+name).tocsr()


def load_pandas(path, name, row_name='userId', col_name='movieId',
                value_name='rating', shape=(138494, 131263), sep=','):
    df = pd.read_csv(path + name, sep=sep)
    rows = df[row_name]
    cols = df[col_name]
    if value_name is not None:
        values = df[value_name]
    else:
        values = [1]*len(rows)

    return csr_matrix((values, (rows, cols)), shape=shape)


def load_csv(path, name, shape=(1010000, 2262292)):
    data = np.genfromtxt(path + name, delimiter=',')
    matrix = csr_matrix((data[:, 2], (data[:, 0], data[:, 1])), shape=shape)
    save_npz(path + "rating.npz", matrix)
    return matrix


def load_pandas_without_names(path, name, row_name='userId', col_name='movieId',
                value_name='rating', shape=(138494, 131263), sep=',', names=['userId', 'trackId', 'rating']):
    df = pd.read_csv(path + name, sep=sep, header=None, names=names)
    rows = df[row_name]
    cols = df[col_name]
    if value_name is not None:
        values = df[value_name]
    else:
        values = [1]*len(rows)

    index = np.where(cols >= 0)[0]
    rows = rows[index]
    cols = cols[index]
    values = values[index]
    return csr_matrix((values, (rows, cols)), shape=shape)


def load_netflix(path, shape=(2649430, 17771)):
    # Cautious: This function will reindex the user-item IDs, only for experiment usage
    frames = []
    print("Load Files")
    for file in tqdm(os.listdir(path)):
        if file.endswith(".txt"):
            movie_path = os.path.join(path, file)
            with open(movie_path) as f:
                movie_index = f.readline().split(':')[0]
            df = pd.read_csv(movie_path, skiprows=1, header=None, names=['userID', 'rating', 'timestamp'])
            df['movieId'] = int(movie_index)
            frames.append(df)

    df = pd.concat(frames)
    ratings = df['rating']
    rows = df['userID']
    cols = df['movieId']
    timestamps = df['timestamp']
    tqdm.pandas()
    print("Transform timestamps")
    timestamps = timestamps.str.replace('-', '').progress_apply(int)
    print("Create Sparse Matrices")
    return csr_matrix((ratings, (rows, cols)), shape=shape), csr_matrix((timestamps, (rows, cols)), shape=shape)


def save_pickle(path, name, data):
    with open('{0}/{1}.pickle'.format(path, name), 'wb') as handle:
        pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)


def load_pickle(path, name):
    with open('{0}/{1}.pickle'.format(path, name), 'rb') as handle:
        data = pickle.load(handle)

    return data


def load_yaml(path, key='parameters'):
    with open(path, 'r') as stream:
        try:
            return yaml.load(stream, Loader=yaml.FullLoader)[key]
        except yaml.YAMLError as exc:
            print(exc)

def find_best_hyperparameters(folder_path, metric):
    csv_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path)
                 if os.path.isfile(os.path.join(folder_path, f)) and f.endswith('.csv')]
    best_settings = []
    for record in csv_files:
        df = pd.read_csv(record)
        # import ipdb; ipdb.set_trace()
        df[metric+'_Score'] = df[metric].map(lambda x: ast.literal_eval(x)[0])
        best_settings.append(df.loc[df[metric+'_Score'].idxmax()].to_dict())

    df = pd.DataFrame(best_settings)

    if any(df['model'].duplicated()):
        df = df.groupby('model', group_keys=False).apply(lambda x: x.loc[x[metric+'_Score'].idxmax()]).reset_index(drop=True)

    df = df.drop(metric+'_Score', axis=1)

    return df

def get_file_names(folder_path, extension='.yml'):
    return [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and f.endswith(extension)]


def write_file(folder_path, file_name, content, exe=False):
    full_path = folder_path+'/'+file_name
    with open(full_path, 'w') as the_file:
        the_file.write(content)

    if exe:
        st = os.stat(full_path)
        os.chmod(full_path, st.st_mode | stat.S_IEXEC)