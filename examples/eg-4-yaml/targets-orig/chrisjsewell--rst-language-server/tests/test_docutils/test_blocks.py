import os
import sys

from docutils import frontend, utils
from docutils.parsers import rst
import pytest
import yaml

from rst_lsp.docutils_ext.inliner_base import Inliner
from rst_lsp.docutils_ext.block_lsp import RSTParserCustom


def load_yaml(path):
    with open(path) as fp:
        data = yaml.safe_load(fp)
    return data


def run_parser(case, parser_class, inliner=None):
    source = "\n".join(case["in"])
    expected = "\n".join(case["out"])

    parser = parser_class(inliner=inliner)
    option_parser = frontend.OptionParser(components=(parser_class,))
    settings = option_parser.get_default_values()
    settings.report_level = 5
    settings.halt_level = 5
    # settings.debug = package_unittest.debug

    document = utils.new_document("test data", settings)
    parser.parse(source, document)
    output = document.pformat()
    # Normalize line endings:
    if expected:
        expected = "\n".join(expected.rstrip().splitlines())
    if output:
        output = "\n".join(output.rstrip().splitlines())

    try:
        assert output == expected
    except AssertionError:
        yaml.dump(output.splitlines(), sys.stdout)
        raise


@pytest.mark.parametrize(
    "name,number,case",
    [
        (name, i, case)
        for name, cases in load_yaml(
            os.path.join(os.path.dirname(__file__), "inputs/test_block_markup.yaml")
        ).items()
        for i, case in enumerate(cases)
    ],
)
def test_block_markup(name, number, case):
    run_parser(case, parser_class=rst.Parser, inliner=Inliner())


@pytest.mark.parametrize(
    "name,number,case",
    [
        (name, i, case)
        for name, cases in load_yaml(
            os.path.join(os.path.dirname(__file__), "inputs/test_block_lsp.yaml")
        ).items()
        for i, case in enumerate(cases)
    ],
)
def test_block_markup_pos(name, number, case):
    run_parser(case, parser_class=RSTParserCustom, inliner=Inliner())
