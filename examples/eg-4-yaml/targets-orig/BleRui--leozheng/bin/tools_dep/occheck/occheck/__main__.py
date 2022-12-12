#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import re
import fnmatch
import sys
import yaml

from antlr4 import *

from occheck import __pkginfo__
from occheck.context import FileContext
from occheck.checks import CheckRegistry
from occheck.reporters import ReporterRegistry
from occheck.diagnostic import DiagnosticConsumer


class Options:
    """Contains options for occheck.
    """

    def __init__(self):
        self.source_files = None
        self.list_checks = False
        self.output_stream = None
        self.output_format = None
        self.checks = ""
        self.check_options = None


class OCCheck:

    def __init__(self):
        self._check_names = []
        self._reporter = None
        self._current_file = None

    def check(self, files, check_options):
        """Check a list of files.
        """
        checks = self._prepare_checks(check_options)
        if not checks:
            return

        walker = ParseTreeWalker()

        for file in files:
            OCCheck._check_file(file, walker, checks)

    def add_checks(self, check_names):
        """Register checks in the check list.
        """
        new_checks = [check for check in check_names if check not in self._check_names]
        self._check_names.extend(new_checks)

    def set_reporter(self, reporter):
        self._reporter = reporter

    def dump_reports(self):
        if self._reporter:
            return self._reporter.dump()
        return ""

    def _prepare_diagnostic_consumer(self):
        consumer = DiagnosticConsumer(self._reporter)
        return consumer

    def _prepare_checks(self, check_options):
        checks = []
        diagnostic_consumer = self._prepare_diagnostic_consumer()

        for check_name in self._check_names:
            check = CheckRegistry.create_check(check_name)
            check.set_name(check_name)
            check.set_options(check_options)
            check.set_consumer(diagnostic_consumer)
            check.initialize()
            checks.append(check)

        return checks

    @classmethod
    def _check_file(cls, file_path, walker, checks):
        context = FileContext(file_path)
        if context.has_syntax_errors():
            # print("Warning: '%s' has syntax errors" % file_path)
            return

        # print("Checking: %s" % file_path)

        for check in checks:
            check.set_current_context(context)
            check.begin_check(file_path)
            walker.walk(check, context.get_ast())
            check.finish_check(file_path)


def get_source_files(source_files):
    """Returns a list of source file paths to check.
    """

    # TODO
    return source_files


def get_enabled_checks(checks):
    """Returns a list of enabled check names.
    """
    enabled_checks = []
    default_checks = 'readability-*'

    if not checks:
        checks = default_checks
    else:
        checks = '%s, %s' % (default_checks, checks)

    check_options = list(map(lambda x: x.strip(), checks.split(',')))

    available_checks = CheckRegistry.list_checks()
    available_checks.sort()

    for option in check_options:
        if option.startswith('-'):
            pattern = re.compile(fnmatch.translate(option[1:]))
            enabled_checks = list(filter(lambda x: not pattern.match(x), enabled_checks))
        else:
            pattern = re.compile(fnmatch.translate(option))
            extra = list(filter(lambda x: pattern.match(x), available_checks))

            # The latter option takes precedence.
            enabled_checks = list(filter(lambda x: x not in extra, enabled_checks))
            enabled_checks.extend(extra)

    return enabled_checks


def parse_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_files", metavar="<source>", nargs="*")
    parser.add_argument("--config", metavar="<filename>", dest="config_stream", type=argparse.FileType('r'),
                        help="Specifies a configuration in YAML format.")
    parser.add_argument("--checks", metavar="<string>",
                        help="Specifies a comma-separated list of globs with optional '-' prefix.")
    parser.add_argument("--list-checks", action='store_true',
                        help="List all enabled checks and exit. Use with -checks='*' to list all available checks")
    parser.add_argument("-o", metavar="<filename>", dest="output_stream", type=argparse.FileType('w'),
                        default=sys.stdout, help="File to store outputs in.")
    parser.add_argument("-f", metavar="<format>", dest="output_format", default="text",
                        help="Sets the output format. Available formats are 'json' and 'text'.")
    parser.add_argument("-v", "--version", action='version', version=__pkginfo__.version,
                        help="Display the version of this program.")

    if sys.argv[1:]:
        args = parser.parse_args()
    else:
        parser.parse_args(['--help'])
        sys.exit(1)

    options = Options()
    options.list_checks = args.list_checks
    options.output_stream = args.output_stream
    options.output_format = args.output_format
    options.source_files = get_source_files(args.source_files)

    if args.config_stream:
        config = yaml.load(args.config_stream, Loader=yaml.SafeLoader)
        options.checks = config.get("Checks", "")
        options.check_options = config.get("CheckOptions")

    if options.checks:
        options.checks = "%s, %s" % (options.checks, args.checks)
    else:
        options.checks = args.checks

    if not options.check_options:
        options.check_options = []

    return options


def redirect_checks():
    # This is a mapping from codecc rule name to occheck check name.
    checks_map = {
        "AvoidThrowingException": "coding-avoid-throwing-exception",
        "MaxLinesPerFunction": "readability-function-size",
        "MaxLineLength": "readability-line-length",
        "Indent": "readability-indent",
        "ClassNaming": "readability-identifier-naming",
        "MethodNaming": "readability-identifier-naming",
        "FunctionNaming": "readability-identifier-naming",
        "ParameterNaming": "readability-identifier-naming",
        "LocalVariableNaming": "readability-identifier-naming",
        "GlobalVariableNaming": "readability-identifier-naming",
        "MacroNaming": "readability-identifier-naming",
    }

    for key, value in checks_map.items():
        CheckRegistry.register_check(key, CheckRegistry.get_check(value))


def run_check():
    # Redirects CodeCC rules to occheck's own checks.
    redirect_checks()

    options = parse_options()
    enabled_checks = get_enabled_checks(options.checks)

    if options.list_checks:
        if not enabled_checks:
            print("No checks enabled.")
            sys.exit(1)

        print("Enabled checks:")
        for check in enabled_checks:
            print("    " + check)
        print("\n")
        sys.exit(0)

    if not enabled_checks:
        print("Warning: no checks enabled.")

    check = OCCheck()
    check.add_checks(enabled_checks)

    reporter = ReporterRegistry.create_reporter(options.output_format, options.output_stream)
    check.set_reporter(reporter)

    check.check(options.source_files, options.check_options)
    reports = check.dump_reports()

    if reports:
        options.output_stream.write(reports)
        options.output_stream.write("\n\n")

    sys.exit(0)


if __name__ == '__main__':
    run_check()
