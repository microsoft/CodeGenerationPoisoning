import json
import logging
import unittest
from unittest.mock import patch

from yaml import YAMLError

from cescout import main


class TestMain(unittest.TestCase):
    def setUp(self):
        self.config = {"ooni": {"db_name": "metadb", "db_user": "postgres",
                                "domains": ["wikipedia.org", "wikidata.org"]}}

    @patch("yaml.safe_load")
    def test_load_config(self, mock):
        mock.side_effect = [self.config, IOError(), YAMLError()]
        self.assertEqual(main.load_config(),
                         self.config)
        self.assertEqual(main.load_config(),
                         {})
        self.assertEqual(main.load_config(),
                         {})
        self.assertIn("ooni", self.config)

    def test_arg_parser(self):
        correct_args = ["-c CA --since 2020-02-01T10:00:00",
                        "-c CA --since 2020-02-01T10:00:00 --until 2020-02-01",
                        "-c CA --since 2020-02-01T10:00:00 --asns 1 --raw"]

        for arg in correct_args:
            main.arg_parser(arg.split(), ["ooni", ])

        incorrect_args = ["--since 2020-02-01T10:00:00",
                          "-c CA 2020-02-01T10:00:00",
                          "-c CA --since 2020-02-01T10:10:10 --asns one"]
        for arg in incorrect_args:
            with self.assertRaises(SystemExit):
                main.arg_parser(arg.split(), ["ooni", "ioda"])

        incorrect_date_args = ["-c CA --since 2020-13-01T10:00:00"]
        for arg in incorrect_date_args:
            with self.assertRaises(SystemExit):
                main.arg_parser(arg.split(), ["ripe", ])

        skip_projects = ["ooni", ]
        skip_args = correct_args[0] + " --skip-ooni"
        output = main.arg_parser(skip_args.split(), skip_projects)
        self.assertEqual(output.skip_ooni, True)

    def test_enable_logging(self):
        with self.assertLogs(logging.getLogger(), level="INFO") as log:
            logging.getLogger().info("test message")
            self.assertEqual(log.output, ["INFO:root:test message"])

    def test_generate_report(self):
        report_data = {"country": "Canada", "asns": 1,
                       "current": "2020-02-01", "since": "2020-02-02", "until": "2020-02-03",
                       "config": self.config}

        project_data = [
            {"projects": {"ooni": {"ran_test": True, "data": None}}},
            {"projects": {"ooni": {"ran_test": True, "data": {"len_all": 2, "len_blocking": 1,
                          "measurements": [{"url": "https://explorer.ooni.io/measurement/", "blocking": "tcp_ip"}]}}}},
            {"projects": {"ioda": {"ran_test": True, "data": {"is_outage": False}}}},
            {"projects": {"ripe": {"ran_test": True, "data": {1: {"current": 10, "since": 10, "until": 10}}}}},
            {"projects": {"ooni": {"ran_test": False}, "ioda": {"ran_test": False}}},
                       ]

        header = "Censorship Report for 'Canada' [2020-02-02 to 2020-02-03]\n\n"
        correct_output_data = [
            """[ooni] no data
""",
            """[ooni] domains: wikipedia.org, wikidata.org
[ooni] (1 / 2) anomalous measurements
[ooni] https://explorer.ooni.io/measurement/ [!]
""",
            """[ioda] no internet outage observed
""",
            """[ripe] ASN 1: 2020-02-01: 10 (current), 2020-02-02: 10 (since), 2020-02-03: 10 (until)
""",
            """[ooni] skipped test
[ioda] skipped test
"""
                               ]
        incorrect_output_data = [
            """ [ooni] no data
""",
            """[ooni] domains: wikidata.org
[ooni] (1 / 2) anomalous measurements
[ooni] https://explorer.ooni.io/measurement/ [!]
""",
            """[ioda] internet outage observed
""",
            """[ripe] ASN 1: 2020-02-02: 10 (current), 2020-02-02: 10 (since), 2020-02-03: 10 (until)""",
            """[ooni] skipped test [ioda] skipped test
"""
                                ]

        for config, output in zip(project_data, correct_output_data):
            self.assertEqual(main.generate_report({**report_data, **config}),
                             header+output)
        for config, output in zip(project_data, incorrect_output_data):
            self.assertNotEqual(main.generate_report({**report_data, **config}),
                                header+output)

    def test_get_measurements(self):
        args = {"country": "CA", "asns": 1,
                "current": "2020-01-01", "since": "2020-01-02", "until": "2020-01-03", "config": {}}
        with patch("cescout.main.load_config") as mock_config, \
                patch("cescout.projects.ooni.run") as mock_ooni, \
                patch("cescout.common.country_name") as mock_country, \
                patch("cescout.common.date_today") as mock_date:
            mock_config.return_value = {}
            mock_ooni.return_value = None
            mock_country.return_value = "CA"
            mock_date.return_value = "2020-01-01"
            self.assertEqual(main.get_measurements(["ooni", ], {**args, "skip_ooni": False}),
                             {**args, "projects": {"ooni": {"data": None, "ran_test": True}}})
            self.assertEqual(main.get_measurements(["ooni", ], {**args, "skip_ooni": True}),
                             {**args, "projects": {"ooni": {"ran_test": False}}})

    @patch("cescout.main.get_measurements")
    @patch("cescout.main.generate_report")
    def test_run(self, report_mock, measurements_mock):
        report_output = '{"projects": {"ooni": {"ran_test": True, "data": None}}}'
        report_mock.return_value = report_output
        measurements_mock.return_value = {"some_data": True}
        with patch("builtins.print") as mock_print:
            main.run("-c CA --since 2020-01-01".split())
            mock_print.assert_called_with(report_output)
            main.run("-c CA --since 2020-01-01 --raw".split())
            mock_print.assert_called_with(json.dumps({"some_data": True}))

    @patch("os.path.isdir")
    def test_config_dir(self, mock):
        mock.side_effect = [True, False, True]
        with patch("os.path.join", return_value="/test/path"):
            main.config_dir()
            mock.assert_called_with("/test/path")
        with patch("os.path.join", return_value="/etc/cescout"):
            main.config_dir()
            mock.assert_called_with("/etc/cescout")
