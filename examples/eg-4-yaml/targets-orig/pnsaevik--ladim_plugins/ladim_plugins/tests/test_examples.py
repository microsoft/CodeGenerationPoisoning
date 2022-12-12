import ladim
import tempfile
import contextlib
import os
import pathlib
import yaml
import xarray as xr
import pytest
import numpy as np
import pkg_resources
from ladim_plugins import release


module_names = [
    d.name for d in pathlib.Path(__file__).parent.parent.glob('*/')
    if d.joinpath('ladim.yaml').is_file()
]


modules_with_makrel = [
    d.name for d in pathlib.Path(__file__).parent.parent.glob('*/')
    if d.joinpath('release.yaml').is_file()
]


@pytest.mark.parametrize("module_name", module_names)
def test_output_matches_snapshot(module_name):
    out = run_ladim(module_name)
    # out.to_netcdf(get_module_dir(module_name).joinpath('out.nc'))
    ref = xr.load_dataset(get_module_dir(module_name).joinpath('out.nc'))
    check_equal(out, ref)


@pytest.mark.parametrize("module_name", modules_with_makrel)
def test_makrel_matches_snapshot(module_name):
    out = run_makrel(module_name)
    ref_fname = get_module_dir(module_name).joinpath('out.rls')
    # with open(ref_fname, 'w', encoding='utf-8') as f:
    #     f.writelines(out.replace('\r', ''))
    with open(ref_fname, encoding='utf-8') as f:
        ref = f.read()

    assert out.splitlines() == ref.splitlines()


def check_equal(new, ref):
    dt = {'date': ''}
    assert {**new.attrs, **dt} == {**ref.attrs, **dt}
    assert new.variables.keys() == ref.variables.keys()
    assert new.coords.keys() == ref.coords.keys()
    assert new.data_vars.keys() == ref.data_vars.keys()
    assert new.dims.items() == ref.dims.items()

    new_dict = {k: v.values.tolist() for k, v in new.variables.items()}
    ref_dict = {k: v.values.tolist() for k, v in ref.variables.items()}
    assert new_dict == ref_dict


def run_makrel(module_name):
    package = 'ladim_plugins.' + module_name
    with pkg_resources.resource_stream(package, 'release.yaml') as config_file:
        conf = yaml.safe_load(config_file)

    import io
    buf = io.StringIO()
    release.make_release(conf, buf)
    buf.seek(0)
    return buf.read()


def run_ladim(module_name):
    # Change into a temporary folder `test_dir`
    with chdir_temp() as test_dir:
        np.random.seed(0)  # To ensure consistent results
        ladim.main(get_config(module_name))

        # Read and return output data
        return xr.load_dataset(test_dir.joinpath('out.nc'))


def get_config(module_name):
    # Load yaml config string
    package = 'ladim_plugins.' + module_name
    with pkg_resources.resource_stream(package, 'ladim.yaml') as config_file:
        config_string = config_file.read()

    # Append module dir to file names so that ladim can find the config files
    # from a different folder
    module_dir = get_module_dir(module_name)
    config_dict = yaml.safe_load(config_string)
    config_dict['files']['particle_release_file'] = os.path.join(
        module_dir, config_dict['files']['particle_release_file'])
    config_dict['gridforce']['input_file'] = os.path.join(
        module_dir, config_dict['gridforce']['input_file'])

    # Re-serialize as yaml
    import io
    buf = io.StringIO()
    yaml.safe_dump(config_dict, buf)
    buf.seek(0)
    return buf.read()


def get_module_dir(module_name):
    this_dir = pathlib.Path(__file__).parent
    package_dir = this_dir.parent
    return package_dir.joinpath(module_name)


@contextlib.contextmanager
def chdir_temp():
    tempdir = None
    try:
        tempdir = pathlib.Path(tempfile.mkdtemp(prefix='ladim_plugins_test_dir_'))
        curdir = None
        try:
            curdir = os.getcwd()
        except FileNotFoundError:
            # If current working dir does not exist (may happen in some test environments)
            pass
        
        os.chdir(tempdir)
        yield tempdir
        
        if curdir and os.path.isdir(curdir):  # curdir may be None or non-existent
            os.chdir(curdir)
            
    finally:
        try:
            if tempdir is not None:
                for fname in tempdir.glob('*'):
                    fname.unlink()
                tempdir.rmdir()

        except PermissionError:
            pass
