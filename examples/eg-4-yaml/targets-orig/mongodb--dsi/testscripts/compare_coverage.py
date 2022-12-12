#!/usr/bin/env python3.7

"""
Compare a new coverage.xml file against a previous one.

The previous coverage report is fetched from most recent completed task in Evergreen dsi project.
If this fails (e.g. due to network being unavailable), a fallback file from testscscripts/data/
is used.

Exit with non-zero if total code coverage is lower than in the previous.
"""


import sys
import traceback
import xml.etree.ElementTree as ElementTree
import yaml

import requests

from dsi.evergreen import evergreen_client


def _does_url_exist(url):
    """
    Check if the url is accessible.

    :return: True if _baseline_url is accessible.
    """
    res = requests.head(url)
    return res.ok


class CompareCoverage:
    """
    Compare a new coverage.xml file against a previous one.
    """

    def __init__(self):
        """
        Initialize.
        """
        self.config = {}
        self.evergreen = self.evergreen_connection()
        # Property:
        self._baseline_url = None


    def evergreen_connection(self):
        """
        Read config.yml, which is what we use in testscripts/.

        Yes, we ignore your ~/.evergreen.yml.
        """
        with open("config.yml") as config_file:
            self.config = yaml.load(config_file)
        return evergreen_client.Client(self.config['evergreen'])

    @property
    def baseline_url(self):
        """
        Get url for the baseline coverage.xml.

        https://s3.amazonaws.com/mciuploads/dsi/linux-runner/843eebfcbf7f9f5e7a116a1f23f2b46f11988d30/dsi_843eebfcbf7f9f5e7a116a1f23f2b46f11988d30/coverage.xml
        """
        if self._baseline_url:
            return self._baseline_url

        # Find the most recent dsi version that has finished running
        # Note: When running inside the waterfall, this also prevents from comparing
        # against myself!
        history = self.evergreen.query_project_history('dsi')
        for history_obj in history['versions']:
            version_obj = self.evergreen.query_revision(history_obj['version_id'])
            if version_obj['status'] in ('success', 'failed'):
                version_id = history_obj['version_id']
                revision = history_obj['revision']
                build = list(history_obj['builds'].keys())[0]
                domain = "https://s3.amazonaws.com"

                potential_url = "{}/mciuploads/dsi/{}/{}/{}/coverage.xml".format(
                    domain, build, revision, version_id)

                if not _does_url_exist(potential_url):
                    continue

                self._baseline_url = potential_url
                return self._baseline_url

        raise evergreen_client.EvergreenError("Did not find a completed task in Evergreen dsi history!")


    def baseline_xml(self):
        """
        Get the most recent coverage.xml from Evergreen.

        In case of a failure, return `testscripts/data/coverage.xml`.
        """
        try:
            print("Fetching: {}".format(self.baseline_url))
            response = requests.get(self.baseline_url)
            root = ElementTree.fromstring(response.text)
        except:
            print("WARNING: Fetching latest coverage % from Evergreen failed. Using {}.".format(
                'testscripts/data/coverage.xml'))
            traceback.print_exc()
            print()

            tree = ElementTree.parse('testscripts/data/coverage.xml')
            root = tree.getroot()

        return root

    def coverage_xml(self):
        """
        Return coverage.xml as an ElementTree root.
        """
        tree = ElementTree.parse('coverage.xml')
        return tree.getroot()


    def compare(self):
        """
        Parse coverage.xml and a previous coverage.xml, and exit with error if total coverage decreased.
        """
        print()
        print("*** compare_coverage.py ***")
        exit_code = 0

        # New coverage.xml
        root = self.coverage_xml()
        coverage_percent = float(root.attrib['line-rate'])

        # Baseline to compare against
        root = self.baseline_xml()
        baseline_percent = float(root.attrib['line-rate'])

        ratio = coverage_percent/baseline_percent
        # Somehow the result isn't quite deterministic over different platforms. We allow 1% "rounding
        # error" or skew:
        if 1 - ratio > 0.01:
            decrease = (1-ratio)*100.0
            print("FAIL: Total code coverage decreased by {} %.".format(decrease))
            exit_code = 1
        else:
            print("PASS: Code coverage {:2.2} >= {:2.2}.".format(coverage_percent, baseline_percent))

        print()
        return exit_code

def main():
    """
    Main program
    """
    compare = CompareCoverage()
    return compare.compare()

if __name__ == '__main__':
    sys.exit(main())
