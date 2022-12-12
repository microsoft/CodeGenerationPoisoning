# coding: utf-8
"""Test dtool integration.

To see verbose logging during testing, run something like

    import logging
    import unittest
    from imteksimfw.fireworks.user_objects.firetasks.tests.test_recover_tasks import RecoverTasksTest
    logging.basicConfig(level=logging.DEBUG)
    suite = unittest.TestSuite()
    suite.addTest(RecoverTasksTest('test_do_nothing'))
    runner = unittest.TextTestRunner()
    runner.run(suite)
"""
__author__ = 'Johannes Laurin Hoermann'
__copyright__ = 'Copyright 2020, IMTEK Simulation, University of Freiburg'
__email__ = 'johannes.hoermann@imtek.uni-freiburg.de, johannes.laurin@gmail.com'
__date__ = 'Aug 11, 2020'

import glob
import json
import logging
import os
import sys
import tempfile
import unittest

# needs dtool cli for verification
# import subprocess  # TODO: replace cli sub-processes with custom verify calls

from fireworks.core.firework import Firework, Workflow
from fireworks.user_objects.firetasks.script_task import PyTask
from imteksimfw.fireworks.user_objects.firetasks.recover_tasks import RecoverTask, dict_merge

module_dir = os.path.abspath(os.path.dirname(__file__))


def _log_nested_dict(dct):
    logger = logging.getLogger(__name__)
    for l in json.dumps(dct, indent=2, default=str).splitlines():
        logger.debug(l)


def _read_json(file):
    with open(file, 'r') as stream:
        return json.load(stream)


# def _read_yaml(file):
#     with open(file, 'r') as stream:
#         return yaml.safe_load(stream)


def _inject(source, injection, marker):
    """Inserts values into nested dicts at positions marked by marker."""
    logger = logging.getLogger(__name__)
    if isinstance(marker, dict):
        for k, v in marker.items():
            if isinstance(v, str):  # str in marker marks desired mapping
                # inject here
                logger.debug(
                    "'{}' from injection[{}] overrides '{}' in source[{}]."
                        .format(injection[v], v, source[k], k))
                source[k] = injection[v]
            else:
                # descend
                logger.debug("Descending into sub-tree '{}' of '{}'.".format(
                    source[k], source))
                source[k] = _inject(source[k], injection, marker[k])
    elif isinstance(marker, list):  # source and marker must have same length
        logger.debug("Branching into element wise sub-trees of '{}'.".format(
            source))
        source = [_inject(s, injection, m) for s, m in zip(source, marker)]
    else:  # nothing to be done for this key
        logger.debug("No injection desired at '{}'.".format(source))

    return source


def _compare(source, target, marker):
    """Compare source and target partially, as marked by marker."""
    # ret = True
    logger = logging.getLogger(__name__)
    if isinstance(marker, dict):
        for k, v in marker.items():
            if k not in source:
                logger.error("{} not in source '{}'.".format(k, source))
                return False
            if k not in target:
                logger.error("{} not in target '{}'.".format(k, source))
                return False

            logger.debug("Descending into sub-tree '{}' of '{}'.".format(
                source[k], source))
            # descend
            if not _compare(source[k], target[k], v):
                return False  # one failed comparison suffices

    # source, target and marker must have same length:
    elif isinstance(marker, list):
        logger.debug("Branching into element wise sub-trees of '{}'.".format(
            source))
        for s, t, m in zip(source, target, marker):
            if not _compare(s, t, m):
                return False  # one failed comparison suffices
    else:  # arrived at leaf, comparison desired?
        if marker is not False:  # yes
            logger.debug("Comparing '{}' == '{}' -> {}.".format(
                source, target, source == target))
            return source == target

    # comparison either not desired or successfull for all elements
    return True


def _log_dir(directory=os.curdir):
    """Log content of directory subtree."""
    logger = logging.getLogger(__name__)
    for root, dirs, files in os.walk(directory, topdown=True):
        for name in files:
            logger.debug(os.path.join(root, name))
        for name in dirs:
            logger.debug(os.path.join(root, name))


def _get_dummy_restart_wf():
    # +-----------------+     +-----------------+     +------------------+
    # | restart_wf root | --> | restart_wf body | --> | restart_wf leafs |
    # +-----------------+     +-----------------+     +------------------+
    dummy_ft = PyTask(func='print', args=['I am a dummy task'])
    restart_root_fw = Firework([dummy_ft], name='restart_wf root')
    restart_body_fw = Firework([dummy_ft], name='restart_wf body', parents=[restart_root_fw])
    restart_leaf_fw = Firework([dummy_ft], name='restart_wf leaf', parents=[restart_body_fw])
    restart_wf = Workflow([restart_root_fw, restart_body_fw, restart_leaf_fw])
    return restart_wf


def _get_dummy_addition_wf():
    # +------------------+     +------------------+     +-------------------+
    # | addition_wf root | --> | addition_wf body | --> | addition_wf leafs |
    # +------------------+     +------------------+     +-------------------+
    dummy_ft = PyTask(func='print', args=['I am a dummy task'])
    addition_root_fw = Firework([dummy_ft], name='addition_wf root')
    addition_body_fw = Firework([dummy_ft], name='addition_wf body', parents=[addition_root_fw])
    addition_leaf_fw = Firework([dummy_ft], name='addition_wf leaf', parents=[addition_body_fw])
    addition_wf = Workflow([addition_root_fw, addition_body_fw, addition_leaf_fw])
    return addition_wf


def _get_dummy_detour_wf():
    # +----------------+     +----------------+     +-----------------+
    # | detour_wf root | --> | detour_wf body | --> | detour_wf leafs |
    # +----------------+     +----------------+     +-----------------+
    dummy_ft = PyTask(func='print', args=['I am a dummy task'])
    detour_root_fw = Firework([dummy_ft], name='detour_wf root')
    detour_body_fw = Firework([dummy_ft], name='detour_wf body', parents=[detour_root_fw])
    detour_leaf_fw = Firework([dummy_ft], name='detour_wf leaf', parents=[detour_body_fw])
    detour_wf = Workflow([detour_root_fw, detour_body_fw, detour_leaf_fw])
    return detour_wf


class RecoverTasksTest(unittest.TestCase):

    def _assert_restart_wf_topology(self, wf, root_fw_id):
        self.assertEqual(wf.id_fw[root_fw_id].name, 'restart_wf root')
        root_fw_children = wf.links[root_fw_id]

        self.assertEqual(len(root_fw_children), 1)
        body_fw_id = root_fw_children[0]
        self.assertEqual(wf.id_fw[body_fw_id].name, 'restart_wf body')

        self.assertEqual(len(wf.links[body_fw_id]), 1)
        leaf_fw_id = wf.links[body_fw_id][0]
        self.assertEqual(wf.id_fw[leaf_fw_id].name, 'restart_wf leaf')

        return leaf_fw_id

    def _assert_addition_wf_topology(self, wf, root_fw_id):
        self.assertEqual(wf.id_fw[root_fw_id].name, 'addition_wf root')
        root_fw_children = wf.links[root_fw_id]

        self.assertEqual(len(root_fw_children), 1)
        body_fw_id = root_fw_children[0]
        self.assertEqual(wf.id_fw[body_fw_id].name, 'addition_wf body')

        self.assertEqual(len(wf.links[body_fw_id]), 1)
        leaf_fw_id = wf.links[body_fw_id][0]
        self.assertEqual(wf.id_fw[leaf_fw_id].name, 'addition_wf leaf')

        return leaf_fw_id

    def _assert_detour_wf_topology(self, wf, root_fw_id):
        self.assertEqual(wf.id_fw[root_fw_id].name, 'detour_wf root')
        root_fw_children = wf.links[root_fw_id]

        self.assertEqual(len(root_fw_children), 1)
        body_fw_id = root_fw_children[0]
        self.assertEqual(wf.id_fw[body_fw_id].name, 'detour_wf body')

        self.assertEqual(len(wf.links[body_fw_id]), 1)
        leaf_fw_id = wf.links[body_fw_id][0]
        self.assertEqual(wf.id_fw[leaf_fw_id].name, 'detour_wf leaf')

        return leaf_fw_id

    def setUp(self):
        dummy_ft = PyTask(func='print', args=['I am a dummy task'])
        dummy_fw = Firework([dummy_ft], name='dummy_fw')
        dummy_wf = Workflow([dummy_fw])

        self.default_restart_wf_dict = dummy_wf.to_dict()

        self.default_task_spec = {
            'loglevel': logging.DEBUG,
            'store_stdlog': True,
            'stored_data': True,
        }

        self.default_fw_spec = {}

        self._tmpdir = tempfile.TemporaryDirectory()
        self._previous_working_directory = os.getcwd()

        os.chdir(self._tmpdir.name)

    def tearDown(self):
        os.chdir(self._previous_working_directory)
        self._tmpdir.cleanup()

    def test_ignore_missing_restart_file(self):
        """Will run a recovery task that does nothing."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        task_spec = {
            'restart_wf': self.default_restart_wf_dict,
            'fizzle_on_no_restart_file': False,
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_job_info': [{
                'launch_dir': os.curdir,
                'name': 'dummy parent',
                'fw_id': 1,
            }]
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)

        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())
        additions = fw_action.additions
        # detours = fw_action.detours

        self.assertEqual(additions, [])

    def test_increase_custom_restart_counter(self):
        """Will run a recovery task and check for an increased restart counter."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        task_spec = {
            'restart_wf': self.default_restart_wf_dict,
            'fizzle_on_no_restart_file': False,
            'restart_counter': 'nested->deeply_nested->restart_count',
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_fizzled_parents': [{
                'launch_dir': os.curdir,
                'name': 'dummy parent',
                'fw_id': 1,
                'spec': {
                    'nested': {'deeply_nested': {'restart_count': 2}},
                },
                'launches': [
                    {'launch_dir': './does/not/exist'}
                ]
            }]
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)

        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())

        detours = fw_action.detours[0]
        for fws in detours.fws:
            self.assertIn('nested',  fws.spec)
            self.assertIn('deeply_nested',  fws.spec["nested"])
            self.assertIn('restart_count',  fws.spec["nested"]["deeply_nested"])
            self.assertEqual(fws.spec["nested"]["deeply_nested"]["restart_count"], 3)

    def test_fizzle_on_no_restart_file(self):
        """Will run a recovery task that fizzles on no restart file."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        task_spec = {
            'restart_wf': self.default_restart_wf_dict,
            'fizzle_on_no_restart_file': True,
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_job_info': [{
                'launch_dir': os.curdir,
                'name': 'dummy parent',
                'fw_id': 1,
            }]
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)
        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))

        with self.assertRaises(ValueError) as cm:
            fw_action = t.run_task(fw_spec)

        self.assertEqual(str(cm.exception),
                         'No restart file in . for glob pattern *.restart[0-9]')


    def test_do_nothing_at_previous_success(self):
        """Will run a recovery task that does nothing."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        task_spec = {
            'restart_wf': self.default_restart_wf_dict,
            'fizzle_on_no_restart_file': False,
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {}
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)

        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())
        detours = fw_action.detours
        self.assertEqual(detours, [])

    def test_do_nothing_at_maximum_numnber_of_restarts(self):
        """Will run a recovery task that does nothing."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        task_spec = {
            'restart_wf': self.default_restart_wf_dict,
            'fizzle_on_no_restart_file': False,
            'max_restarts': 5,
            'restart_counter': 'restart_count',
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_fizzled_parents': [{
                'launches': [{'launch_dir': os.curdir}],
                'name': 'dummy parent',
                'fw_id': 1,
                'spec': {'restart_count': 5},
            }]
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)

        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())
        detours = fw_action.detours
        self.assertEqual(detours, [])

    def test_recover_single_restart_file(self):
        """Will run a recovery task that does nothing."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        os.mkdir('dummy_prev_launch')
        with open(os.path.join('dummy_prev_launch', 'dummy_restart_file'), 'w') as fp:
            pass

        logger.debug("Test directory tree before running RecoverTask.")
        _log_dir()

        task_spec = {
            'restart_wf': self.default_restart_wf_dict,
            'fizzle_on_no_restart_file': True,
            'restart_file_glob_patterns': '*_restart_file'
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_job_info': [{
                'launch_dir': 'dummy_prev_launch',
                'name': 'dummy parent',
                'fw_id': 1,
            }]
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)
        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())
        logger.debug("Test directory tree after running RecoverTask.")
        _log_dir()

        recoverd_restart_files = glob.glob('*_restart_file')
        self.assertEqual(len(recoverd_restart_files), 1)
        self.assertEqual(recoverd_restart_files[0], "dummy_restart_file")

    def test_select_latest_restart_file(self):
        """Will run a recovery task that does nothing."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        os.mkdir('dummy_prev_launch')
        first_restart_file = os.path.join('dummy_prev_launch', 'first_restart_file')
        second_restart_file = os.path.join('dummy_prev_launch', 'second_restart_file')
        with open(first_restart_file, 'w'):
            pass
        with open(second_restart_file, 'w'):
            pass

        logger.debug("Test directory tree before running RecoverTask.")
        _log_dir()

        # make sure files are sortable by mtime
        second_restart_file_stats = os.stat(second_restart_file)

        os.utime(first_restart_file, ns=(
            second_restart_file_stats.st_atime_ns-1e9,
            second_restart_file_stats.st_mtime_ns-1e9))

        first_restart_file_stats = os.stat(first_restart_file)

        logger.debug("firts_restart_file (atime_ns, mtime_ns) = ({}, {})".format(
                      first_restart_file_stats.st_atime_ns,
                      first_restart_file_stats.st_mtime_ns,))
        logger.debug("second_restart_file (atime_ns, mtime_ns) = ({}, {})".format(
                      second_restart_file_stats.st_atime_ns,
                      second_restart_file_stats.st_mtime_ns,))

        task_spec = {
            'restart_wf': self.default_restart_wf_dict,
            'fizzle_on_no_restart_file': True,
            'restart_file_glob_patterns': '*_restart_file'
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_job_info': [{
                'launch_dir': 'dummy_prev_launch',
                'name': 'dummy parent',
                'fw_id': 1,
            }]
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)
        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())
        logger.debug("Test directory tree after running RecoverTask.")
        _log_dir()

        recoverd_restart_files = glob.glob('*_restart_file')
        self.assertEqual(len(recoverd_restart_files), 1)
        self.assertEqual(recoverd_restart_files[0], "second_restart_file")

    def test_select_multiple_restart_files(self):
        """Will run a recovery task that does nothing."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        os.mkdir('dummy_prev_launch')

        first_restart_file = os.path.join('dummy_prev_launch', 'first_restart_file')
        second_restart_file = os.path.join('dummy_prev_launch', 'second_restart_file')
        with open(first_restart_file, 'w'):
            pass
        with open(second_restart_file, 'w'):
            pass

        logger.debug("Test directory tree before running RecoverTask.")
        _log_dir()

        # make sure files are sortable by mtime
        second_restart_file_stats = os.stat(second_restart_file)

        os.utime(first_restart_file, ns=(
            second_restart_file_stats.st_atime_ns-1e9,
            second_restart_file_stats.st_mtime_ns-1e9))

        first_restart_file_stats = os.stat(first_restart_file)

        logger.debug("firts_restart_file (atime_ns, mtime_ns) = ({}, {})".format(
                      first_restart_file_stats.st_atime_ns,
                      first_restart_file_stats.st_mtime_ns,))
        logger.debug("second_restart_file (atime_ns, mtime_ns) = ({}, {})".format(
                      second_restart_file_stats.st_atime_ns,
                      second_restart_file_stats.st_mtime_ns,))

        # different set of restart files
        first_checkpoint_file = os.path.join('dummy_prev_launch', 'first_checkpoint_file')
        second_checkpoint_file = os.path.join('dummy_prev_launch', 'second_checkpoint_file')
        with open(first_checkpoint_file, 'w'):
            pass
        with open(second_checkpoint_file, 'w'):
            pass

        logger.debug("Test directory tree before running RecoverTask.")
        _log_dir()

        # make sure files are sortable by mtime
        second_checkpoint_file_stats = os.stat(second_checkpoint_file)

        os.utime(first_checkpoint_file, ns=(
            second_checkpoint_file_stats.st_atime_ns-1e9,
            second_checkpoint_file_stats.st_mtime_ns-1e9))

        first_checkpoint_file_stats = os.stat(first_checkpoint_file)

        logger.debug("firts_checkpoint_file (atime_ns, mtime_ns) = ({}, {})".format(
                      first_checkpoint_file_stats.st_atime_ns,
                      first_checkpoint_file_stats.st_mtime_ns,))
        logger.debug("second_checkpoint_file (atime_ns, mtime_ns) = ({}, {})".format(
                      second_checkpoint_file_stats.st_atime_ns,
                      second_checkpoint_file_stats.st_mtime_ns,))

        task_spec = {
            'restart_wf': self.default_restart_wf_dict,
            'fizzle_on_no_restart_file': True,
            'restart_file_glob_patterns': ['*_restart_file', '*_checkpoint_file'],
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_job_info': [{
                'launch_dir': 'dummy_prev_launch',
                'name': 'dummy parent',
                'fw_id': 1,
            }]
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)
        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())
        logger.debug("Test directory tree after running RecoverTask.")
        _log_dir()

        recoverd_restart_files = glob.glob('*_restart_file')
        self.assertEqual(len(recoverd_restart_files), 1)
        self.assertEqual(recoverd_restart_files[0], "second_restart_file")

        recoverd_checkpoint_files = glob.glob('*_checkpoint_file')
        self.assertEqual(len(recoverd_checkpoint_files), 1)
        self.assertEqual(recoverd_checkpoint_files[0], "second_checkpoint_file")

    def test_recover_other_files(self):
        """Will run a recovery task that recovers all files matching other_glob_patterns."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        os.mkdir('dummy_prev_launch')

        some_file = os.path.join('dummy_prev_launch', 'some_file')
        some_other_file = os.path.join('dummy_prev_launch', 'some_other_file')
        some_third_file = os.path.join('dummy_prev_launch', 'some_third_file')
        with open(some_file, 'w'):
            pass
        with open(some_other_file, 'w'):
            pass
        with open(some_third_file, 'w'):
            pass

        logger.debug("Test directory tree before running RecoverTask.")
        _log_dir()

        task_spec = {
            'restart_wf': self.default_restart_wf_dict,
            'fizzle_on_no_restart_file': False,
            'other_glob_patterns': ['some_file', 'some_*_file'],
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_job_info': [{
                'launch_dir': 'dummy_prev_launch',
                'name': 'dummy parent',
                'fw_id': 1,
            }]
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)

        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())
        logger.debug("Test directory tree after running RecoverTask.")
        _log_dir()

        some_recovered_file = glob.glob('some_file')
        self.assertEqual(len(some_recovered_file), 1)
        self.assertEqual(some_recovered_file[0], "some_file")

        some_other_recovered_files = glob.glob('some_*_file')
        self.assertEqual(len(some_other_recovered_files), 2)
        self.assertIn("some_other_file", some_other_recovered_files)
        self.assertIn("some_third_file", some_other_recovered_files)

    def test_restart_wf_insertion(self):
        """Run a recovery task that returns a restart detour."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))
        # the following restart_wf parameter...
        # +-----------------+     +-----------------+     +------------------+
        # | restart_wf root | --> | restart_wf body | --> | restart_wf leafs |
        # +-----------------+     +-----------------+     +------------------+
        dummy_ft = PyTask(func='print', args=['I am a dummy task'])
        restart_root_fw = Firework([dummy_ft], name='restart_wf root')
        restart_body_fw = Firework([dummy_ft], name='restart_wf body', parents=[restart_root_fw])
        restart_leaf_fw = Firework([dummy_ft], name='restart_wf leaf', parents=[restart_body_fw])

        restart_wf = Workflow([restart_root_fw, restart_body_fw, restart_leaf_fw])

        logger.debug("Restart wf:")
        _log_nested_dict(restart_wf.as_dict())

        task_spec = {
            'fizzle_on_no_restart_file': False,
            'repeated_recover_fw_name': 'recover_fw',
            'restart_wf': restart_wf.as_dict(),
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_job_info': [{
                'launch_dir': 'dummy_prev_launch',
                'name': 'dummy parent',
                'fw_id': 1,
            }]
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)

        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())

        # ... must result in the following detour
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
        # ' restart_wf                                                          '
        # '                                                                     '
        # ' +-----------------+     +-----------------+     +-----------------+ '     +------------+
        # ' | restart_wf root | --> | restart_wf body | --> | restart_wf leaf | ' --> | recover_fw |
        # ' +-----------------+     +-----------------+     +-----------------+ '     +------------+
        # '                                                                     '
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
        detour = fw_action.detours[0]
        self.assertIsInstance(detour, Workflow)

        self.assertEqual(len(detour.leaf_fw_ids), 1)
        self.assertEqual(len(detour.root_fw_ids), 1)

        root_fw_id = detour.root_fw_ids[0]
        self.assertEqual(detour.id_fw[root_fw_id].name, 'restart_wf root')

        self.assertEqual(len(detour.links[root_fw_id]), 1)
        body_fw_id = detour.links[root_fw_id][0]
        self.assertEqual(detour.id_fw[body_fw_id].name, 'restart_wf body')

        self.assertEqual(len(detour.links[body_fw_id]), 1)
        leaf_fw_id = detour.links[body_fw_id][0]
        self.assertEqual(detour.id_fw[leaf_fw_id].name, 'restart_wf leaf')

        self.assertEqual(len(detour.links[leaf_fw_id]), 1)
        recover_fw_id = detour.links[leaf_fw_id][0]
        self.assertEqual(detour.id_fw[recover_fw_id].name, 'recover_fw')

    def test_detour_wf_insertion(self):
        """Run a recovery task that returns a detour."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        # The following restart_wf parameter...
        # +-----------------+     +-----------------+     +------------------+
        # | restart_wf root | --> | restart_wf body | --> | restart_wf leafs |
        # +-----------------+     +-----------------+     +------------------+
        dummy_ft = PyTask(func='print', args=['I am a dummy task'])
        restart_root_fw = Firework([dummy_ft], name='restart_wf root')
        restart_body_fw = Firework([dummy_ft], name='restart_wf body', parents=[restart_root_fw])
        restart_leaf_fw = Firework([dummy_ft], name='restart_wf leaf', parents=[restart_body_fw])

        restart_wf = Workflow([restart_root_fw, restart_body_fw, restart_leaf_fw])

        logger.debug("Restart wf:")
        _log_nested_dict(restart_wf.as_dict())

        # ...together with the following detour_wf parameter...
        # +----------------+     +-----------------+     +------------------+
        # | detour_wf root | --> | detour_wf body | --> | detour_wf leafs |
        # +----------------+     +-----------------+     +------------------+
        detour_root_fw = Firework([dummy_ft], name='detour_wf root')
        detour_body_fw = Firework([dummy_ft], name='detour_wf body', parents=[detour_root_fw])
        detour_leaf_fw = Firework([dummy_ft], name='detour_wf leaf', parents=[detour_body_fw])

        detour_wf = Workflow([detour_root_fw, detour_body_fw, detour_leaf_fw])

        logger.debug("Detour wf:")
        _log_nested_dict(detour_wf.as_dict())

        task_spec = {
            'restart_wf': restart_wf.as_dict(),
            'detour_wf': detour_wf.as_dict(),
            'fizzle_on_no_restart_file': False,
            'repeated_recover_fw_name': 'recover_fw',
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_job_info': [{
                'launch_dir': 'dummy_prev_launch',
                'name': 'dummy parent',
                'fw_id': 1,
            }]
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)

        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())

        # ... must result in the following detour:
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
        # ' detour_wf                                                           '
        # '                                                                     '
        # ' +-----------------+     +-----------------+     +-----------------+ '     +------------+
        # ' | detour_wf root  | --> | detour_wf body  | --> | detour_wf leaf  | ' --> | recover_fw |
        # ' +-----------------+     +-----------------+     +-----------------+ '     +------------+
        # '                                                                     '
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
        #                                                                               ^
        #                                                                               |
        #                                                                               |
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +       |
        # ' restart_wf                                                          '       |
        # '                                                                     '       |
        # ' +-----------------+     +-----------------+     +-----------------+ '       |
        # ' | restart_wf root | --> | restart_wf body | --> | restart_wf leaf | ' ------+
        # ' +-----------------+     +-----------------+     +-----------------+ '
        # '                                                                     '
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
        detour = fw_action.detours[0]
        self.assertIsInstance(detour, Workflow)

        self.assertEqual(len(detour.leaf_fw_ids), 1)
        self.assertEqual(len(detour.root_fw_ids), 2)

        # roots
        root_fw_names = {detour.id_fw[fw_id].name: fw_id for fw_id in detour.root_fw_ids}

        self.assertIn('detour_wf root', root_fw_names)
        self.assertIn('restart_wf root', root_fw_names)

        # restart_wf
        restart_root_fw_children = detour.links[root_fw_names['restart_wf root']]
        self.assertEqual(len(restart_root_fw_children), 1)
        restart_body_fw_id = restart_root_fw_children[0]
        self.assertEqual(detour.id_fw[restart_body_fw_id].name, 'restart_wf body')

        self.assertEqual(len(detour.links[restart_body_fw_id]), 1)
        restart_leaf_fw_id = detour.links[restart_body_fw_id][0]
        self.assertEqual(detour.id_fw[restart_leaf_fw_id].name, 'restart_wf leaf')

        self.assertEqual(len(detour.links[restart_leaf_fw_id]), 1)
        recover_fw_id = detour.links[restart_leaf_fw_id][0]
        self.assertEqual(detour.id_fw[recover_fw_id].name, 'recover_fw')

        # detour_wf
        detour_root_fw_children = detour.links[root_fw_names['detour_wf root']]
        self.assertEqual(len(detour_root_fw_children), 1)
        detour_body_fw_id = detour_root_fw_children[0]
        self.assertEqual(detour.id_fw[detour_body_fw_id].name, 'detour_wf body')

        self.assertEqual(len(detour.links[detour_body_fw_id]), 1)
        detour_leaf_fw_id = detour.links[detour_body_fw_id][0]
        self.assertEqual(detour.id_fw[detour_leaf_fw_id].name, 'detour_wf leaf')

        self.assertEqual(len(detour.links[detour_leaf_fw_id]), 1)
        same_recover_fw_id = detour.links[detour_leaf_fw_id][0]
        self.assertEqual(recover_fw_id, same_recover_fw_id)

    def test_addition_wf_insertion(self):
        """Run a recovery task that returns a detour."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        # The following restart_wf parameter...
        # +-----------------+     +-----------------+     +------------------+
        # | restart_wf root | --> | restart_wf body | --> | restart_wf leafs |
        # +-----------------+     +-----------------+     +------------------+
        dummy_ft = PyTask(func='print', args=['I am a dummy task'])
        restart_root_fw = Firework([dummy_ft], name='restart_wf root')
        restart_body_fw = Firework([dummy_ft], name='restart_wf body', parents=[restart_root_fw])
        restart_leaf_fw = Firework([dummy_ft], name='restart_wf leaf', parents=[restart_body_fw])

        restart_wf = Workflow([restart_root_fw, restart_body_fw, restart_leaf_fw])

        logger.debug("Restart wf:")
        _log_nested_dict(restart_wf.as_dict())

        # ...together with the following addition_wf parameter...
        # +----------------+     +-----------------+     +------------------+
        # | addition_wf root | --> | addition_wf body | --> | addition_wf leafs |
        # +----------------+     +-----------------+     +------------------+
        addition_root_fw = Firework([dummy_ft], name='addition_wf root')
        addition_body_fw = Firework([dummy_ft], name='addition_wf body', parents=[addition_root_fw])
        addition_leaf_fw = Firework([dummy_ft], name='addition_wf leaf', parents=[addition_body_fw])

        addition_wf = Workflow([addition_root_fw, addition_body_fw, addition_leaf_fw])

        logger.debug("Addition wf:")
        _log_nested_dict(addition_wf.as_dict())

        task_spec = {
            'restart_wf': restart_wf.as_dict(),
            'addition_wf': addition_wf.as_dict(),
            'fizzle_on_no_restart_file': False,
            'repeated_recover_fw_name': 'recover_fw',
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_job_info': [{
                'launch_dir': 'dummy_prev_launch',
                'name': 'dummy parent',
                'fw_id': 1,
            }]
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)

        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())

        # ... must result in the following addition:
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+
        # ' addition_wf                                                            '
        # '                                                                        '
        # ' +------------------+     +------------------+     +------------------+ '
        # ' | addition_wf root | --> | addition_wf body | --> | addition_wf leaf | '
        # ' +------------------+     +------------------+     +------------------+ '
        # '                                                                        '
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+
        #
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
        # ' restart_wf                                                          '
        # '                                                                     '
        # ' +-----------------+     +-----------------+     +-----------------+ '    +------------+
        # ' | restart_wf root | --> | restart_wf body | --> | restart_wf leaf | '--> | recover_fw |
        # ' +-----------------+     +-----------------+     +-----------------+ '    +------------+
        # '                                                                     '
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +

        detour = fw_action.detours[0]
        self.assertIsInstance(detour, Workflow)

        self.assertEqual(len(detour.leaf_fw_ids), 1)
        self.assertEqual(len(detour.root_fw_ids), 1)

        root_fw_id = detour.root_fw_ids[0]
        self.assertEqual(detour.id_fw[root_fw_id].name, 'restart_wf root')

        self.assertEqual(len(detour.links[root_fw_id]), 1)
        body_fw_id = detour.links[root_fw_id][0]
        self.assertEqual(detour.id_fw[body_fw_id].name, 'restart_wf body')

        self.assertEqual(len(detour.links[body_fw_id]), 1)
        leaf_fw_id = detour.links[body_fw_id][0]
        self.assertEqual(detour.id_fw[leaf_fw_id].name, 'restart_wf leaf')

        self.assertEqual(len(detour.links[leaf_fw_id]), 1)
        recover_fw_id = detour.links[leaf_fw_id][0]
        self.assertEqual(detour.id_fw[recover_fw_id].name, 'recover_fw')


        addition = fw_action.additions[0]
        self.assertIsInstance(addition, Workflow)

        self.assertEqual(len(addition.leaf_fw_ids), 1)
        self.assertEqual(len(addition.root_fw_ids), 1)

        root_fw_id = addition.root_fw_ids[0]
        self.assertEqual(addition.id_fw[root_fw_id].name, 'addition_wf root')

        self.assertEqual(len(addition.links[root_fw_id]), 1)
        body_fw_id = addition.links[root_fw_id][0]
        self.assertEqual(addition.id_fw[body_fw_id].name, 'addition_wf body')

        self.assertEqual(len(addition.links[body_fw_id]), 1)
        leaf_fw_id = addition.links[body_fw_id][0]
        self.assertEqual(addition.id_fw[leaf_fw_id].name, 'addition_wf leaf')

        self.assertEqual(len(addition.links[leaf_fw_id]), 0)


    def test_triple_wf_insertion(self):
        """Run a recovery task that returns a detour."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        restart_wf = _get_dummy_restart_wf()
        logger.debug("Restart wf:")
        _log_nested_dict(restart_wf.as_dict())


        addition_wf = _get_dummy_addition_wf()
        logger.debug("Addition wf:")
        _log_nested_dict(addition_wf.as_dict())

        detour_wf = _get_dummy_detour_wf()
        logger.debug("Detour wf:")
        _log_nested_dict(detour_wf.as_dict())


        task_spec = {
            'restart_wf': restart_wf.as_dict(),
            'addition_wf': addition_wf.as_dict(),
            'detour_wf': detour_wf.as_dict(),
            'fizzle_on_no_restart_file': False,
            'repeated_recover_fw_name': 'recover_fw',
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_job_info': [{
                'launch_dir': 'dummy_prev_launch',
                'name': 'dummy parent',
                'fw_id': 1,
            }]
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)

        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())

        # ... must result in the following addition:
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+
        # ' addition_wf                                                            '
        # '                                                                        '
        # ' +------------------+     +------------------+     +------------------+ '
        # ' | addition_wf root | --> | addition_wf body | --> | addition_wf leaf | '
        # ' +------------------+     +------------------+     +------------------+ '
        # '                                                                        '
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+
        #
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
        # ' detour_wf                                                           '
        # '                                                                     '
        # ' +-----------------+     +-----------------+     +-----------------+ '     +------------+
        # ' | detour_wf root  | --> | detour_wf body  | --> | detour_wf leaf  | ' --> | recover_fw |
        # ' +-----------------+     +-----------------+     +-----------------+ '     +------------+
        # '                                                                     '
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
        #                                                                               ^
        #                                                                               |
        #                                                                               |
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +       |
        # ' restart_wf                                                          '       |
        # '                                                                     '       |
        # ' +-----------------+     +-----------------+     +-----------------+ '       |
        # ' | restart_wf root | --> | restart_wf body | --> | restart_wf leaf | ' ------+
        # ' +-----------------+     +-----------------+     +-----------------+ '
        # '                                                                     '
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +

        # detour
        detour = fw_action.detours[0]
        self.assertIsInstance(detour, Workflow)

        self.assertEqual(len(detour.leaf_fw_ids), 1)
        self.assertEqual(len(detour.root_fw_ids), 2)

        # detour roots
        root_fw_names = {detour.id_fw[fw_id].name: fw_id for fw_id in detour.root_fw_ids}

        self.assertIn('detour_wf root', root_fw_names)
        self.assertIn('restart_wf root', root_fw_names)

        # restart_wf
        restart_leaf_fw_id = self._assert_restart_wf_topology(detour, root_fw_names['restart_wf root'])
        self.assertEqual(len(detour.links[restart_leaf_fw_id]), 1)
        recover_fw_id = detour.links[restart_leaf_fw_id][0]
        self.assertEqual(detour.id_fw[recover_fw_id].name, 'recover_fw')

        # detour_wf
        detour_leaf_fw_id = self._assert_detour_wf_topology(detour, root_fw_names['detour_wf root'])
        self.assertEqual(len(detour.links[detour_leaf_fw_id]), 1)
        same_recover_fw_id = detour.links[detour_leaf_fw_id][0]
        self.assertEqual(recover_fw_id, same_recover_fw_id)

        # addition
        addition = fw_action.additions[0]
        self.assertIsInstance(addition, Workflow)

        self.assertEqual(len(addition.leaf_fw_ids), 1)
        self.assertEqual(len(addition.root_fw_ids), 1)

        addition_root_fw_id = addition.root_fw_ids[0]
        addition_leaf_fw_id = self._assert_addition_wf_topology(addition, addition_root_fw_id)
        self.assertEqual(len(addition.links[addition_leaf_fw_id]), 0)

    def test_triple_wf_insertion_with_custom_links(self):
        """Run a recovery task that returns a detour."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        restart_wf = _get_dummy_restart_wf()
        logger.debug("Restart wf:")
        _log_nested_dict(restart_wf.as_dict())

        restart_wf_root_fw_ids = [fw.fw_id for fw in restart_wf.fws if fw.name == 'restart_wf body']
        restart_wf_leaf_fw_ids = [fw.fw_id for fw in restart_wf.fws if fw.name == 'restart_wf body']

        detour_wf = _get_dummy_detour_wf()
        logger.debug("Detour wf:")
        _log_nested_dict(detour_wf.as_dict())

        detour_wf_root_fw_ids = [fw.fw_id for fw in detour_wf.fws if fw.name == 'detour_wf body']
        detour_wf_leaf_fw_ids = [fw.fw_id for fw in detour_wf.fws if fw.name == 'detour_wf body']

        addition_wf = _get_dummy_addition_wf()
        logger.debug("Addition wf:")
        _log_nested_dict(addition_wf.as_dict())

        addition_wf_root_fw_ids = [fw.fw_id for fw in addition_wf.fws if fw.name == 'addition_wf body']

        task_spec = {
            'restart_wf': restart_wf.as_dict(),
            'addition_wf': addition_wf.as_dict(),
            'detour_wf': detour_wf.as_dict(),
            'restart_fws_root': restart_wf_root_fw_ids,
            'restart_fws_leaf': restart_wf_leaf_fw_ids,
            'detour_fws_root': detour_wf_root_fw_ids,
            'detour_fws_leaf': detour_wf_leaf_fw_ids,
            'addition_fws_root': addition_wf_root_fw_ids,
            'fizzle_on_no_restart_file': False,
            'repeated_recover_fw_name': 'recover_fw',
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_job_info': [{
                'launch_dir': 'dummy_prev_launch',
                'name': 'dummy parent',
                'fw_id': 1,
            }]
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)

        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())

        # per default, would result in
        #     + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+
        #     ' restart_wf                                                             '
        #     '                                                                        '
        #     ' +------------------+     +------------------+     +------------------+ '     +------------+
        # --> ' | restart_wf root  | --> | restart_wf body  | --> | restart_wf leaf  | ' --> | recover_fw |
        #     ' +------------------+     +------------------+     +------------------+ '     +------------+
        #     '                                                                        '
        #     + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+
        #                                                                                      ^
        #                                                                                      |
        #                                                                                      |
        #     + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+       |
        #     ' detour_wf                                                              '       |
        #     '                                                                        '       |
        #     ' +------------------+     +------------------+     +------------------+ '       |
        # --> ' |  detour_wf root  | --> |  detour_wf body  | --> |  detour_wf leaf  | ' ------+
        #     ' +------------------+     +------------------+     +------------------+ '
        #     '                                                                        '
        #     + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+
        #     + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+
        #     ' addition_wf                                                            '
        #     '                                                                        '
        #     ' +------------------+     +------------------+     +------------------+ '
        # --> ' | addition_wf root | --> | addition_wf body | --> | addition_wf leaf | '
        #     ' +------------------+     +------------------+     +------------------+ '
        #     '                                                                        '
        #     + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+

        # with custom entry and exit hooks (parent-child links), looks like
        #                              |
        #                              |
        #                              v
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+
        # ' restart_wf                                                             '
        # '                                                                        '
        # ' +------------------+     +------------------+     +------------------+ '
        # ' | restart_wf root  | --> | restart_wf body  | --> | restart_wf leaf  | '
        # ' +------------------+     +------------------+     +------------------+ '
        # '                                                                        '
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+
        #                              |
        #                              |
        #                              v
        #                            +------------------+
        #                            |    recover_fw    |
        #                            +------------------+
        #                              ^
        #                              |
        #                              |
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+
        # ' detour_wf                                                              '
        # '                                                                        '
        # ' +------------------+     +------------------+     +------------------+ '
        # ' |  detour_wf root  | --> |  detour_wf body  | --> |  detour_wf leaf  | '
        # ' +------------------+     +------------------+     +------------------+ '
        # '                                                                        '
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+
        #                              ^
        #                              |
        #                              |
        #
        #
        #
        #
        #
        #
        #                              |
        #                              |
        #                              v
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+
        # ' addition_wf                                                            '
        # '                                                                        '
        # ' +------------------+     +------------------+     +------------------+ '
        # ' | addition_wf root | --> | addition_wf body | --> | addition_wf leaf | '
        # ' +------------------+     +------------------+     +------------------+ '
        # '                                                                        '
        # + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+

        # detour
        detour = fw_action.detours[0]
        self.assertIsInstance(detour, Workflow)

        self.assertEqual(len(detour.leaf_fw_ids), 3)
        self.assertEqual(len(detour.root_fw_ids), 2)

        # detour roots
        root_fw_names = {detour.id_fw[fw_id].name: fw_id for fw_id in detour.root_fw_ids}
        self.assertIn('detour_wf root', root_fw_names)
        self.assertIn('restart_wf root', root_fw_names)

        # detour leaves
        leaf_fw_names = {detour.id_fw[fw_id].name: fw_id for fw_id in detour.leaf_fw_ids}
        self.assertIn('detour_wf leaf', leaf_fw_names)
        self.assertIn('restart_wf leaf', leaf_fw_names)
        self.assertIn('recover_fw', leaf_fw_names)

        recover_fw_id = leaf_fw_names['recover_fw']

        # restart_wf
        restart_root_fw_id = root_fw_names['restart_wf root']
        self.assertEqual(detour.id_fw[restart_root_fw_id].name, 'restart_wf root')
        restart_root_fw_children = detour.links[restart_root_fw_id]

        self.assertEqual(len(restart_root_fw_children), 1)
        restart_body_fw_id = restart_root_fw_children[0]
        self.assertEqual(detour.id_fw[restart_body_fw_id].name, 'restart_wf body')
        restart_body_fw_children = detour.links[restart_body_fw_id]

        self.assertEqual(len(restart_body_fw_children), 2)
        restart_body_fw_child_names = {detour.id_fw[fw_id].name: fw_id for fw_id in restart_body_fw_children}
        self.assertIn('restart_wf leaf', restart_body_fw_child_names)
        self.assertIn('recover_fw', restart_body_fw_child_names)
        self.assertEqual(restart_body_fw_child_names['recover_fw'], recover_fw_id)

        restart_leaf_fw_id = restart_body_fw_child_names['restart_wf leaf']
        self.assertEqual(len(detour.links[restart_leaf_fw_id]), 0)

        # detour_wf
        detour_root_fw_id = root_fw_names['detour_wf root']
        self.assertEqual(detour.id_fw[detour_root_fw_id].name, 'detour_wf root')
        detour_root_fw_children = detour.links[detour_root_fw_id]

        self.assertEqual(len(detour_root_fw_children), 1)
        detour_body_fw_id = detour_root_fw_children[0]
        self.assertEqual(detour.id_fw[detour_body_fw_id].name, 'detour_wf body')
        detour_body_fw_children = detour.links[detour_body_fw_id]

        self.assertEqual(len(detour_body_fw_children), 2)
        detour_body_fw_child_names = {detour.id_fw[fw_id].name: fw_id for fw_id in detour_body_fw_children}
        self.assertIn('detour_wf leaf', detour_body_fw_child_names)
        self.assertIn('recover_fw', detour_body_fw_child_names)
        self.assertEqual(detour_body_fw_child_names['recover_fw'], recover_fw_id)

        detour_leaf_fw_id = detour_body_fw_child_names['detour_wf leaf']
        self.assertEqual(len(detour.links[detour_leaf_fw_id]), 0)

        # addition
        addition = fw_action.additions[0]
        self.assertIsInstance(addition, Workflow)

        self.assertEqual(len(addition.leaf_fw_ids), 1)
        self.assertEqual(len(addition.root_fw_ids), 1)

        addition_root_fw_id = addition.root_fw_ids[0]
        self.assertEqual(addition.id_fw[addition_root_fw_id].name, 'addition_wf root')
        addition_root_fw_children = addition.links[addition_root_fw_id]

        self.assertEqual(len(addition_root_fw_children), 1)
        addition_body_fw_id = addition_root_fw_children[0]
        self.assertEqual(addition.id_fw[addition_body_fw_id].name, 'addition_wf body')

        self.assertEqual(len(addition.links[addition_body_fw_id]), 1)
        addition_leaf_fw_id = addition.links[addition_body_fw_id][0]
        self.assertEqual(addition.id_fw[addition_leaf_fw_id].name, 'addition_wf leaf')
        self.assertEqual(len(addition.links[addition_leaf_fw_id]), 0)

        # custom outgoing links
        self.assertEqual(len(fw_action.detours_root_fw_ids), 1)
        self.assertEqual(len(fw_action.detours_leaf_fw_ids), 1)
        self.assertEqual(len(fw_action.additions_root_fw_ids), 1)

        self.assertEqual(len(fw_action.detours_root_fw_ids[0]), 2)
        self.assertEqual(len(fw_action.detours_leaf_fw_ids[0]), 1)
        self.assertEqual(len(fw_action.additions_root_fw_ids[0]), 1)

        self.assertIn(restart_body_fw_id, fw_action.detours_root_fw_ids[0])
        self.assertIn(detour_body_fw_id, fw_action.detours_root_fw_ids[0])
        self.assertIn(recover_fw_id, fw_action.detours_leaf_fw_ids[0])
        self.assertIn(addition_body_fw_id, fw_action.additions_root_fw_ids[0])

        logger.info("detoors_root_fw_ids: {}".format(fw_action.detours_root_fw_ids))
        logger.info("detoors_leaf_fw_ids: {}".format(fw_action.detours_leaf_fw_ids))
        logger.info("additions_root_fw_ids: {}".format(fw_action.additions_root_fw_ids))

    def test_base_spec_for_triple_wf(self):
        """Run a recovery task that merges new and recovered specs for restart_wf, detour_wf, and restart_fw."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        restart_wf = _get_dummy_restart_wf()
        logger.debug("Restart wf:")
        _log_nested_dict(restart_wf.as_dict())


        addition_wf = _get_dummy_addition_wf()
        logger.debug("Addition wf:")
        _log_nested_dict(addition_wf.as_dict())

        detour_wf = _get_dummy_detour_wf()
        logger.debug("Detour wf:")
        _log_nested_dict(detour_wf.as_dict())


        task_spec = {
            'restart_wf': restart_wf.as_dict(),
            'addition_wf': addition_wf.as_dict(),
            'detour_wf': detour_wf.as_dict(),
            'fizzle_on_no_restart_file': False,
            'repeated_recover_fw_name': 'recover_fw',
            'fw_spec_to_exclude': {
                "top-level-key-to-include": {
                    "nested-level-key-to-exclude": True,
                },
                "top-level-key-to-exclude": True,
            },
            'restart_fw_spec_to_exclude': {
                "top-level-key-to-include": {
                    "nested-level-key-to-exclude": True,
                },
                "top-level-key-to-exclude": True,
            },
            'addition_fw_spec_to_exclude': {
                "top-level-key-to-include": {
                    "nested-level-key-to-exclude": True,
                },
                "top-level-key-to-exclude": True,
            },
            'detour_fw_spec_to_exclude': {
                "top-level-key-to-include": {
                    "nested-level-key-to-exclude": True,
                },
                "top-level-key-to-exclude": True,
            },
            "superpose_restart_on_parent_fw_spec": True,
            "superpose_addition_on_parent_fw_spec": True,
            "superpose_detour_on_parent_fw_spec": True,
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_job_info': [{
                'launch_dir': 'dummy_prev_launch',
                'name': 'dummy parent',
                'fw_id': 1,
                "spec": {
                    "top-level-key-to-include": {
                        "nested-level-key-to-include": True,
                        "nested-level-key-to-exclude": True,
                    },
                    "top-level-key-to-exclude": True
                },
            }],
            'top-level-key-in-recover-fw': True,
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)

        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())

        # ... must result in the following addition:

        # detour
        detour = fw_action.detours[0]
        self.assertIsInstance(detour, Workflow)

        self.assertEqual(len(detour.leaf_fw_ids), 1)
        self.assertEqual(len(detour.root_fw_ids), 2)

        # detour roots
        root_fw_names = {detour.id_fw[fw_id].name: fw_id for fw_id in detour.root_fw_ids}

        self.assertIn('detour_wf root', root_fw_names)
        self.assertIn('restart_wf root', root_fw_names)

        # restart_wf
        restart_leaf_fw_id = self._assert_restart_wf_topology(detour, root_fw_names['restart_wf root'])
        self.assertEqual(len(detour.links[restart_leaf_fw_id]), 1)
        recover_fw_id = detour.links[restart_leaf_fw_id][0]
        self.assertEqual(detour.id_fw[recover_fw_id].name, 'recover_fw')

        # detour_wf
        detour_leaf_fw_id = self._assert_detour_wf_topology(detour, root_fw_names['detour_wf root'])
        self.assertEqual(len(detour.links[detour_leaf_fw_id]), 1)
        same_recover_fw_id = detour.links[detour_leaf_fw_id][0]
        self.assertEqual(recover_fw_id, same_recover_fw_id)

        # addition
        addition = fw_action.additions[0]
        self.assertIsInstance(addition, Workflow)

        self.assertEqual(len(addition.leaf_fw_ids), 1)
        self.assertEqual(len(addition.root_fw_ids), 1)

        addition_root_fw_id = addition.root_fw_ids[0]
        addition_leaf_fw_id = self._assert_addition_wf_topology(addition, addition_root_fw_id)
        self.assertEqual(len(addition.links[addition_leaf_fw_id]), 0)

        # fw_spec assertions:
        for fw in [*detour.fws, *addition.fws]:
            if fw.name != "recover_fw":
                self.assertIn("top-level-key-to-include", fw.spec)
                self.assertIn("nested-level-key-to-include", fw.spec["top-level-key-to-include"])
                self.assertNotIn("nested-level-key-to-exclude", fw.spec["top-level-key-to-include"])
                self.assertNotIn("top-level-key-to-exclude", fw.spec)
                self.assertNotIn("top-level-key-in-recover-fw", fw.spec)
            else:
                self.assertNotIn("top-level-key-to-include", fw.spec)
                self.assertIn("top-level-key-in-recover-fw", fw.spec)

    def test_default_exclusions_for_triple_wf(self):
        """Run a recovery task that applies default exclusions when merging specs."""
        logger = logging.getLogger(__name__)
        logger.info("### {} ###".format(sys._getframe().f_code.co_name))

        restart_wf = _get_dummy_restart_wf()
        logger.debug("Restart wf:")
        _log_nested_dict(restart_wf.as_dict())


        addition_wf = _get_dummy_addition_wf()
        logger.debug("Addition wf:")
        _log_nested_dict(addition_wf.as_dict())

        detour_wf = _get_dummy_detour_wf()
        logger.debug("Detour wf:")
        _log_nested_dict(detour_wf.as_dict())


        task_spec = {
            'restart_wf': restart_wf.as_dict(),
            'addition_wf': addition_wf.as_dict(),
            'detour_wf': detour_wf.as_dict(),
            'fizzle_on_no_restart_file': False,
            'repeated_recover_fw_name': 'recover_fw',
            "superpose_restart_on_parent_fw_spec": True,
            "superpose_addition_on_parent_fw_spec": True,
            "superpose_detour_on_parent_fw_spec": True,
        }
        task_spec = dict_merge(self.default_task_spec, task_spec)

        fw_spec = {
            '_fizzled_parents': [{
                'name': 'dummy parent',
                'fw_id': 1,
                'launches': [
                    {'launch_dir': './does/not/exist'}
                ],
                'spec': {
                    '_fizzled_parents': {'from': 'FizzledParent'},
                    '_job_info': {'from': 'FizzledParent'},
                    '_fw_env': {'from': 'FizzledParent'},
                    '_files_prev': {'from': 'FizzledParent'},
                }
            }],
            '_fw_env': {'from': 'RecoverTask'},
            '_files_prev': {'from': 'RecoverTask'},
        }
        fw_spec = dict_merge(self.default_fw_spec, fw_spec)

        logger.debug("Instantiate RecoverTask with '{}'".format(task_spec))
        t = RecoverTask(**task_spec)
        logger.debug("Run with fw_spec '{}'".format(fw_spec))
        fw_action = t.run_task(fw_spec)
        logger.debug("FWAction:")
        _log_nested_dict(fw_action.as_dict())

        # ... must result in the following addition:

        # detour
        detour = fw_action.detours[0]
        addition = fw_action.additions[0]

        # fw_spec assertions:
        for fw in [*detour.fws, *addition.fws]:
            self.assertNotIn('_job_info', fw.spec)
            self.assertNotIn('_fw_env', fw.spec)
            self.assertNotIn('_files_prev', fw.spec)
            self.assertNotIn('_fizzled_parents', fw.spec)


if __name__ == '__main__':
    unittest.main()
