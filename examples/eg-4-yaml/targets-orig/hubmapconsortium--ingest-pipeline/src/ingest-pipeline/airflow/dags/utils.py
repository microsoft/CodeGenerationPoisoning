from abc import ABC, abstractmethod
from collections import namedtuple
from functools import lru_cache
import json
from os import environ, fspath, walk
from os.path import (
    basename, dirname, relpath, split, join, getsize,
    realpath, exists
)
from pathlib import Path
from pprint import pprint
import re
import shlex
import sys
import uuid
from subprocess import check_output, CalledProcessError
from typing import (
    Any, Callable, Dict, Iterable, List, Mapping, Optional,
    Pattern, Tuple, TypeVar, Union
)
from requests.exceptions import HTTPError
from requests import codes
from copy import deepcopy

import yaml
from airflow import DAG
from airflow.operators import BaseOperator
from airflow.configuration import conf as airflow_conf
from airflow.hooks.http_hook import HttpHook
from cryptography.fernet import Fernet

from hubmap_commons.schema_tools import (
    assert_json_matches_schema,
    set_schema_base_path
)
from hubmap_commons.type_client import TypeClient

import cwltool  # used to find its path


airflow_conf.read(join(environ['AIRFLOW_HOME'], 'instance', 'app.cfg'))
try:
    sys.path.append(airflow_conf.as_dict()['connections']['SRC_PATH']
                    .strip("'").strip('"'))
    from misc.tools.survey import ENDPOINTS
    sys.path.pop()
except KeyError:
    ENDPOINTS = {}


JSONType = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]

# Some functions accept a `str` or `List[str]` and return that same type
StrOrListStr = TypeVar('StrOrListStr', str, List[str])

PathStrOrList = Union[str, Path, Iterable[Union[str, Path]]]

SCHEMA_BASE_PATH = join(dirname(dirname(dirname(realpath(__file__)))),
                        'schemata')
SCHEMA_BASE_URI = 'http://schemata.hubmapconsortium.org/'

# Some constants
PIPELINE_BASE_DIR = Path(__file__).resolve().parent / 'cwl'

RE_ID_WITH_SLICES = re.compile(r'([a-zA-Z0-9\-]*)-(\d*)_(\d*)')

RE_GIT_URL_PATTERN = re.compile(r'(^git@github.com:)(.*)(\.git)')

# default maximum for number of files for which info should be returned in_line
# rather than via an alternative scratch file
MAX_IN_LINE_FILES = 500

GIT = 'git'
GIT_CLONE_COMMAND = [
    GIT,
    'clone',
    '{repository}',
]
GIT_FETCH_COMMAND = [
    GIT,
    'fetch',
]
GIT_CHECKOUT_COMMAND = [
    GIT,
    'checkout',
    '{ref}',
]
GIT_LOG_COMMAND = [
    GIT,
    'log',
    '-n1',
    '--oneline'
]
GIT_ORIGIN_COMMAND = [
    GIT,
    'config',
    '--get',
    'remote.origin.url'
]
GIT_ROOT_COMMAND = [
    GIT,
    'rev-parse',
    '--show-toplevel'
]
SHA1SUM_COMMAND = [
    'sha1sum',
    '{fname}'
]
FILE_TYPE_MATCHERS = [(r'^.*\.csv$', 'csv'),  # format is (regex, type)
                      (r'^.*\.hdf5$', 'hdf5'),
                      (r'^.*\.h5ad$', 'h5ad'),
                      (r'^.*\.pdf$', 'pdf'),
                      (r'^.*\.json$', 'json'),
                      (r'^.*\.arrow$', 'arrow'),
                      (r'(^.*\.fastq$)|(^.*\.fastq.gz$)', 'fastq'),
                      (r'(^.*\.yml$)|(^.*\.yaml$)', 'yaml')
                      ]
COMPILED_TYPE_MATCHERS: Optional[List[Tuple[Pattern, str]]] = None

"""
Lazy construction: a list of tuples (collection_type_regex, assay_type_regex, workflow)
"""
WORKFLOW_MAP_FILENAME = 'workflow_map.yml'  # Expected to be found in this same dir
WORKFLOW_MAP_SCHEMA = 'workflow_map_schema.yml'
COMPILED_WORKFLOW_MAP: Optional[List[Tuple[Pattern, Pattern, str]]] = None

"""
Lazy construction; a list of tuples (dag_id_reges, task_id_regex, {key:value})
"""
RESOURCE_MAP_FILENAME = 'resource_map.yml'  # Expected to be found in this same dir
RESOURCE_MAP_SCHEMA = 'resource_map_schema.yml'
COMPILED_RESOURCE_MAP: Optional[List[Tuple[Pattern, int, Dict[str, Any]]]] = None

TYPE_CLIENT: Optional[TypeClient] = None

# Parameters used to generate scRNA and scATAC analysis DAGs; these
# are the only fields which differ between assays and DAGs
SequencingDagParameters = namedtuple(
    'SequencingDagParameters',
    [
        'dag_id',
        'pipeline_name',
        'assay',
        'dataset_type',
    ],
)

ManifestMatch = Tuple[bool, Optional[str], Optional[str], Optional[bool]]


class FileMatcher(ABC):
    @abstractmethod
    def get_file_metadata(self, file_path: Path) -> ManifestMatch:
        """
        :return: A 3-tuple:
         [0] bool, whether to add `file_path` to a downstream index
         [1] formatted description if [0] is True, otherwise None
         [2] EDAM ontology term if [0] is True, otherwise None
        """


class PipelineFileMatcher(FileMatcher):
    # (file/directory regex, description template, EDAM ontology term)
    matchers: List[Tuple[Pattern, str, str, bool]]

    def __init__(self):
        self.matchers = []

    @classmethod
    def read_manifest(cls, pipeline_file_manifest: Path) -> Iterable[Tuple[Pattern, str, str, bool]]:
        with open(pipeline_file_manifest) as f:
            manifest = json.load(f)
            localized_assert_json_matches_schema(manifest, 'pipeline_file_manifest.yml')

        for annotation in manifest:
            pattern = re.compile(annotation['pattern'])
            is_qa_qc = annotation.get('is_qa_qc', False)
            yield pattern, annotation['description'], annotation['edam_ontology_term'], is_qa_qc

    @classmethod
    def create_from_files(cls, pipeline_file_manifests: Iterable[Path]):
        obj = cls()
        for manifest in pipeline_file_manifests:
            obj.matchers.extend(cls.read_manifest(manifest))
        return obj

    def get_file_metadata(self, file_path: Path) -> ManifestMatch:
        """
        Checks `file_path` against the list of patterns stored in this object.
        At the first match, return the associated description and ontology term.
        If no match, return `None`. Patterns are ordered in the JSON file, so
        the "first-match" behavior is deliberate.
        """
        path_str = fspath(file_path)
        for pattern, description_template, ontology_term, is_qa_qc in self.matchers:
            # TODO: walrus operator
            m = pattern.search(path_str)
            if m:
                formatted_description = description_template.format_map(m.groupdict())
                return True, formatted_description, ontology_term, is_qa_qc
        return False, None, None, None


class DummyFileMatcher(FileMatcher):
    """
    Drop-in replacement for PipelineFileMatcher which allows everything and always
    provides empty descriptions and ontology terms.
    """
    def get_file_metadata(self, file_path: Path) -> ManifestMatch:
        return True, '', '', False


class HMDAG(DAG):
    """
    A wrapper class for an Airflow DAG which applies certain defaults.
    Defaults are applied to the DAG itself, and to any Tasks added to
    the DAG.
    """
    def __init__(self, dag_id: str, **kwargs):
        """
        Provide "max_active_runs" from the lanes resource, if it is
        not already present.
        """
        if 'max_active_runs' not in kwargs:
            kwargs['max_active_runs'] = get_lanes_resource(dag_id)
        super().__init__(dag_id, **kwargs)

    def add_task(self, task: BaseOperator):
        """
        Provide "queue".  This overwrites existing data on the fly
        unless the queue specified in the resource table is None.

        TODO: because a value will be set for "queue" in BaseOperator
        based on conf.get('celery', 'default_queue') it is not easy
        to know if the creator of this task tried to override that
        default value.  One would have to monkeypatch BaseOperator
        to respect a queue specified on the task definition line.
        """
        res_queue = get_queue_resource(self.dag_id, task.task_id)
        if res_queue is not None:
            task.queue = res_queue
        super().add_task(task)

        
def find_pipeline_manifests(cwl_files: Iterable[Path]) -> List[Path]:
    """
    Constructs manifest paths from CWL files (strip '.cwl', append
    '-manifest.json'), and check whether each manifest exists. Return
    a list of `Path`s that exist on disk.
    """
    manifests = []
    for cwl_file in cwl_files:
        manifest_file = cwl_file.with_name(f'{cwl_file.stem}-manifest.json')
        if manifest_file.is_file():
            manifests.append(manifest_file)
    return manifests


def get_absolute_workflows(*workflows: Path) -> List[Path]:
    """
    :param workflows: iterable of `Path`s to CWL files, absolute
      or relative
    :return: Absolute paths to workflows: if the input paths were
      already absolute, they are returned unchanged; if relative,
      they are anchored to `PIPELINE_BASE_DIR`
    """
    return [
        PIPELINE_BASE_DIR / workflow
        for workflow in workflows
    ]


def get_named_absolute_workflows(**workflow_kwargs: Path) -> Dict[str, Path]:
    # The type hint for **workflow_kwargs looks a little odd, but
    # apparently this is how you specify that all values are of that
    # type -- the keys of that dict are necessarily strings
    """
    :param workflows: Mapping from string names to workflow Paths,
      absolute or relative
    :return: Mapping of the same strings to absolute paths to workflows:
      if the input paths were already absolute, they are returned unchanged;
      if relative, they are anchored to `PIPELINE_BASE_DIR`
    """
    return {
        name: PIPELINE_BASE_DIR / workflow
        for name, workflow in workflow_kwargs.items()
    }


def build_dataset_name(dag_id: str, pipeline_str: str, **kwargs) -> str:
    parent_submission_str = '_'.join(get_parent_dataset_uuids_list(**kwargs))
    return f'{dag_id}__{parent_submission_str}__{pipeline_str}'


def get_parent_dataset_uuids_list(**kwargs) -> List[str]:
    uuid_list = kwargs['dag_run'].conf['parent_submission_id']
    if not isinstance(uuid_list, list):
        uuid_list = [uuid_list]
    return uuid_list


def get_parent_dataset_uuid(**kwargs) -> str:
    uuid_set = set(get_parent_dataset_uuids_list(**kwargs))
    assert len(uuid_set) == 1, f"Found {len(uuid_set)} elements, expected 1"
    return uuid_set.pop()


def get_parent_dataset_paths_list(**kwargs) -> List[Path]:
    path_list = kwargs['dag_run'].conf['parent_lz_path']
    if not isinstance(path_list, list):
        path_list = [path_list]
    return [Path(p) for p in path_list]


def get_parent_dataset_path(**kwargs) -> Path:
    path_set = set(get_parent_dataset_paths_list(**kwargs))
    assert len(path_set) == 1, f"Found {len(path_set)} elements, expected 1"
    return path_set.pop()


def get_parent_data_dirs_list(**kwargs) -> List[Path]:
    """
    Build the absolute paths to the data, including the data_path offsets from
    the parent datasets' metadata
    """
    ctx = kwargs["dag_run"].conf
    data_dir_list = get_parent_dataset_paths_list(**kwargs)
    ctx_md_list = ctx["metadata"]
    if not isinstance(ctx_md_list, list):
        ctx_md_list = [ctx_md_list]
    assert len(data_dir_list) == len(ctx_md_list), "lengths of data directory and md lists do not match"
    return [Path(data_dir) / ctx_md['metadata']['data_path']
            for data_dir, ctx_md in zip(data_dir_list, ctx_md_list)]


def get_parent_data_dir(**kwargs) -> Path:
    path_set = set(get_parent_data_dirs_list(**kwargs))
    assert len(path_set) == 1, f"Found {len(path_set)} elements, expected 1"
    return path_set.pop()


def get_previous_revision_uuid(**kwargs) -> Optional[str]:
    return kwargs['dag_run'].conf.get('previous_version_uuid', None)


def get_dataset_uuid(**kwargs) -> str:
    return kwargs['ti'].xcom_pull(key='derived_dataset_uuid',
                                  task_ids="send_create_dataset")


def get_uuid_for_error(**kwargs) -> Optional[str]:
    """
    Return the uuid for the derived dataset if it exists, and of the parent dataset otherwise.
    """
    rslt = get_dataset_uuid(**kwargs)
    if rslt is None:
        rslt = get_parent_dataset_uuid(**kwargs)
    return rslt


def get_git_commits(file_list: StrOrListStr) -> StrOrListStr:
    """
    Given a list of file paths, return a list of the current short commit hashes of those files
    """
    rslt = []
    if isinstance(file_list, str):  # sadly, a str is an Iterable[str]
        file_list = [file_list]
        unroll = True
    else:
        unroll = False
    for fname in file_list:
        log_command = [piece.format(fname=fname)
                       for piece in GIT_LOG_COMMAND]
        try:
            dirnm = dirname(fname)
            if dirnm == '':
                dirnm = '.'
            line = check_output(log_command, cwd=dirnm)
        except CalledProcessError as e:
            # Git will fail if this is not running from a git repo
            line = 'DeadBeef git call failed: {}'.format(e.output)
            line = line.encode('utf-8')
        hashval = line.split()[0].strip().decode('utf-8')
        rslt.append(hashval)
    if unroll:
        return rslt[0]
    else:
        return rslt


def _convert_git_to_proper_url(raw_url: str) -> str:
    """
    If the provided string is of the form git@github.com:something.git, return
    https://github.com/something .  Otherwise just return the input string.
    """
    m = RE_GIT_URL_PATTERN.fullmatch(raw_url)
    if m:
        return f'https://github.com/{m[2]}'
    else:
        return raw_url


def get_git_origins(file_list: StrOrListStr) -> StrOrListStr:
    """
    Given a list of file paths, return a list of the git origins of those files
    """
    rslt = []
    if isinstance(file_list, str):  # sadly, a str is an Iterable[str]
        file_list = [file_list]
        unroll = True
    else:
        unroll = False
    for fname in file_list:
        command = [piece.format(fname=fname)
                   for piece in GIT_ORIGIN_COMMAND]
        try:
            dirnm = dirname(fname)
            if dirnm == '':
                dirnm = '.'
            line = check_output(command, cwd=dirnm)
        except CalledProcessError as e:
            # Git will fail if this is not running from a git repo
            line = 'https://unknown/unknown.git git call failed: {}'.format(e.output)
            line = line.encode('utf-8')
        url = line.split()[0].strip().decode('utf-8')
        url = _convert_git_to_proper_url(url)
        rslt.append(url)
    if unroll:
        return rslt[0]
    else:
        return rslt


def get_git_root_paths(file_list: Iterable[str]) -> Union[str, List[str]]:
    """
    Given a list of file paths, return a list of the root directories of the git
    working trees of the files.
    """
    rslt = []
    if isinstance(file_list, str):  # sadly, a str is an Iterable[str]
        file_list = [file_list]
        unroll = True
    else:
        unroll = False
    for fname in file_list:
        command = [piece.format(fname=fname)
                   for piece in GIT_ROOT_COMMAND]
        try:
            dirnm = dirname(fname)
            if dirnm == '':
                dirnm = '.'
            root_path = check_output(command, cwd=dirnm)
        except CalledProcessError as e:
            root_path = dirname(fname).encode('utf-8')
        rslt.append(root_path.strip().decode('utf-8'))
    if unroll:
        return rslt[0]
    else:
        return rslt


def get_git_provenance_dict(file_list: PathStrOrList) -> Mapping[str, str]:
    """
    Given a list of file paths, return a list of dicts of the form:
    
      [{<file base name>:<file commit hash>}, ...]
    """
    if isinstance(file_list, (str, Path)):  # sadly, a str is an Iterable[str]
        file_list = [file_list]
    return {basename(fname) : get_git_commits(realpath(fname))
            for fname in file_list}


def get_git_provenance_list(file_list: Iterable[str]) -> List[Mapping[str, Any]]:
    """
    Given a list of file paths, return a list of dicts of the form:
    
      [{'name':<file base name>, 'hash':<file commit hash>, 'origin':<file git origin>},...]
    """
    if isinstance(file_list, str):  # sadly, a str is an Iterable[str]
        file_list = [file_list]
    name_l = file_list
    hash_l = [get_git_commits(realpath(fname)) for fname in file_list]
    origin_l = [get_git_origins(realpath(fname)) for fname in file_list]
    root_l = get_git_root_paths(file_list)
    rel_name_l = [relpath(name, root) for name, root in zip(name_l, root_l)]
    # Make sure each repo appears only once
    repo_d = {origin: {'name': name, 'hash': hash}
              for origin, name, hash in zip(origin_l, rel_name_l, hash_l)}
    rslt = []
    for origin in repo_d:
        dct = repo_d[origin].copy()
        dct['origin'] = origin
        if not dct['name'].endswith('cwl'):
            del dct['name']  # include explicit names for workflows only
        rslt.append(dct)
    #pprint(rslt)
    return rslt


def _get_file_type(path: Path) -> str:
    """
    Given a path, guess the type of the file
    """
    global COMPILED_TYPE_MATCHERS
    if COMPILED_TYPE_MATCHERS is None:
        lst = []
        for regex, tpnm in FILE_TYPE_MATCHERS:
            lst.append((re.compile(regex), tpnm))
        COMPILED_TYPE_MATCHERS = lst
    for regex, tpnm in COMPILED_TYPE_MATCHERS:
        #print('testing ', regex, tpnm)
        if regex.match(fspath(path)):
            return tpnm
    return 'unknown'


def get_file_metadata(root_dir: str, matcher: FileMatcher) -> List[Mapping[str, Any]]:
    """
    Given a root directory, return a list of the form:
    
      [
        {
          'rel_path': <relative path>,
          'type': <file type>,
          'size': <file size>,
          'description': <human-readable file description>,
          'edam_term': <EDAM ontology term>,
          'is_qa_qc': <Boolean of whether this is a QA/QC file>,
        },
        ...
      ]
    
    containing an entry for every file below the given root directory:
    """
    root_path = Path(root_dir)
    rslt = []
    for dirpth, dirnames, fnames in walk(root_dir):
        dp = Path(dirpth)
        for fn in fnames:
            full_path = dp / fn
            relative_path = full_path.relative_to(root_path)
            add_to_index, description, ontology_term, is_qa_qc = matcher.get_file_metadata(relative_path)
            if add_to_index:
                # sha1sum disabled because of run time issues on large data collections
                #line = check_output([word.format(fname=full_path)
                #                     for word in SHA1SUM_COMMAND])
                #cs = line.split()[0].strip().decode('utf-8')
                rslt.append(
                    {
                        'rel_path': fspath(relative_path),
                        'type': _get_file_type(full_path),
                        'size': getsize(full_path),
                        'description': description,
                        'edam_term': ontology_term,
                        'is_qa_qc': is_qa_qc,
                        #'sha1sum': cs,
                    }
                )
    return rslt

def get_file_metadata_dict(
        root_dir: str,
        alt_file_dir: str,
        pipeline_file_manifests: List[Path],
        max_in_line_files: int = MAX_IN_LINE_FILES,
) -> Mapping[str, Any]:
    """
    This routine returns file metadata, either directly as JSON in the form
    {'files': [{...}, {...}, ...]} with the list returned by get_file_metadata() or the form
    {'files_info_alt_path': path} where path is the path of a unique file in alt_file_dir
    relative to the WORKFLOW_SCRATCH config parameter
    """
    if not pipeline_file_manifests:
        matcher = DummyFileMatcher()
    else:
        matcher = PipelineFileMatcher.create_from_files(pipeline_file_manifests)
    file_info = get_file_metadata(root_dir, matcher)
    if len(file_info) > max_in_line_files:
        localized_assert_json_matches_schema(file_info, 'file_info_schema.yml')
        fpath = join(alt_file_dir, '{}.json'.format(uuid.uuid4()))
        with open(fpath, 'w') as f:
            json.dump({'files': file_info}, f)
        return {'files_info_alt_path' : relpath(fpath, _get_scratch_base_path())}
    else:
        return {'files' : file_info}

def pythonop_trigger_target(**kwargs) -> None:
    """
    When used as the python_callable of a PythonOperator,this just logs
    data provided to the running DAG.
    """
    ctx = kwargs['dag_run'].conf
    run_id = kwargs['run_id']
    print('run_id: ', run_id)
    print('dag_run.conf:')
    pprint(ctx)
    print('kwargs:')
    pprint(kwargs)


def pythonop_maybe_keep(**kwargs) -> str:
    """
    accepts the following via the caller's op_kwargs:
    'next_op': the operator to call on success
    'bail_op': the operator to which to bail on failure (default 'no_keep')
    'test_op': the operator providing the success code
    'test_key': xcom key to test.  Defaults to None for return code
    """
    bail_op = kwargs['bail_op'] if 'bail_op' in kwargs else 'no_keep'
    test_op = kwargs['test_op']
    test_key = kwargs['test_key'] if 'test_key' in kwargs else None
    retcode = int(kwargs['ti'].xcom_pull(task_ids=test_op, key=test_key))
    print('%s key %s: %s\n' % (test_op, test_key, retcode))
    if retcode == 0:
        return kwargs['next_op']
    else:
        return bail_op


def get_auth_tok(**kwargs) -> str:
    """
    Recover the authorization token from the environment, and
    decrpyt it.
    """
    crypt_auth_tok = (kwargs['crypt_auth_tok'] if 'crypt_auth_tok' in kwargs
                      else kwargs['dag_run'].conf['crypt_auth_tok'])
    auth_tok = ''.join(e for e in decrypt_tok(crypt_auth_tok.encode())
                       if e.isalnum())  # strip out non-alnum characters
    return auth_tok


def pythonop_send_create_dataset(**kwargs) -> str:
    """
    Requests creation of a new dataset.  Returns dataset info via XCOM
    
    Accepts the following via the caller's op_kwargs:
    'http_conn_id' : the http connection to be used
    'parent_dataset_uuid_callable' : called with **kwargs; returns uuid
                                     of the parent of the new dataset
    'dataset_name_callable' : called with **kwargs; returns the
                              display name of the new dataset
    'previous_revision_uuid_callable': if present, called with **kwargs;
                                       returns the uuid of the previous
                                       revision of the dataset to be
                                       created or None
    either
      'dataset_types' : the types list of the new dataset
    or
      'dataset_types_callable' : called with **kwargs; returns the
                                 types list of the new dataset
    
    Returns the following via XCOM:
    (no key) : data_directory_path for the new dataset
    'derived_dataset_uuid' : uuid for the created dataset
    'group_uuid' : group uuid for the created dataset
    """

    for arg in ['parent_dataset_uuid_callable', 'http_conn_id']:
        assert arg in kwargs, "missing required argument {}".format(arg)
    for arg_options in [['dataset_types', 'dataset_types_callable']]:
        assert any([arg in kwargs for arg in arg_options])

    http_conn_id = kwargs['http_conn_id']
    ctx = kwargs['dag_run'].conf
    headers = {
        'authorization' : 'Bearer ' + get_auth_tok(**kwargs),
        'content-type' : 'application/json',
        'X-Hubmap-Application' : 'ingest-pipeline'
    }

    if 'dataset_types' in kwargs:
        dataset_types = kwargs['dataset_types']
    else:
        dataset_types = kwargs['dataset_types_callable'](**kwargs)
    if not isinstance(dataset_types, list):
        dataset_types = [dataset_types]
    canonical_types = set()  # to avoid duplicates
    contains_seq = False
    for assay_type in dataset_types:
        type_info = _get_type_client().getAssayType(assay_type)
        canonical_types.add(type_info.name)
        contains_seq |= type_info.contains_pii
    canonical_types = list(canonical_types)

    source_uuids = kwargs['parent_dataset_uuid_callable'](**kwargs)
    if not isinstance(source_uuids, list):
        source_uuids = [source_uuids]

    dataset_name = kwargs['dataset_name_callable'](**kwargs)
    
    try:
        response = HttpHook('GET', http_conn_id=http_conn_id).run(
            endpoint=f'entities/{source_uuids[0]}',
            headers=headers,
            extra_options={'check_response': False}
        )
        response.raise_for_status()
        response_json = response.json()
        if 'group_uuid' not in response_json:
            print(f'response from GET on entities{source_uuids[0]}:')
            pprint(response_json)
            raise ValueError('entities response did not contain group_uuid')
        parent_group_uuid = response_json['group_uuid']

        data = {
            "direct_ancestor_uuids": source_uuids,
            "dataset_info": dataset_name,
            "data_types": dataset_types,
            "group_uuid": parent_group_uuid,
            "contains_human_genetic_sequences": contains_seq
        }
        if 'previous_revision_uuid_callable' in kwargs:
            previous_revision_uuid = kwargs['previous_revision_uuid_callable'](**kwargs);
            if previous_revision_uuid is not None:
                data['previous_revision_uuid'] = previous_revision_uuid
        print('data for dataset creation:')
        pprint(data)
        response = HttpHook('POST', http_conn_id=http_conn_id).run(
            endpoint='datasets',
            data=json.dumps(data),
            headers=headers,
            extra_options=[]
        )
        response.raise_for_status()
        response_json = response.json()
        print('response to dataset creation:')
        pprint(response_json)
        for elt in ['uuid', 'group_uuid']:
            if elt not in response_json:
                raise ValueError(f'datasets response did not contain {elt}')
        uuid = response_json['uuid']
        group_uuid = response_json['group_uuid']
        
        response = HttpHook('GET', http_conn_id=http_conn_id).run(
            endpoint=f'datasets/{uuid}/file-system-abs-path',
            headers=headers,
            extra_options={'check_response': False}
        )
        response.raise_for_status()
        response_json = response.json()
        if 'path' not in response_json:
            print(f'response from datasets/{uuid}/file-system-abs-path:')
            pprint(response_json)
            raise ValueError(f'datasets/{uuid}/file-system-abs-path'
                             ' did not return a path')
        abs_path = response_json['path']

    except HTTPError as e:
        print(f'ERROR: {e}')
        if e.response.status_code == codes.unauthorized:
            raise RuntimeError(f'authorization for {endpoint} was rejected?')
        else:
            raise RuntimeError(f'misc error {e} on {endpoint}')
            
    kwargs['ti'].xcom_push(key='group_uuid', value=group_uuid)
    kwargs['ti'].xcom_push(key='derived_dataset_uuid', value=uuid)
    return abs_path


def pythonop_set_dataset_state(**kwargs) -> None:
    """
    Sets the status of a dataset, to 'Processing' if no specific state
    is specified.  NOTE that this routine cannot change a dataset into
    or out of the Published state.
    
    Accepts the following via the caller's op_kwargs:
    'dataset_uuid_callable' : called with **kwargs; returns the
                              uuid of the dataset to be modified
    'http_conn_id' : the http connection to be used.  Default is "entity_api_connection"
    'ds_state' : one of 'QA', 'Processing', 'Error', 'Invalid'. Default: 'Processing'
    'message' : update message, saved as dataset metadata element "pipeline_messsage".
                The default is not to save any message.
    """
    for arg in ['dataset_uuid_callable']:
        assert arg in kwargs, "missing required argument {}".format(arg)
    dataset_uuid = kwargs['dataset_uuid_callable'](**kwargs)
    http_conn_id = kwargs.get('http_conn_id', 'entity_api_connection')
    endpoint = f'/entities/{dataset_uuid}'
    ds_state = kwargs['ds_state'] if 'ds_state' in kwargs else 'Processing'
    message = kwargs.get('message', None)
    headers = {
        'authorization' : 'Bearer ' + get_auth_tok(**kwargs),
        'content-type' : 'application/json',
        'X-Hubmap-Application': 'ingest-pipeline'}
    extra_options = []

    http_hook = HttpHook('PUT',
                         http_conn_id=http_conn_id)

    data = {'status' : ds_state}
    if message is not None:
        data['pipeline_message'] = message
    print('data: ')
    pprint(data)

    response = http_hook.run(endpoint,
                             json.dumps(data),
                             headers,
                        extra_options)
    print('response: ')
    pprint(response.json())


def restructure_entity_metadata(raw_metadata: JSONType) -> JSONType:
    """
    When a dataset is initially ingested, the associated metadata is parsed and
    associated with the database representation of the dataset.  The same metadata
    is made available to workflows so that they can perform downstream processing
    on the dataset.  The copy of the metadata which is associated with the dataset
    uuid in the database is restructured to bring some important information to the
    top level.  This function attempts to un-do that restructuring to produce a
    version of the metadata as much as possible like the original.  This
    de-restructured version can be used by workflows in liu of the original.
    """
    md = {}
    if 'ingest_metadata' in raw_metadata:
        if 'metadata' in raw_metadata['ingest_metadata']:
            md['metadata'] = deepcopy(raw_metadata['ingest_metadata']['metadata'])
        if 'extra_metadata' in raw_metadata['ingest_metadata']:
            md.update(raw_metadata['ingest_metadata']['extra_metadata'])
    if 'contributors' in raw_metadata:
        md['contributors'] = deepcopy(raw_metadata['contributors'])
    if 'antibodies' in raw_metadata:
        md['antibodies'] = deepcopy(raw_metadata['antibodies'])
    #print('reconstructed metadata follows')
    #pprint(md)
    return md


def pythonop_get_dataset_state(**kwargs) -> JSONType:
    """
    Gets the status JSON structure for a dataset.  Works for Uploads as well
    as Datasets.
    
    Accepts the following via the caller's op_kwargs:
    'dataset_uuid_callable' : called with **kwargs; returns the
                              uuid of the Dataset or Upload to be examined
    """
    for arg in ['dataset_uuid_callable']:
        assert arg in kwargs, "missing required argument {}".format(arg)
    uuid = kwargs['dataset_uuid_callable'](**kwargs)
    method = 'GET'
    auth_tok = get_auth_tok(**kwargs)
    headers = {
        'authorization' : f'Bearer {auth_tok}',
        'content-type' : 'application/json',
        'X-Hubmap-Application' : 'ingest-pipeline',
        }
    http_hook = HttpHook(method, http_conn_id='ingest_api_connection')

    endpoint = f'entities/{uuid}'

    try:
        response = http_hook.run(endpoint,
                                 headers=headers,
                                 extra_options={'check_response': False})
        response.raise_for_status()
        ds_rslt = response.json()
        print('ds rslt:')
        pprint(ds_rslt)
    except HTTPError as e:
        print(f'ERROR: {e}')
        if e.response.status_code == codes.unauthorized:
            raise RuntimeError('entity database authorization was rejected?')
        else:
            print('benign error')
            return {}

    for key in ['status', 'uuid', 'entity_type']:
        assert key in ds_rslt, f"Dataset status for {uuid} has no {key}"
    if ds_rslt['entity_type'] == 'Dataset':
        assert 'data_types' in ds_rslt, f"Dataset status for {uuid} has no data_types"
        data_types = ds_rslt['data_types']
        metadata = restructure_entity_metadata(ds_rslt)
        endpoint = f"datasets/{ds_rslt['uuid']}/file-system-abs-path"
    elif ds_rslt['entity_type'] == 'Upload':
        data_types = []
        metadata = {}
        endpoint = f"uploads/{ds_rslt['uuid']}/file-system-abs-path"
    else:
        raise RuntimeError(f"Unknown entity_type {ds_rslt['entity_type']}")
    try:
        response = http_hook.run(endpoint,
                                 headers=headers,
                                 extra_options={'check_response': False})
        response.raise_for_status()
        path_query_rslt = response.json()
        print('path_query rslt:')
        pprint(path_query_rslt)
    except HTTPError as e:
        print(f'ERROR: {e}')
        if e.response.status_code == codes.unauthorized:
            raise RuntimeError('entity database authorization was rejected?')
        else:
            print('benign error')
            return {}
    assert 'path' in path_query_rslt, (f"Dataset path for {uuid} produced"
                                       " no path")
    full_path = path_query_rslt['path']

    rslt = {
        'entity_type': ds_rslt['entity_type'],
        'status': ds_rslt['status'],
        'uuid': ds_rslt['uuid'],
        'data_types': data_types,
        'local_directory_full_path': full_path,
        'metadata': metadata,
    }

    if ds_rslt['entity_type'] == 'Dataset':
        http_hook = HttpHook('GET', http_conn_id='entity_api_connection')
        endpoint = f"datasets/{ds_rslt['uuid']}/organs"
        try:
            response = http_hook.run(endpoint,
                                     headers=headers,
                                     extra_options={'check_response': False})
            response.raise_for_status()
            organs_query_rslt = response.json()
            print('organs_query_rslt:')
            pprint(organs_query_rslt)
            rslt['organs'] = [entry['organ'] for entry in organs_query_rslt]
        except HTTPError as e:
            print(f'ERROR: {e}')
            if e.response.status_code == codes.unauthorized:
                raise RuntimeError('entity database authorization was rejected?')
            else:
                print('benign error')
                return {}
        
    return rslt


def _uuid_lookup(uuid, **kwargs):
    http_conn_id = 'uuid_api_connection'
    endpoint = 'hmuuid/{}'.format(uuid)
    method = 'GET'
    headers = {'authorization' : 'Bearer ' + get_auth_tok(**kwargs)}
#     print('headers:')
#     pprint(headers)
    extra_options = []

    http_hook = HttpHook(method,
                         http_conn_id=http_conn_id)

    response = http_hook.run(endpoint,
                             None,
                             headers,
                             extra_options)
#     print('response: ')
#     pprint(response.json())
    return response.json()


def _generate_slices(id: str) -> Iterable[str]:
    mo = RE_ID_WITH_SLICES.fullmatch(id)
    if mo:
        base, lidx, hidx = mo.groups()
        lidx = int(lidx)
        hidx = int(hidx)
        for idx in range(lidx, hidx+1):
            yield f'{base}-{idx}'
    else:
        yield id


def assert_id_known(id: str, **kwargs) -> None:
    """
    Is the given id string known to the uuid database?  Id strings with suffixes like
    myidstr-n1_n2 where n1 and n2 are integers are interpreted as representing multiple
    ids with suffix integers in the range n1 to n2 inclusive.
    
    Raises AssertionError if the ID is not known.
    """
    for slice in _generate_slices(id):
        tissue_info = _uuid_lookup(slice, **kwargs)
        assert tissue_info and len(tissue_info) >= 1, f'tissue_id {slice} not found on lookup'


def pythonop_md_consistency_tests(**kwargs) -> int:
    """
    Perform simple consistency checks of the metadata stored as YAML in kwargs['metadata_fname'].
    This includes accessing the UUID api via its Airflow connection ID to verify uuids.
    """
    md_path = join(get_tmp_dir_path(kwargs['run_id']), kwargs['metadata_fname'])
    if exists(md_path):
        with open(md_path, 'r') as f:
            md = yaml.safe_load(f)
    #     print('metadata from {} follows:'.format(md_path))
    #     pprint(md)
        if '_from_metadatatsv' in md and md['_from_metadatatsv']:
            try:
                for elt in ['tissue_id', 'donor_id']:
                    assert elt in md, 'metadata is missing {}'.format(elt)
                assert md['tissue_id'].startswith(md['donor_id']+'-'), 'tissue_id does not match'
                assert_id_known(md['tissue_id'], **kwargs)
                return 0
            except AssertionError as e:
                kwargs['ti'].xcom_push(key='err_msg',
                                       value='Assertion Failed: {}'.format(e))
                return 1
        else:
            return 0
    else:
            kwargs['ti'].xcom_push(key='err_msg',
                                   value='Expected metadata file is missing')
            return 1
        

def _get_scratch_base_path() -> Path:
    dct = airflow_conf.as_dict(display_sensitive=True)['connections']
    if 'WORKFLOW_SCRATCH' in dct:
        scratch_path = dct['WORKFLOW_SCRATCH']
    elif 'workflow_scratch' in dct:
        # support for lower case is necessary setting the scratch path via the
        # environment variable AIRFLOW__CONNECTIONS__WORKFLOW_SCRATCH
        scratch_path = dct['workflow_scratch']
    else:
        raise KeyError('WORKFLOW_SCRATCH')  # preserve original code behavior
    scratch_path = scratch_path.strip("'").strip('"')  # remove quotes that may be on the string
    return Path(scratch_path)


def get_tmp_dir_path(run_id: str) -> Path:
    """
    Given the run_id, return the path to the dag run's scratch directory
    """
    return _get_scratch_base_path() / run_id


@lru_cache(maxsize=1)
def get_cwltool_bin_path() -> Path:
    """
    Returns the full path to the cwltool binary
    """
    cwltool_dir = dirname(cwltool.__file__)
    while cwltool_dir:
        part1, part2 = split(cwltool_dir)
        cwltool_dir = part1
        if part2 == 'lib':
            break
    assert cwltool_dir, 'Failed to find cwltool bin directory'
    cwltool_dir = Path(cwltool_dir, 'bin')
    return cwltool_dir


def get_cwltool_base_cmd(tmpdir: Path) -> List[str]:
    return [
        'env',
        'TMPDIR={}'.format(tmpdir),
        'cwltool',
        '--timestamps',
        # The trailing slashes in the next two lines are deliberate.
        # cwltool treats these path prefixes as *strings*, not as
        # directories in which new temporary dirs should be created, so
        # a path prefix of '/tmp/cwl-tmp' will cause cwltool to use paths
        # like '/tmp/cwl-tmpXXXXXXXX' with 'XXXXXXXX' as a random string.
        # Adding the trailing slash is ensures that temporary directories
        # are created as *subdirectories* of 'cwl-tmp' and 'cwl-out-tmp'.
        '--tmpdir-prefix={}/'.format(tmpdir / 'cwl-tmp'),
        '--tmp-outdir-prefix={}/'.format(tmpdir / 'cwl-out-tmp'),
    ]

def make_send_status_msg_function(
        dag_file: str,
        retcode_ops: List[str],
        cwl_workflows: List[Path],
        http_conn_id: str = 'ingest_api_connection',
        uuid_src_task_id: str = 'send_create_dataset',
        dataset_uuid_fun: Optional[Callable[..., str]] = None,
        dataset_lz_path_fun: Optional[Callable[..., str]] = None,
        metadata_fun: Optional[Callable[..., dict]] = None,
        include_file_metadata: Optional[bool] = True
) -> Callable[..., None]:
    """
    The function which is generated by this function will return a boolean,
    True if the message which was ultimately sent was for a success and
    False otherwise.  This return value is not necessary in most circumstances
    but is useful when the generated function is being wrapped.

    The user can specify dataset_uuid_fun and dataset_lz_path_fun, or leave
    both to their empty default values and specify 'uuid_src_task_id'.

    `dag_file` should always be `__file__` wherever this function is used,
    to include the DAG file in the provenance. This could be "automated" with
    something like `sys._getframe(1).f_code.co_filename`, but that doesn't
    seem worth it at the moment

    'http_conn_id' is the Airflow connection id associated with the /datasets/status service.

    'dataset_uuid_fun' is a function which returns the uuid of the dataset to be
    updated, or None.  If given, it will be called with **kwargs arguments.

    'dataset_lz_path_fun' is a function which returns the full path of the dataset 
    data directory, or None.  If given, it will be called with **kwargs arguments.
    If the return value of this callable is None or the empty string, no file metadata
    will be ultimately be included in the status message.

    'uuid_src_task_id' is the Airflow task_id of a task providing the uuid via 
    the XCOM key 'derived_dataset_uuid' and the dataset data directory
    via the None key.  This is used only if dataset_uuid is None or dataset_lz_path 
    is None.

    'metadata_fun' is a function which returns additional metadata in JSON form,
    or None.  If given, it will be called with **kwargs arguments.  This function
    will only be evaluated if retcode_ops have all returned 0.

    'include_file_metadata is a boolean defaulting to True which indicates whether
    file metadata should be included in the transmitted metadata structure.  If False,
    no file metadata will be included.  Note that file metadata may also be excluded
    based on the return value of 'dataset_lz_path_fun' above.
    """
    def send_status_msg(**kwargs) -> bool:
        retcodes = [
            kwargs['ti'].xcom_pull(task_ids=op)
            for op in retcode_ops
        ]
        retcodes = [int(rc or '0') for rc in retcodes]
        print('retcodes: ', {k: v for k, v in zip(retcode_ops, retcodes)})
        success = all(rc == 0 for rc in retcodes)
        if dataset_uuid_fun is None:
            dataset_uuid = kwargs['ti'].xcom_pull(
                key='derived_dataset_uuid',
                task_ids=uuid_src_task_id,
            )
        else:
            dataset_uuid = dataset_uuid_fun(**kwargs)
        if dataset_lz_path_fun is None:
            ds_dir = kwargs['ti'].xcom_pull(task_ids=uuid_src_task_id)
        else:
            ds_dir = dataset_lz_path_fun(**kwargs)
        endpoint = '/datasets/status'
        method = 'PUT'
        headers = {
            'authorization': 'Bearer ' + get_auth_tok(**kwargs),
            'content-type': 'application/json',
        }
        extra_options = []
        return_status = True  # mark false on failure

        http_hook = HttpHook(method, http_conn_id=http_conn_id)

        if success:
            md = {}
            files_for_provenance = [dag_file, *cwl_workflows]

            if 'dag_provenance' in kwargs['dag_run'].conf:
                md['dag_provenance'] = kwargs['dag_run'].conf['dag_provenance'].copy()
                new_prv_dct = get_git_provenance_dict(files_for_provenance)
                md['dag_provenance'].update(new_prv_dct)
            else:
                dag_prv = (kwargs['dag_run'].conf['dag_provenance_list']
                           if 'dag_provenance_list' in kwargs['dag_run'].conf
                           else [])
                dag_prv.extend(get_git_provenance_list(files_for_provenance))
                md['dag_provenance_list'] = dag_prv

            if metadata_fun:
                md['metadata'] = metadata_fun(**kwargs)
                
            if dataset_lz_path_fun:
                dataset_dir_abs_path = dataset_lz_path_fun(**kwargs)
                if dataset_dir_abs_path:
                    #########################################################################
                    # Added by Zhou 6/16/2021 for registering thumbnail image
                    # This is the only place that uses this hardcoded extras/thumbnail.jpg
                    thumbnail_file_abs_path = join(dataset_dir_abs_path,
                                                   'extras/thumbnail.jpg')
                    if exists(thumbnail_file_abs_path):
                        md['thumbnail_file_abs_path'] = thumbnail_file_abs_path
                    #########################################################################

            manifest_files = find_pipeline_manifests(cwl_workflows)
            if include_file_metadata and ds_dir is not None and not ds_dir == '':
                md.update(
                    get_file_metadata_dict(
                        ds_dir,
                        get_tmp_dir_path(kwargs['run_id']),
                        manifest_files,
                    ),
                )
            try:
                assert_json_matches_schema(md, 'dataset_metadata_schema.yml')
                data = {
                    'dataset_id': dataset_uuid,
                    'status': 'QA',
                    'message': 'the process ran',
                    'metadata': md,
                }
            except AssertionError as e:
                print('invalid metadata follows:')
                pprint(md)
                data = {
                    'dataset_id': dataset_uuid,
                    'status': 'Error',
                    'message': 'internal error; schema violation: {}'.format(e),
                    'metadata': {},
                }
                return_status = False
        else:
            log_fname = Path(get_tmp_dir_path(kwargs['run_id']), 'session.log')
            with open(log_fname, 'r') as f:
                err_txt = '\n'.join(f.readlines())
            data = {
                'dataset_id': dataset_uuid,
                'status': 'Invalid',
                'message': err_txt,
            }
            return_status = False
        print('data: ')
        pprint(data)

        response = http_hook.run(
            endpoint,
            json.dumps(data),
            headers,
            extra_options,
        )
        print('response: ')
        pprint(response.json())

        return return_status

    return send_status_msg


def map_queue_name(raw_queue_name: str) -> str:
    """
    If the configuration contains QUEUE_NAME_TEMPLATE, use it to customize the
    provided queue name.  This allows job separation under Celery.
    """
    conf_dict = airflow_conf.as_dict()
    if 'QUEUE_NAME_TEMPLATE' in conf_dict.get('connections', {}):
        template = conf_dict['connections']['QUEUE_NAME_TEMPLATE']
        template = template.strip("'").strip('"')  # remove quotes that may be on the config string
        rslt = template.format(raw_queue_name)
        return rslt
    else:
        return raw_queue_name

def create_dataset_state_error_callback(dataset_uuid_callable: Callable[[Any], str]) -> Callable[[Mapping, Any],
                                                                                                 None]:
    def set_dataset_state_error(contextDict: Mapping, **kwargs) -> None:
        """
        This routine is meant to be
        """
        msg = 'An internal error occurred in the {} workflow step {}'.format(contextDict['dag'].dag_id,
                                                                             contextDict['task'].task_id)
        new_kwargs = kwargs.copy()
        new_kwargs.update(contextDict)
        new_kwargs.update({'dataset_uuid_callable' : dataset_uuid_callable,
                           'http_conn_id' : 'ingest_api_connection',
                           'ds_state' : 'Error',
                           'message' : msg
                           })
        pythonop_set_dataset_state(**new_kwargs)
    return set_dataset_state_error


set_schema_base_path(SCHEMA_BASE_PATH, SCHEMA_BASE_URI)

def localized_assert_json_matches_schema(jsn: JSONType, schemafile: str) -> None:
    """
    This version of assert_json_matches_schema knows where to find schemata used by this module
    """
    try:
        return assert_json_matches_schema(jsn, schemafile)  # localized by set_schema_base_path
    except AssertionError as e:
        print('ASSERTION FAILED: {}'.format(e))
        raise


def _get_workflow_map() -> List[Tuple[Pattern, Pattern, str]]:
    """
    Lazy compilation of workflow map
    """
    global COMPILED_WORKFLOW_MAP
    if COMPILED_WORKFLOW_MAP is None:
        map_path = join(dirname(__file__), WORKFLOW_MAP_FILENAME)
        with open(map_path, 'r') as f:
            map = yaml.safe_load(f)
        localized_assert_json_matches_schema(map, WORKFLOW_MAP_SCHEMA)
        cmp_map = []
        for dct in map['workflow_map']:
            ct_re = re.compile(dct['collection_type'])
            at_re = re.compile(dct['assay_type'])
            cmp_map.append((ct_re, at_re, dct['workflow']))
        COMPILED_WORKFLOW_MAP = cmp_map
    return COMPILED_WORKFLOW_MAP


def _get_resource_map() -> List[Tuple[Pattern, Pattern, Dict[str, str]]]:
    """
    Lazy compilation of resource map
    """
    global COMPILED_RESOURCE_MAP
    if COMPILED_RESOURCE_MAP is None:
        map_path = join(dirname(__file__), RESOURCE_MAP_FILENAME)
        with open(map_path, 'r') as f:
            map = yaml.safe_load(f)
        localized_assert_json_matches_schema(map, RESOURCE_MAP_SCHEMA)
        cmp_map = []
        for dct in map['resource_map']:
            dag_re = re.compile(dct['dag_re'])
            dag_dct = {key: dct[key] for key in dct
                       if key not in ['dag_re', 'tasks']}
            tasks = []
            for inner_dct in dct['tasks']:
                assert 'task_re' in inner_dct, ('schema should guarantee'
                                                ' "task_re" is present?')
                task_re = re.compile(inner_dct['task_re'])
                task_dct = {key: inner_dct[key] for key in inner_dct
                            if key not in ['task_re']}
                tasks.append((task_re, task_dct))
            cmp_map.append((dag_re, dag_dct, tasks))
        COMPILED_RESOURCE_MAP = cmp_map
    return COMPILED_RESOURCE_MAP


def _lookup_resource_record(dag_id: str,
                            task_id: Optional[str] = None) -> Tuple[int, Dict]:
    """
    Look up the resource map entry for the given dag_id and task_id. The first
    match is returned.  If the task_id is None, the first record matching only
    the dag_id is returned and only the information which is not task_id-specific
    is included.
    """
    for dag_re, dag_dict, task_list in _get_resource_map():
        if dag_re.match(dag_id):
            rslt = dag_dict.copy()
            if task_id is not None:
                for task_re, task_dict in task_list:
                    if task_re.match(task_id):
                        rslt.update(task_dict)
                        break
                else:
                    raise ValueError(f'Resource map entry for dag_id <{dag_id}>'
                                     f' has no match for task_id <{task_id}>')
            return rslt
    else:
        raise ValueError('No resource map entry found for'
                         f' dag_id <{dag_id}> task_id <{task_id}>')

    
def get_queue_resource(dag_id: str, task_id: Optional[str] = None) -> str:
    """
    Look up the queue defined for this dag_id and task_id in the current
    resource map.  If the task_id is None, the lookup is done with 
    task_id='__default__', which presumably only matches the wildcard case.  
    """
    if task_id is None:
        task_id = '__default__'
    rec = _lookup_resource_record(dag_id, task_id)
    assert 'queue' in rec, 'schema should guarantee "queue" is present?'
    return map_queue_name(rec['queue'])


def get_lanes_resource(dag_id: str) -> int:
    """
    Look up the number of lanes defined for this dag_id in the current
    resource map.
    """
    rec = _lookup_resource_record(dag_id)
    assert 'lanes' in rec, 'schema should guarantee "lanes" is present?'
    return int(rec['lanes'])


def get_preserve_scratch_resource(dag_id: str) -> bool:
    """
    Look up the number of lanes defined for this dag_id in the current
    resource map.
    """
    rec = _lookup_resource_record(dag_id)
    assert 'preserve_scratch' in rec, ('schema should guarantee'
                                       ' "preserve_scratch" is present?')
    return bool(rec['preserve_scratch'])


def get_threads_resource(dag_id: str, task_id: Optional[str] = None) -> int:
    """
    Look up the number of threads defined for this dag_id and task_id in
    the current resource map.  If the task_id is None, the lookup is done
    with task_id='__default__', which presumably only matches the wildcard
    case.  
    """
    if task_id is None:
        task_id = '__default__'
    rec = _lookup_resource_record(dag_id, task_id)
    assert 'threads' in rec, 'schema should guarantee "threads" is present?'
    return int(rec['threads'])


def get_type_client() -> TypeClient:
    """
    Expose the type client instance publicly
    """
    return _get_type_client()


def _get_type_client() -> TypeClient:
    """
    Lazy initialization of the global TypeClient instance
    """
    global TYPE_CLIENT
    if TYPE_CLIENT is None:
        conn = HttpHook.get_connection('search_api_connection')
        if conn.port is None:
            url = f'{conn.conn_type}://{conn.host}'
        else:
            url = f'{conn.conn_type}://{conn.host}:{conn.port}'
        TYPE_CLIENT = TypeClient(url)
    return TYPE_CLIENT


def _canonicalize_assay_type_if_possible(assay_type: StrOrListStr) -> StrOrListStr:
    """
    Attempt to look up the the assay type (or each element if it is a list) and
    return the canonical version.
    """
    if isinstance(assay_type, list):
        return [_canonicalize_assay_type_if_possible(elt) for elt in assay_type]
    else:
        try:
            type_info = _get_type_client().getAssayType(assay_type)
            assay_type = type_info.name
        except Exception:
            pass
        return assay_type


def downstream_workflow_iter(collectiontype: str, assay_type: StrOrListStr) -> Iterable[str]:
    """
    Returns an iterator over zero or more workflow names matching the given
    collectiontype and assay_type.  Each workflow name is expected to correspond to
    a known workflow, e.g. an Airflow DAG implemented by workflow_name.py .
    """
    collectiontype = collectiontype or ''
    assay_type = _canonicalize_assay_type_if_possible(assay_type)
    assay_type = assay_type or ''
    for ct_re, at_re, workflow in _get_workflow_map():
        if isinstance(assay_type, str):
            at_match = at_re.match(assay_type)
        else:
            at_match = all(at_re.match(elt) for elt in assay_type)
        if ct_re.match(collectiontype) and at_match:
            yield workflow


def encrypt_tok(cleartext_tok: str) -> bytes:
    key = airflow_conf.as_dict(display_sensitive=True)['core']['fernet_key']
    fernet = Fernet(key.encode())
    return fernet.encrypt(cleartext_tok.encode())


def decrypt_tok(crypt_tok: bytes) -> str:
    key = airflow_conf.as_dict(display_sensitive=True)['core']['fernet_key']
    fernet = Fernet(key.encode())
    return fernet.decrypt(crypt_tok).decode()


def join_quote_command_str(pieces: List[Any]):
    command_str = ' '.join(shlex.quote(str(piece)) for piece in pieces)
    print('final command_str:', command_str)
    return command_str


def _strip_url(url):
    return url.split(':')[1].strip('/')


def find_matching_endpoint(host_url: str)-> str:
    """
    Find the identity of the 'instance' of Airflow infrastructure based
    on environment information.
    
    host_url: the URL of entity-api in the current context

    returns: an instance string, for example 'PROD' or 'DEV'
    """
    assert ENDPOINTS, "Context information is unavailable"
    stripped_url = _strip_url(host_url)
    print(f'stripped_url: {stripped_url}')
    candidates = [ep for ep in ENDPOINTS
                  if stripped_url == _strip_url(ENDPOINTS[ep]['entity_url'])]
    assert len(candidates) == 1, f'Found {candidates}, expected 1 match'
    return candidates[0]



def main():
    """
    This provides some unit tests.  To run it, you will need to define the
    'search_api_connection' connection ID and the Fernet key.  The easiest way
    to do that is with something like:
    
      export AIRFLOW_CONN_SEARCH_API_CONNECTION='https://search.api.hubmapconsortium.org/
      fernet_key=`python -c 'from cryptography.fernet import Fernet ; print(Fernet.generate_key().decode())'`
      export AIRFLOW__CORE__FERNET_KEY=${fernet_key}
    """
    print(__file__)
    print(get_git_commits([__file__]))
    print(get_git_provenance_dict(__file__))
    dirnm = dirname(__file__)
    if dirnm == '':
        dirnm = '.'
    for elt in get_file_metadata(dirnm, DummyFileMatcher()):
        print(elt)
    pprint(get_git_provenance_list(__file__))
    md = {'metadata' : {'my_string' : 'hello world'},
          'files' : get_file_metadata(dirnm, DummyFileMatcher()),
          'dag_provenance_list' : get_git_provenance_list(__file__)}
    try:
        localized_assert_json_matches_schema(md, 'dataset_metadata_schema.yml')
        print('ASSERT passed')
    except AssertionError as e:
        print('ASSERT failed')

    assay_pairs = [('devtest', 'devtest'), ('codex', 'CODEX'),
                   ('codex', 'SOMEOTHER'), ('someother', 'CODEX'),
                   ('someother', 'salmon_sn_rnaseq_10x'), ('someother', 'salmon_rnaseq_10x_sn')]
    for collectiontype, assay_type in assay_pairs:
        print('collectiontype {}, assay_type {}:'.format(collectiontype, assay_type))
        for elt in downstream_workflow_iter(collectiontype, assay_type):
            print('  -> {}'.format(elt))

    print(f'cwltool bin path: {get_cwltool_bin_path()}')

    s = 'hello world'
    crypt_s = encrypt_tok(s)
    s2 = decrypt_tok(crypt_s)
    print('crypto test: {} -> {} -> {}'.format(s, crypt_s, s2))


if __name__ == "__main__":
    main()
