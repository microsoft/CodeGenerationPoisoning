import sys
import collections
import shutil
import re
import pickle
import subprocess as sp
import warnings
import difflib
from pathlib import Path
from typing import Iterable, List, Union, Dict, Tuple, Optional, Sequence

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

import yaml
import git

# pylint: disable=no-name-in-module
from tensorflow.python.summary.summary_iterator import summary_iterator

StrOrPath = Union[str, Path]


class MetaWriter():
    def __init__(
            self,
            repo_roots: Union[Iterable[StrOrPath], StrOrPath],
            files: Union[Iterable[StrOrPath], StrOrPath],
            print_log_dir: bool = True,
            symlink_dir: str = "."):

        def _to_list_of_paths(var: Union[Iterable[StrOrPath], StrOrPath]) \
                -> List[Path]:
            var_list = [var] if isinstance(repo_roots, (str, Path)) else var
            return [Path(v) for v in var_list]  # type: ignore

        roots = _to_list_of_paths(repo_roots)
        self.files = _to_list_of_paths(files)
        self.symlink_dir = Path(symlink_dir).expanduser()

        self.requirements = sp.check_output(
            ['pip3', 'freeze']).decode(encoding='UTF-8')

        self.print_log_dir = print_log_dir

        self.cmd = " ".join(sys.argv)

        self.git_info = {}
        for repo_root in roots:
            repo = git.Repo(repo_root,
                            search_parent_directories=True)
            diff = sp.check_output(
                ['git', 'diff'], cwd=repo.working_dir).decode(encoding='UTF-8')

            self.git_info[Path(repo.working_dir).stem] = {
                'repo_dir': repo.working_dir,
                'commit': repo.commit().name_rev,
                'diff': diff}

    def write(self, logdir: str) -> None:
        if self.print_log_dir:
            print(f'log dir: {logdir}')

        if self.symlink_dir:
            link_tgt = self.symlink_dir / 'latest'
            try:
                # can add missing_ok in python 3.8
                link_tgt.unlink()
            except FileNotFoundError:
                pass
            link_tgt.symlink_to(logdir, target_is_directory=True)

        meta_dir = Path(logdir) / 'meta'
        meta_dir.mkdir(exist_ok=True)

        for fname in self.files:
            shutil.copy2(fname, meta_dir)

        with open(meta_dir / 'args.txt', 'w') as f:
            f.write(self.cmd)

        with open(meta_dir / 'requirements.txt', 'w') as f:
            f.write(self.requirements)

        for repo_name in self.git_info:
            commit = self.git_info[repo_name]['commit']
            commit_only = commit.split(" ")[0]
            repo_dir = self.git_info[repo_name]['repo_dir']

            meta_repo_dir = meta_dir / repo_name
            meta_repo_dir.mkdir(exist_ok=True)

            with open(meta_repo_dir / (repo_name + '_commit.txt'), 'w') as f:
                f.write(commit)

            code = [
                "import subprocess as sp",
                f"repo_dir = '{repo_dir}'",
                f"print('stashing changes in {repo_dir}')",
                "sp.call(['git', 'stash'], cwd=repo_dir)",
                f"sp.call(['git', 'checkout', '{commit_only}'], cwd=repo_dir)",
            ]

            if self.git_info[repo_name]['diff']:
                diff_file = meta_repo_dir / (repo_name + '_diff.diff')
                with open(diff_file, 'w') as f:
                    f.write(self.git_info[repo_name]['diff'])
                code.append(
                    (f"sp.call(['git', 'apply', '{diff_file.resolve()}'], "
                     "cwd=repo_dir)"))

            with open(meta_repo_dir / (repo_name + '_restore.py'), 'w') as f:
                f.write("\n".join(code))


def find_filepath(
        fname: StrOrPath,
        search_dirs: Union[StrOrPath, Iterable[StrOrPath]]) \
        -> Path:
    fname_path = Path(fname)
    if fname_path.exists():
        # absolute path or relative
        return fname_path
    else:
        # relative to search_dirs
        if isinstance(search_dirs, (str, Path)):
            search_dirs = [search_dirs]

        try:
            paths = next(
                list(Path(d).rglob(fname_path.name))
                for d in search_dirs)  # type: ignore
            if not paths:  # pylint: disable=no-else-raise
                raise FileNotFoundError(
                    f'could not find {fname} in {search_dirs}')
            else:
                return paths[0]
        except StopIteration as e:
            print(f'could not find {fname}')
            raise e


def get_inputs(
        yaml_file: StrOrPath,
        search_dirs: Union[StrOrPath, Iterable[StrOrPath]]) \
        -> List[Path]:

    inputs = []

    def _get_inputs(fname: StrOrPath) -> None:
        filepath = find_filepath(fname, search_dirs)
        with open(filepath, 'r') as f:
            params = yaml.safe_load(f)

        for inp in params.get('__inputs__', []):
            _get_inputs(inp)

        inputs.append(filepath)

    _get_inputs(yaml_file)
    return inputs


def parse_inputs(inputs: Iterable[StrOrPath]) -> dict:
    # note that importing ray.tune does not override tf.executing_eagerly
    # pylint: disable=import-outside-toplevel
    from ray.tune.utils import merge_dicts

    out: dict = {}
    for inp in inputs:
        with open(inp, 'r') as f:
            params = yaml.safe_load(f)

        out = merge_dicts(out, params)

    return out


def get_latest_checkpoint(ckpt_root_dir: str) -> str:
    ckpts = [str(c) for c in Path(ckpt_root_dir).rglob('*checkpoint-*')
             if 'meta' not in str(c)]
    r = re.compile(r'checkpoint_(\d+)')
    ckpt_nums = [int(r.search(c).group(1)) for c in ckpts]  # type: ignore
    return ckpts[np.argmax(ckpt_nums)]


def get_log_dir(log_params: Dict[str, str],
                yaml_fname: StrOrPath,
                exp_name: str) \
        -> Path:
    prefix = next((Path(d).expanduser() for d in log_params['prefixes']
                   if Path(d).expanduser().is_dir()))
    return prefix / log_params['exp_group'] / Path(yaml_fname).stem / exp_name


def tensorboard_data(
        fname: Union[str, Path], tag: str, max_step: Optional[int] = None) \
        -> Tuple[List[int], List[float]]:
    values = []
    step_nums = []
    # print('reading ', fname)
    tags = set()

    for e in summary_iterator(str(fname)):

        if max_step and e.step > max_step:
            break

        for v in e.summary.value:
            tags.add(v.tag)
            # print(v.tag)
            if v.tag == tag:
                step_nums.append(e.step)
                values.append(v.simple_value)

    if not values:
        suggestions = difflib.get_close_matches(tag, tags, n=3)
        if not suggestions:
            suggestions = tags  # type: ignore
        warnings.warn("no data found in {}, you may have meant {}".format(
            fname, suggestions))

    return step_nums, values


def _merge_dfs(_dfs: Sequence[pd.DataFrame]) -> pd.DataFrame:
    _df = _dfs[0]
    if len(_dfs) > 1:
        for i, __df in enumerate(_dfs[1:]):
            _df = _df.join(__df, how='outer', rsuffix=f'_{i+1}')
        cols = [f'values_{i}' for i in range(len(_dfs))]
        _df.columns = cols
    return _df


def shorten_dfs(_dfs: Sequence[pd.DataFrame]) -> None:
    shortest_max_step = min([_df.index.max() for _df in _dfs])
    for i, _df in enumerate(_dfs):
        _dfs[i] = _df[_df.index <= shortest_max_step]  # type: ignore


def find_tb_fnames(base_dir: str) -> List[List[Path]]:
    tb_fnames = Path(base_dir).rglob('events.out.tfevents*')
    tb_grouped_fnames: dict = collections.defaultdict(list)
    for f in tb_fnames:
        tb_grouped_fnames[f.parent].append(f)

    return list(tb_grouped_fnames.values())


def tb_to_df(
        tb_fnames: Iterable[Iterable[Path]],
        tag: str,
        max_step: Optional[int],
        only_complete_data: bool) -> pd.DataFrame:

    all_dfs = []
    for tb_group in tb_fnames:
        if isinstance(tb_group, (Path, str)):
            tb_group = [tb_group]

        # get the data
        data = [tensorboard_data(f, tag, max_step) for f in tb_group]
        dfs = [pd.DataFrame({'values': v, 'steps': s}).set_index('steps')
               for s, v in data]
        df = _merge_dfs(dfs)
        if len(df.columns) > 1:
            cols = df.columns
            df['values'] = df.mean(axis=1)
            df = df.drop(cols, axis=1)
        all_dfs.append(df)

    if only_complete_data:
        shorten_dfs(all_dfs)

    return _merge_dfs(all_dfs)


def plot_percentiles(
        ax: plt.axis, df: pd.DataFrame, percentiles: Tuple[float, float],
        alpha: float) -> None:

    assert 0 <= alpha <= 1

    assert len(percentiles) == 2 and \
        0 <= percentiles[0] <= 1 and \
        0 <= percentiles[1] <= 1, "percentiles must be between 0 and 1"

    pct_low = df.quantile(percentiles[0], axis=1)
    pct_high = df.quantile(percentiles[1], axis=1)
    ax.fill_between(df.index, pct_low, pct_high, alpha=alpha)


def filter_tensorboard_values(values: Sequence[float], smoothing: float) \
        -> List[float]:
    # https://stackoverflow.com/a/49357445
    smoothed = []
    smoothed.append(values[0])
    for v in values[1:]:
        smoothed.append(smoothed[-1] * smoothing + v * (1 - smoothing))

    return smoothed


def plot_smoothed(
        ax: plt.axis,
        timesteps: Iterable[int],
        values: Sequence[float], smoothed_values: float,
        label: str,
        alpha: float = 0.2) \
        -> None:
    line = ax.plot(timesteps, smoothed_values, label=label)[0]
    clr = line.get_color()
    ax.plot(timesteps, values, color=clr, alpha=alpha)


def plot_tensorboard(
        ax: plt.axis,
        tag: str,
        tb_data: Iterable[Iterable[Iterable[Path]]],
        names: Iterable[str],
        percentiles: Optional[Tuple[float, float]] = (0.25, 0.75),
        alpha: float = 0.1,
        use_data_cache: bool = False,
        data_cache_fname: str = ".rlgear_data.p",
        show_same_num_timesteps: bool = False,
        max_step: Optional[int] = None) -> None:

    if use_data_cache:
        with open(data_cache_fname, 'rb') as f:
            out_dfs = pickle.load(f)
    else:
        out_dfs = []
        for grouped_files in tb_data:
            out_dfs.append(tb_to_df(
                grouped_files,
                tag, max_step=max_step, only_complete_data=True))

        with open(data_cache_fname, 'wb') as f:
            pickle.dump(out_dfs, f)

    if show_same_num_timesteps:
        shorten_dfs(out_dfs)

    for name, df in zip(names, out_dfs):
        ax.plot(df.index, df.mean(axis=1), label=name)

        if percentiles:
            plot_percentiles(ax, df, percentiles, alpha)

    # https://stackoverflow.com/a/25750438
    ax.xaxis.set_major_formatter(mtick.FormatStrFormatter('%.1e'))
    ax.set_xlabel('Training Step')
    plt.tight_layout()
