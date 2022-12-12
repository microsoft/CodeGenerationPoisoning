# Copyright 2020-present MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, os.path
from time import sleep
from unittest import TestCase

from pymongo import MongoClient
import yaml

from atlasclient import JSONObject
from astrolabe.exceptions import WorkloadExecutorError, PrematureExitError
from astrolabe.utils import DriverWorkloadSubprocessRunner


class ValidateWorkloadExecutor(TestCase):
    WORKLOAD_EXECUTOR = None
    CONNECTION_STRING = None
    STARTUP_TIME = None

    def setUp(self):
        self.client = MongoClient(self.CONNECTION_STRING, w='majority')

    def set_collection_from_workload(self, driver_workload):
        # Set self.coll for future use of the validator, such that it can
        # read the data inserted into the collection.
        # Actual insertion of initial data isn't done via this object.
        dbname = None
        collname = None
        for e in driver_workload['createEntities']:
            if dbname and collname:
                break
            if dbname is None and 'database' in e:
                dbname = e['database']['databaseName']
            elif collname is None and 'collection' in e:
                collname = e['collection']['collectionName']

        if not (dbname and collname):
            self.fail('Invalid scenario: executor validator test cases must provide database and collection entities')

        self.coll = self.client.get_database(dbname).get_collection(collname)

    def run_test(self, driver_workload):
        self.set_collection_from_workload(driver_workload)
        
        subprocess = DriverWorkloadSubprocessRunner()
        try:
            subprocess.spawn(workload_executor=self.WORKLOAD_EXECUTOR,
                             connection_string=self.CONNECTION_STRING,
                             driver_workload=driver_workload,
                             startup_time=self.STARTUP_TIME)
        except WorkloadExecutorError:
            outs, errs = subprocess.workload_subprocess.communicate(timeout=2)
            self.fail("The workload executor terminated prematurely before "
                      "receiving the termination signal.\n"
                      "STDOUT: {!r}\nSTDERR: {!r}".format(outs, errs))

        # Run operations for 5 seconds.
        sleep(5)

        try:
            stats = subprocess.stop()
        except WorkloadExecutorError as exc:
            self.fail("WorkloadExecutorError: %s" % exc)

        return stats
    
    def run_test_expecting_error(self, driver_workload):
        self.set_collection_from_workload(driver_workload)
        
        subprocess = DriverWorkloadSubprocessRunner()
        try:
            subprocess.spawn(workload_executor=self.WORKLOAD_EXECUTOR,
                             connection_string=self.CONNECTION_STRING,
                             driver_workload=driver_workload,
                             startup_time=self.STARTUP_TIME)

            # Run operations for 5 seconds.
            sleep(5)
        except WorkloadExecutorError:
            # Accept premature workload executor exits when expecting the
            # run to error.
            pass

        # The workload executor is permitted to exit prematurely when expecting
        # an error, but it should still report stats via results.json
        try:
            try:
                stats = subprocess.stop()
            # Premature exit can cause a PrematureExitError or PermissionError
            except (PrematureExitError, PermissionError):
                stats = subprocess.read_stats()
        except WorkloadExecutorError as exc:
            self.fail("WorkloadExecutorError: %s" % exc)

        return stats

    # Assert that all keys exist on the object
    def assert_has_keys(self, obj, keys):
        for key in keys:
            if key not in obj:
                self.fail("Object did not contain expected key: %s" % key)

    # Assert that the parsed stats contain required fields and that numErrors
    # and numFailures are both set (i.e. not -1)
    def assert_basic_stats(self, stats):
        self.assert_has_keys(stats, ['numErrors', 'numFailures', 'numIterations', 'numSuccesses'])

        if stats['numErrors'] < 0:
            self.fail_stats(
                "Expected numErrors to be non-negative, but got {} instead."
                .format(stats['numErrors']))

        if stats['numFailures'] < 0:
            self.fail_stats(
                "Expected numFailures to be non-negative, but got {} instead."
                .format(stats['numFailures']))

    # Assert contents of the events.json file. The presence and type of each
    # required field (i.e. events, errors, failures) will always be asserted.
    # Based on the corresponding parameter for each field, the function will
    # then assert either that the array is empty or that it is non-empty and
    # each document therein has an expected structure.
    #
    # By default, this function will assert that events.json contains some
    # events but no errors or failures.
    #
    # If hasErrorsXorFailures is true, hasErrors and hasFailures will be ignored
    # and the function will instead assert that either errors or failures are
    # present (but not both).
    def assert_events(self, hasEvents=True, hasErrors=False, hasFailures=False,
                      hasErrorsXorFailures=False):
        try:
            events = yaml.safe_load(open('events.json').read())
        except OSError as exc:
            self.fail("Failed to open events.json: %s" % exc)
        except yaml.YAMLError as e:
            self.fail("Failed to parse events.json: %s" % e)

        # Assert both presence and type of required fields in events.json
        self.assert_has_keys(events, ['events', 'errors', 'failures'])

        if not isinstance(events['events'], list):
            self.fail("The workload executor didn't record events as an array.")

        if not isinstance(events['errors'], list):
            self.fail("The workload executor didn't record errors as an array.")

        if not isinstance(events['failures'], list):
            self.fail("The workload executor didn't record failrues as an array.")

        # If hasEvents is true, assert that the array is non-empty and that each
        # object within contains essential fields. If hasEvents is false, the
        # array should be empty.
        #
        # Note: we do not assert the type of events observed since not all
        # drivers implement CMAP and thus might only log Command events.
        if hasEvents:
            if not events['events']:
                self.fail("The workload executor recorded no events but some were expected")

            numConnectionEvents = 0
            numPoolEvents = 0
            numCommandEvents = 0

            for event in events['events']:
                if ('name' not in event) or (not event['name'].endswith('Event')):
                    self.fail("The workload executor didn't record event name as expected.")

                if 'observedAt' not in event:
                    self.fail("The workload executor didn't record event observation time as expected.")

                if event['name'].startswith('Connection'):
                    numConnectionEvents += 1

                if event['name'].startswith('Pool'):
                    numPoolEvents += 1

                if event['name'].startswith('Command'):
                    numCommandEvents += 1

            if numConnectionEvents == 0:
                self.fail("The workload executor recorded no CMAP connection events but some were expected")

            if numPoolEvents == 0:
                self.fail("The workload executor recorded no CMAP connection pool events but some were expected")

            if numCommandEvents == 0:
                self.fail("The workload executor recorded no command monitoring events but some were expected")
        else:
            if events['events']:
                self.fail("The workload executor recorded %d events but none were expected" % len(events['events']))

        # If hasErrorsXorFailures is true, allow either hasErrors or hasFailures
        # but not both. This is mainly needed for test_num_failures_not_captured
        # since the workload executor is permitted to report an uncaught failure
        # as either an error or failure.
        if hasErrorsXorFailures:
            # Infer hasErrors and hasFailures from the contents of events.json.
            # We need only assert xor equivalence here as the function will go
            # on to assert hasErrors and hasFailures independently.
            hasErrors = bool(events['errors'])
            hasFailures = bool(events['failures'])

            if hasErrors and hasFailures:
                self.fail("The workload executor recorded both errors and failures but only one was expected.")

            if not (hasErrors or hasFailures):
                self.fail("The workload executor recorded neither errors nor failures but one was expected.")

        # If hasErrors is true, assert that the array is non-empty and that each
        # object within contains essential fields. If hasErrors is false, the
        # array should be empty.
        if hasErrors:
            if not events['errors']:
                self.fail("The workload executor recorded no errors but some were expected")

            for error in events['errors']:
                if ('error' not in error) or ('time' not in error):
                    self.fail("The workload executor didn't record error as expected: {}".format(error))
        else:
            if events['errors']:
                self.fail("The workload executor recorded %d errors but none were expected" % len(events['errors']))

        # If hasFailures is true, assert that the array is non-empty and that
        # each object within contains essential fields. If hasFailures is false,
        # the array should be empty.
        if hasFailures:
            if not events['failures']:
                self.fail("The workload executor recorded no failures but some were expected")

            for failure in events['failures']:
                if ('error' not in failure) or ('time' not in failure):
                    self.fail("The workload executor didn't record failure as expected: {}".format(failure))
        else:
            if events['failures']:
                self.fail("The workload executor recorded %d failures but none were expected" % len(events['failures']))

    def fail_stats(self, msg):
        self.fail("The workload executor reported inconsistent execution statistics. " + str(msg))

    def test_simple(self):
        driver_workload = JSONObject.from_dict(
            yaml.safe_load(open('tests/validator-simple.yml').read())['driverWorkload']
        )

        stats = self.run_test(driver_workload)
        self.assert_basic_stats(stats)

        # The simple test's loop contains a single updateOne that increments the
        # document on each iteration. Fetch that value to use for assertions on
        # numSuccesses and numIterations.
        update_count = self.coll.find_one(
            {'_id': 'validation_sentinel'})['count']

        if update_count == 0:
            self.fail(
                "The workload executor didn't execute any operations "
                "or didn't execute them appropriately.")

        if abs(stats['numSuccesses']/2 - update_count) > 1:
            self.fail_stats(
                "Expected 2*{} successful operations to be reported in "
                "numSuccesses, but got {} instead."
                .format(update_count, stats['numSuccesses']))

        if abs(stats['numIterations'] - update_count) > 1:
            self.fail(
                "Expected {} iterations to be reported in numIterations, but "
                "got {} instead."
                .format(update_count, stats['numIterations']))

        if stats['numErrors'] != 0:
            self.fail_stats(
                "Expected no errors to be reported, but got {} instead."
                .format(stats['numErrors']))

        if stats['numFailures'] != 0:
            self.fail_stats(
                "Expected no failures to be reported, but got {} instead."
                .format(stats['numFailures']))

        self.assert_events(hasEvents=True, hasErrors=False, hasFailures=False)

    def test_num_errors(self):
        driver_workload = JSONObject.from_dict(
            yaml.safe_load(open('tests/validator-numErrors.yml').read())['driverWorkload']
        )

        stats = self.run_test(driver_workload)
        self.assert_basic_stats(stats)

        # Since the test only uses storeErrorsAsEntity, numFailures should never
        # be reported. This is irrelevant to whether or how a test runner
        # distinguishes between errors and failures.
        if stats['numFailures'] != 0:
            self.fail_stats(
                "Expected no failures to be reported, but got {} instead."
                .format(stats['numFailures']))

        # Each loop iteration should include two successful sub-operations
        # followed by one failure, so expect numErrors to be numSuccesses/2
        if abs(stats['numErrors'] - stats['numSuccesses']/2) > 1:
            self.fail_stats(
                "Expected approximately {}/2 errored operations to be reported "
                "in numErrors, but got {} instead."
                .format(stats['numSuccesses'], stats['numErrors']))

        # Each loop iteration should include two successful sub-operations, so
        # expect reported numIterations to be numSuccesses/2
        if abs(stats['numIterations'] - stats['numSuccesses']/2) > 1:
            self.fail_stats(
                "Expected approximately {}/2 iterations to be reported in "
                "numIterations, but got {} instead."
                .format(stats['numSuccesses'], stats['numIterations']))

        self.assert_events(hasEvents=False, hasErrors=True, hasFailures=False)

    def test_num_errors_not_captured(self):
        driver_workload = JSONObject.from_dict(
            yaml.safe_load(open('tests/validator-numErrors-not-captured.yml').read())['driverWorkload']
        )

        stats = self.run_test_expecting_error(driver_workload)
        self.assert_basic_stats(stats)

        # The workload executor is still expected to report errors propagated
        # from the unified test runner (e.g. loop operation without
        # storeErrorsAsEntity and storeFailuresAsEntity).
        if stats['numErrors'] != 1:
            self.fail_stats(
                "Expected one error to be reported, but got {} instead."
                .format(stats['numErrors']))

        if stats['numFailures'] != 0:
            self.fail_stats(
                "Expected no failures to be reported, but got {} instead."
                .format(stats['numFailures']))

        # Note: we do not assert numSuccesses or numIterations because the spec
        # does not guarantee that they will be reported via the entity map if
        # test runner propagates an error/failure.

        # In the event the test runner does not capture an error, the workload
        # executor is expected to report it in the same format
        self.assert_events(hasEvents=False, hasErrors=True, hasFailures=False)

    def test_num_errors_as_failures(self):
        driver_workload = JSONObject.from_dict(
            yaml.safe_load(open('tests/validator-numErrors-as-failures.yml').read())['driverWorkload']
        )

        stats = self.run_test(driver_workload)
        self.assert_basic_stats(stats)

        # Errors should be reported in numFailures instead of numErrors
        if stats['numErrors'] != 0:
            self.fail_stats(
                "Expected no errors to be reported in numErrors, but got {} "
                "instead.".format(stats['numErrors']))

        # Each loop iteration should include two successful sub-operations
        # followed by one error, so expect numFailures to be numSuccesses/2
        if abs(stats['numFailures'] - stats['numSuccesses']/2) > 1:
            self.fail_stats(
                "Expected approximately {}/2 errored operations to be reported "
                "in numFailures, but got {} instead."
                .format(stats['numSuccesses'], stats['numFailures']))

        # Each loop iteration should include two successful sub-operations, so
        # expect reported numIterations to be numSuccesses/2
        if abs(stats['numIterations'] - stats['numSuccesses']/2) > 1:
            self.fail_stats(
                "Expected approximately {}/2 iterations to be reported in "
                "numIterations, but got {} instead."
                .format(stats['numSuccesses'], stats['numIterations']))

        self.assert_events(hasEvents=False, hasErrors=False, hasFailures=True)

    def test_num_failures(self):
        driver_workload = JSONObject.from_dict(
            yaml.safe_load(open('tests/validator-numFailures.yml').read())['driverWorkload']
        )

        stats = self.run_test(driver_workload)
        self.assert_basic_stats(stats)

        # Since the test only uses storeFailuresAsEntity, numErrors should never
        # be reported. This is irrelevant to whether or how a test runner
        # distinguishes between errors and failures.
        if stats['numErrors'] != 0:
            self.fail_stats(
                "Expected no errors to be reported, but got {} instead."
                .format(stats['numErrors']))

        # Each loop iteration should include two successful sub-operations
        # followed by one failure, so expect numFailures to be numSuccesses/2
        if abs(stats['numFailures'] - stats['numSuccesses']/2) > 1:
            self.fail_stats(
                "Expected approximately {}/2 failed operations to be reported "
                "in numFailures, but got {} instead."
                .format(stats['numSuccesses'], stats['numFailures']))

        # Each loop iteration should include two successful sub-operations, so
        # expect reported numIterations to be numSuccesses/2
        if abs(stats['numIterations'] - stats['numSuccesses']/2) > 1:
            self.fail_stats(
                "Expected approximately {}/2 iterations to be reported in "
                "numIterations, but got {} instead."
                .format(stats['numSuccesses'], stats['numIterations']))

        self.assert_events(hasEvents=False, hasErrors=False, hasFailures=True)

    def test_num_failures_not_captured(self):
        driver_workload = JSONObject.from_dict(
            yaml.safe_load(open('tests/validator-numFailures-not-captured.yml').read())['driverWorkload']
        )

        stats = self.run_test_expecting_error(driver_workload)
        self.assert_basic_stats(stats)

        # The workload executor is still expected to report failures propagated
        # from the unified test runner (e.g. loop operation without
        # storeErrorsAsEntity and storeFailuresAsEntity) and is permitted to
        # report them as errors. For this reason, we must be flexible and allow
        # either numFailures or numErrors to be reported (but not both).
        if not ((stats['numErrors'] == 0 and stats['numFailures'] == 1) or
                (stats['numErrors'] == 1 and stats['numFailures'] == 0)):
            self.fail_stats(
                "Expected either numErrors:0 and numFailures:1 or numErrors:1 "
                "and numFailures:0, but got numErrors:{} and numFailures:{} "
                "instead."
                .format(stats['numErrors'], stats['numFailures']))

        # Note: we do not assert numSuccesses or numIterations because the spec
        # does not guarantee that they will be reported via the entity map if
        # test runner propagates an error/failure.

        # In the event the test runner does not capture a failure, the workload
        # executor is expected to report it in the same format; however, it may
        # be reported as either an error or failure
        self.assert_events(hasEvents=False, hasErrorsXorFailures=True)

    def test_num_failures_as_errors(self):
        driver_workload = JSONObject.from_dict(
            yaml.safe_load(open('tests/validator-numFailures-as-errors.yml').read())['driverWorkload']
        )

        stats = self.run_test(driver_workload)
        self.assert_basic_stats(stats)

        # Failures should be reported in numErrors instead of numFailures
        if stats['numFailures'] != 0:
            self.fail_stats(
                "Expected no failures to be reported in numFailures, but got "
                "{} instead.".format(stats['numFailures']))

        # Each loop iteration should include two successful sub-operations
        # followed by one failure, so expect numErrors to be numSuccesses/2
        if abs(stats['numErrors'] - stats['numSuccesses']/2) > 1:
            self.fail(
                "Expected approximately {}/2 failed operations to be reported "
                "in numErrors, but got {} instead."
                .format(stats['numSuccesses'], stats['numErrors']))

        # Each loop iteration should include two successful sub-operations, so
        # expect reported numIterations to be numSuccesses/2
        if abs(stats['numIterations'] - stats['numSuccesses']/2) > 1:
            self.fail(
                "Expected approximately {}/2 iterations to be reported in "
                "numIterations, but got {} instead."
                .format(stats['numSuccesses'], stats['numIterations']))

        self.assert_events(hasEvents=False, hasErrors=True, hasFailures=False)

def validator_factory(workload_executor, connection_string, startup_time):
    ValidateWorkloadExecutor.WORKLOAD_EXECUTOR = workload_executor
    ValidateWorkloadExecutor.CONNECTION_STRING = connection_string
    ValidateWorkloadExecutor.STARTUP_TIME = startup_time
    return ValidateWorkloadExecutor
