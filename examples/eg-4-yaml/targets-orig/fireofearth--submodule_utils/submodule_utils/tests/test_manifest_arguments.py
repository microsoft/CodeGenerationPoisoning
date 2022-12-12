import os
import argparse
import yaml
import pytest
import unittest

from submodule_utils.tests import OUTPUT_DIR
from submodule_utils.arguments import (
        dir_path, file_path, dataset_origin, balance_patches_options,
        str_kv, int_kv, subtype_kv, make_dict,
        ParseKVToDictAction, CustomHelpFormatter)
from submodule_utils.manifest.arguments import (
        walk_experiment_manifest, AIMManifestArgumentManager,
        manifest_arguments)

## EXP_MANIFEST_1

EXP_MANIFEST_1 = """
try_me:
    foo: ~
    bar: baz
"""
component_id_EXP_MANIFEST_1 = 'try_me'
raw_args_EXP_MANIFEST_1 = ['--foo', '--bar', 'baz']
def create_parser_EXP_MANIFEST_1(parser):
    parser.add_argument('--foo', action='store_true')
    parser.add_argument('--bar', type=str, required=True)

def check_args_EXP_MANIFEST_1(args):
    assert args.foo is True
    assert args.bar == 'baz'

## EXP_MANIFEST_2

EXP_MANIFEST_2 = """
try_me:
    store_true_arg_1: ~
    subparser_1:
        ? store_true_arg_2
        subparser_2:
            key_str_arg: foobar
            key_list_arg:
                - 1
                - 2
                - 3
        ? store_true_arg_3
        key_int_arg_2: 2
    key_int_arg_1: 1
"""
component_id_EXP_MANIFEST_2 = 'try_me'
raw_args_EXP_MANIFEST_2 = ['--store_true_arg_1', '--key_int_arg_1', '1',
        'subparser_1', '--store_true_arg_2', '--store_true_arg_3',
        '--key_int_arg_2', '2',
        'subparser_2', '--key_str_arg', 'foobar', '--key_list_arg', '1', '2', '3']
def create_parser_EXP_MANIFEST_2(parser):
    parser.add_argument('--store_true_arg_1', action='store_true')
    parser.add_argument('--key_int_arg_1', type=int, required=False)
    subparsers_outer = parser.add_subparsers(dest='outer', required=True)
    subparser_1 = subparsers_outer.add_parser('subparser_1')
    subparser_1_other = subparsers_outer.add_parser('subparser_1_other')
    subparser_1.add_argument('--store_true_arg_2', action='store_true')
    subparser_1.add_argument('--store_true_arg_3', action='store_true')
    subparser_1.add_argument('--key_int_arg_2', type=int, required=True)
    subparser_1_other.add_argument('--not_used_1', type=int, required=True)
    subparser_1_other.add_argument('--not_used_2', type=int, required=True)
    subparsers_inner = subparser_1.add_subparsers(dest='inner', required=True)
    subparser_2 = subparsers_inner.add_parser('subparser_2')
    subparser_2_other = subparsers_inner.add_parser('subparser_2_other')
    subparser_2.add_argument('--key_str_arg', type=str, required=False)
    subparser_2.add_argument('--store_true_arg_4', action='store_true')
    subparser_2.add_argument('--key_list_arg', type=int, nargs='+', required=True)
    subparser_1_other.add_argument('--not_used_3', type=int, required=True)
    subparser_1_other.add_argument('--not_used_4', type=int, required=True)

def check_args_EXP_MANIFEST_2(args):
    assert args.store_true_arg_1 is True
    assert args.key_int_arg_1 == 1
    assert args.outer == 'subparser_1'
    assert args.store_true_arg_2 is True
    assert args.store_true_arg_3 is True
    assert args.key_int_arg_2 == 2
    assert args.inner == 'subparser_2'
    assert args.key_str_arg == 'foobar'
    assert args.store_true_arg_4 is False
    assert args.key_list_arg == [1, 2, 3]

## MOCK_MANIFEST

MOCK_MANIFEST = """
extract_annotated_patches_1:
    num_patch_loaders: 10
    use-directory:
        use-annotation:
            max_slide_patches: 10000
            annotation_location: /path/to/annotations
        slide_location: /path/to/slides
        slide_pattern: subtype/subtype

extract_annotated_patches_2:
    use-manifest:
        manifest_location: /path/to/manifest.json
        use-slide-coords:
            slide_coords_location: /path/to/coords.json

create_groups:
    seed: 256
    n_groups: 3
    subtypes:
        - EC=0
        - CC=1
        - MC=2
        - HGSC=3
        - LGSC=4
    is_binary: ~
    balance_patches: category=500
    dataset_origin: tcga
    patch_location: /path/to/patches
    patch_pattern:  subtype/slide
    filter_labels: [annotation=Tumor, patch_size=256, magnification=20]
    out_location: /path/to/patient_groups.json
    max_patient_patches: 1000

train: {}

evaluate:
    log_file_location: /path/to/training/logs/log.txt
    log_dir_location: /path/to/test/log
    ? test_shuffle
    use_log_file : ~
"""
component_id_MOCK_MANIFEST_EXTRACT_1 = 'extract_annotated_patches_1'
component_id_MOCK_MANIFEST_EXTRACT_2 = 'extract_annotated_patches_2'
component_id_MOCK_MANIFEST_GROUPS = 'create_groups'
component_id_MOCK_MANIFEST_EVALUATE = 'evaluate'
raw_args_MOCK_MANIFEST_EXTRACT_1 = ['--num_patch_loaders', '10',
        'use-directory', '--slide_location', '/path/to/slides',
        '--slide_pattern', 'subtype/subtype',
        'use-annotation', '--max_slide_patches', '10000',
        '--annotation_location', '/path/to/annotations']
raw_args_MOCK_MANIFEST_EXTRACT_2 = ['use-manifest',
        '--manifest_location', '/path/to/manifest.json',
        'use-slide-coords', '--slide_coords_location', '/path/to/coords.json']
raw_args_MOCK_MANIFEST_GROUPS = ['--seed', '256', '--n_groups', '3',
        '--subtypes', 'EC=0', 'CC=1', 'MC=2', 'HGSC=3', 'LGSC=4', '--is_binary',
        '--balance_patches', 'category=500', '--dataset_origin', 'tcga',
        '--patch_location', '/path/to/patches',
        '--patch_pattern', 'subtype/slide',
        '--filter_labels', 'annotation=Tumor', 'patch_size=256', 'magnification=20',
        '--out_location', '/path/to/patient_groups.json',
        '--max_patient_patches', '1000']
raw_args_MOCK_MANIFEST_EVALUATE = [
        '--log_file_location', '/path/to/training/logs/log.txt',
        '--log_dir_location', '/path/to/test/log', '--test_shuffle', '--use_log_file']

def create_parser_MOCK_MANIFEST_EXTRACT(parser):
    parser.add_argument('--num_patch_loaders', type=int, default=0)
    subparsers_load = parser.add_subparsers(dest='load_method', required=True)
    parser_manifest = subparsers_load.add_parser("use-manifest")
    parser_manifest_grp = parser_manifest.add_argument_group("required arguments:")
    parser_manifest_grp.add_argument("--manifest_location", type=str, required=True)
    parser_directory = subparsers_load.add_parser("use-directory")
    parser_directory_grp = parser_directory.add_argument_group("required arguments:")
    parser_directory_grp.add_argument("--slide_location", type=str, required=True)
    parser_directory.add_argument("--slide_pattern", type=str, default='subtype')
    subparsers_load_list = [parser_manifest, parser_directory]

    for subparser in subparsers_load_list:
        subparsers_extract = subparser.add_subparsers(
                dest="extract_method", required=True)
        parser_coords = subparsers_extract.add_parser("use-slide-coords")
        parser_coords_grp = parser_coords.add_argument_group("required arguments:")
        parser_coords_grp.add_argument("--slide_coords_location",
                type=str, required=True)
        parser_annotation = subparsers_extract.add_parser("use-annotation")
        parser_annotation_grp = parser_annotation.add_argument_group("required arguments:")
        parser_annotation_grp.add_argument("--annotation_location",
                type=str, required=True)
        parser_annotation.add_argument("--patch_size", type=int, default=1024)
        parser_annotation.add_argument("--resize_sizes",
                nargs='+',type=int, required=False)
        parser_annotation.add_argument("--max_slide_patches",
                type=int, required=False)

def create_parser_MOCK_MANIFEST_GROUPS(parser):
    parser.add_argument("--seed", type=int, default=256)
    parser.add_argument("--n_groups", type=int, default=3)
    parser.add_argument("--subtypes", nargs='+', type=subtype_kv,
            action=ParseKVToDictAction,
            default={'MMRD':0, 'P53ABN': 1, 'P53WT': 2, 'POLE': 3})
    parser.add_argument("--is_binary", action='store_true')
    parser.add_argument("--balance_patches",
            type=balance_patches_options, required=False)
    parser.add_argument('--dataset_origin', type=dataset_origin,
            default='ovcare')
    parser.add_argument("--patch_location", type=str, required=True)
    parser.add_argument("--patch_pattern", type=str,
            default='annotation/subtype/slide')
    parser.add_argument("--filter_labels", nargs='+', type=str_kv,
            action=ParseKVToDictAction,
            default={})
    parser.add_argument("--out_location", type=str, required=True)
    parser.add_argument("--min_patches", type=int, required=False)
    parser.add_argument("--max_patches", type=int, required=False)
    parser.add_argument("--max_patient_patches", type=int, required=False)

def create_parser_MOCK_MANIFEST_EVALUATE(parser):
    parser_grp = parser.add_argument_group("required arguments")
    parser_grp.add_argument("--log_file_location", type=str, required=True)
    parser_grp.add_argument("--log_dir_location", type=str, required=True)
    parser_grp.add_argument("----test_chunks", nargs="+", type=int, default=[2])
    parser.add_argument("--test_shuffle", action='store_true')
    parser.add_argument("--use_log_file", action='store_true')

def check_args_MOCK_MANIFEST_EXTRACT_1(args):
    assert args.num_patch_loaders == 10
    assert args.load_method == 'use-directory'
    assert args.slide_location == '/path/to/slides'
    assert args.slide_pattern == 'subtype/subtype'
    assert args.extract_method == 'use-annotation'
    assert args.patch_size == 1024
    assert args.max_slide_patches == 10000
    assert args.annotation_location == '/path/to/annotations'

def check_args_MOCK_MANIFEST_EXTRACT_2(args):
    assert args.num_patch_loaders == 0
    assert args.load_method == 'use-manifest'
    assert args.manifest_location == '/path/to/manifest.json'
    assert args.extract_method == 'use-slide-coords'
    assert args.slide_coords_location == '/path/to/coords.json'

def check_args_MOCK_MANIFEST_GROUPS(args):
    assert args.seed == 256
    assert args.n_groups == 3
    assert args.subtypes == {'EC': 0, 'CC': 1, 'MC': 2, 'HGSC': 3, 'LGSC': 4}
    assert args.is_binary is True
    assert args.balance_patches == ('category', 500)
    assert args.dataset_origin == 'tcga'
    assert args.patch_location == '/path/to/patches'
    assert args.patch_pattern == 'subtype/slide'
    assert args.filter_labels == {'annotation': 'Tumor', 'patch_size': '256', 'magnification': '20'}
    assert args.out_location == '/path/to/patient_groups.json'
    assert args.max_patient_patches == 1000

def check_args_MOCK_MANIFEST_EVALUATE(args):
    assert args.log_file_location == '/path/to/training/logs/log.txt'
    assert args.log_dir_location == '/path/to/test/log'
    assert args.test_shuffle is True
    assert args.use_log_file is True

@pytest.fixture
def mock_parser():
    return argparse.ArgumentParser()

# EXPERIMENT_MANIFEST_FILEPATH = os.path.join(output_dir, 'experiment.yaml')
TEST_PARAMETERS = [
    pytest.param(EXP_MANIFEST_1, component_id_EXP_MANIFEST_1,
            raw_args_EXP_MANIFEST_1, create_parser_EXP_MANIFEST_1,
            check_args_EXP_MANIFEST_1, id="EXP_MANIFEST_1"),
    pytest.param(EXP_MANIFEST_2, component_id_EXP_MANIFEST_2,
            raw_args_EXP_MANIFEST_2, create_parser_EXP_MANIFEST_2,
            check_args_EXP_MANIFEST_2, id="EXP_MANIFEST_2"),
    pytest.param(MOCK_MANIFEST, component_id_MOCK_MANIFEST_EXTRACT_1,
            raw_args_MOCK_MANIFEST_EXTRACT_1, create_parser_MOCK_MANIFEST_EXTRACT,
            check_args_MOCK_MANIFEST_EXTRACT_1, id="MOCK_MANIFEST_EXTRACT_1"),
    pytest.param(MOCK_MANIFEST, component_id_MOCK_MANIFEST_EXTRACT_2,
            raw_args_MOCK_MANIFEST_EXTRACT_2, create_parser_MOCK_MANIFEST_EXTRACT,
            check_args_MOCK_MANIFEST_EXTRACT_2, id="MOCK_MANIFEST_EXTRACT_2"),
    pytest.param(MOCK_MANIFEST, component_id_MOCK_MANIFEST_GROUPS,
            raw_args_MOCK_MANIFEST_GROUPS, create_parser_MOCK_MANIFEST_GROUPS,
            check_args_MOCK_MANIFEST_GROUPS, id="MOCK_MANIFEST_GROUPS"),
    pytest.param(MOCK_MANIFEST, component_id_MOCK_MANIFEST_EVALUATE,
            raw_args_MOCK_MANIFEST_EVALUATE, create_parser_MOCK_MANIFEST_EVALUATE,
            check_args_MOCK_MANIFEST_EVALUATE, id="MOCK_MANIFEST_EVALUATE")
]
@pytest.mark.parametrize(
        "yaml_str,component_id,expected_raw_args,create_parser,check_args",
        TEST_PARAMETERS)
def test_manifest_arguments(yaml_str, component_id, expected_raw_args,
        create_parser, check_args, mock_parser, output_dir):
    EXPERIMENT_MANIFEST_FILEPATH = os.path.join(output_dir, 'experiment.yaml')
    data = yaml.safe_load(yaml_str)[component_id]
    raw_args = walk_experiment_manifest(data)
    assert raw_args == expected_raw_args
    parser = mock_parser
    create_parser(parser)
    args = parser.parse_args(raw_args)
    check_args(args)
    parser = manifest_arguments()(create_parser)()
    args = parser.get_cmdline_args(argv=['from-arguments',*raw_args])
    assert args.config_method == 'from-arguments'
    check_args(args)
    with open(EXPERIMENT_MANIFEST_FILEPATH, 'w') as f:
        f.write(yaml_str)
    args = parser.get_cmdline_args(argv=[
            'from-experiment-manifest', EXPERIMENT_MANIFEST_FILEPATH,
            '--component_id', component_id])
    assert args.config_method == 'from-experiment-manifest'
    assert args.experiment_manifest_location == EXPERIMENT_MANIFEST_FILEPATH
    assert args.component_id == component_id
    args = parser.get_experiment_manifest_args(
            EXPERIMENT_MANIFEST_FILEPATH, component_id)
    check_args(args)
    args = parser.get_args(argv=[
            'from-experiment-manifest', EXPERIMENT_MANIFEST_FILEPATH,
            '--component_id', component_id])
    check_args(args)

    parser = manifest_arguments(default_component_id=component_id)(create_parser)()
    args = parser.get_cmdline_args(argv=[
            'from-experiment-manifest', EXPERIMENT_MANIFEST_FILEPATH])
    assert args.config_method == 'from-experiment-manifest'
    assert args.experiment_manifest_location == EXPERIMENT_MANIFEST_FILEPATH
    assert args.component_id == component_id
    args = parser.get_args(argv=[
            'from-experiment-manifest', EXPERIMENT_MANIFEST_FILEPATH])
    check_args(args)

def test_decorator(output_dir):
    EXPERIMENT_MANIFEST_FILEPATH = os.path.join(output_dir, 'experiment.yaml')
    EXP_MANIFEST_1 = """
    try_me:
        foo: ~
        bar: baz
    """
    component_id_EXP_MANIFEST_1 = 'try_me'
    raw_args_EXP_MANIFEST_1 = ['--foo', '--bar', 'baz']
    @manifest_arguments(default_component_id='try_me')
    def create_parser_EXP_MANIFEST_1(parser):
        parser.add_argument('--foo', action='store_true')
        parser.add_argument('--bar', type=str, required=True)

    parser = create_parser_EXP_MANIFEST_1()
    args = parser.get_args(argv=['from-arguments', *raw_args_EXP_MANIFEST_1])
    assert args.foo is True
    assert args.bar == 'baz'

    with open(EXPERIMENT_MANIFEST_FILEPATH, 'w') as f:
        f.write(EXP_MANIFEST_1)
    args = parser.get_args(argv=[
            'from-experiment-manifest', EXPERIMENT_MANIFEST_FILEPATH])
    assert args.foo is True
    assert args.bar == 'baz'
