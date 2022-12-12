"""First group of pytest test cases for phmdoctest."""
import configparser
import copy
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

import phmdoctest
import phmdoctest.cases
from phmdoctest.fenced import Role
import phmdoctest.main
import phmdoctest.simulator
import phmdoctest.tool


# Caution:
# This test file is run by pytest.
# The call to invoke_and_pytest() will start pytest in a
# subprocess.
# Pytest captures stdout and so does CliRunner.invoke().


class TestSameVersions:
    """Verify same release version string in all places.

    Obtain the version string from various places in the source tree
    and check that they are all the same.
    Compare all the occurrences to phmdoctest.__version__.
    This test does not prove the version is correct.
    Whitespace may be significant in some cases.
    """

    package_version = phmdoctest.__version__

    def verify_found_in_file(self, filename, format_spec="{}"):
        """Format the package version and look for result in caller's file."""
        looking_for = format_spec.format(self.package_version)
        text = Path(filename).read_text(encoding="utf-8")
        assert looking_for in text

    def test_readme_md(self):
        """Check the version near the top of README.md."""
        self.verify_found_in_file("README.md", "# phmdoctest {}")
        self.verify_found_in_file("README.md", "section Development tools API {}")

    def test_configuring_md(self):
        """Check the version near the top of doc/configuring.md."""
        self.verify_found_in_file(
            "doc/configuring.md", "section Development tools API {}"
        )

    def test_index_rst(self):
        """Check the version is anywhere in index.rst."""
        self.verify_found_in_file("index.rst", "phmdoctest {}\n=============")

    def test_recent_changes(self):
        """Check the version is anywhere in recent_changes.md."""
        self.verify_found_in_file("doc/recent_changes.md", "{} - ")

    def test_conf_py_release(self):
        """Check version in the release = line in conf.py."""
        self.verify_found_in_file("conf.py", 'release = "{}"')

    def test_setup_cfg(self):
        """Check the version in setup.cfg."""
        config = configparser.ConfigParser()
        config.read("setup.cfg")
        metadata_version = config["metadata"]["version"]
        assert metadata_version == self.package_version

    def test_deploy_github_action(self):
        """Check the ref: value in the GitHub deploy.yml action."""
        self.verify_found_in_file(".github/workflows/deploy.yml", "\n        ref: v{}")

    def test_api_rst(self):
        """Check the version is anywhere in api.rst."""
        self.verify_found_in_file("doc/api.rst", "version {}")

    def test_actions_usage(self):
        """Check the version in the link  is anywhere in actions_usage.md."""
        self.verify_found_in_file("doc/actions_usage.md", "blob/v{}")


def string_to_dependencies(text: str) -> set:
    """Return the set of pip dependencies from a multi-line string.

    Whitespace and empty lines are not significant.
    Comment lines are ignored.
    """
    lines = text.splitlines()
    lines = [line for line in lines if not line.startswith("#")]
    collapsed_lines = [line.replace(" ", "") for line in lines if line]
    items = set(collapsed_lines)
    if "" in items:
        items.remove("")  # empty string from blank lines
    return items


def setup_dependencies(section, option) -> set:
    """Extract set of dependencies from setup.cfg section/option."""
    config = configparser.ConfigParser()
    config.read("setup.cfg", encoding="utf-8")
    text = config.get(section, option)
    return string_to_dependencies(text)


def file_dependencies(filename: str) -> set:
    """Extract set of dependencies from a requirements.txt file."""
    text = Path(filename).read_text(encoding="utf-8")
    return string_to_dependencies(text)


def test_install_requires():
    """setup.cfg install_requires == requirements.txt."""
    setup_values = setup_dependencies("options", "install_requires")
    requirements_values = file_dependencies("requirements.txt")
    assert setup_values == requirements_values


def test_extras_require_test():
    """setup.cfg extras_require|test key is up to date with tests/requirements.txt.

    The test key should have at least all the requirements from the
    requirements file.  It can have more.
    """
    setup_values = setup_dependencies("options.extras_require", "test")
    requirements_values = file_dependencies("tests/requirements.txt")
    assert requirements_values.issubset(setup_values)


def test_extras_require_inspect():
    """setup.cfg extras_require|inspect key == tests/requirements_inspect.txt."""
    setup_values = setup_dependencies("options.extras_require", "inspect")
    requirements_values = file_dependencies("tests/requirements_inspect.txt")
    assert setup_values == requirements_values


def test_doc_requirements_file():
    """
    For the Sphinx documentation builds on GitHUb and readthedocs.org (RTD)
    versions are described by the file doc/requirements.txt.
    For Sphinx autodoc the phmdoctest dependencies Click and monotable
    are installed so that the RTD build can import phmdoctest to look
    for docstrings.
    Make sure the docs build install the same versions listed by
    requirements.txt at the repository root.
    """
    packages = ["Click", "monotable", "commonmark", "tomli"]
    setup_versions = {}
    setup_text = Path("requirements.txt").read_text(encoding="utf-8")
    setup_requirements = setup_text.splitlines()
    for line in setup_requirements:
        for package in packages:
            if line.startswith(package):
                setup_versions[package] = line

    doc_versions = {}
    doc_text = Path("doc/requirements.txt").read_text(encoding="utf-8")
    doc_requirements = doc_text.splitlines()
    for line in doc_requirements:
        for package in packages:
            if line.startswith(package):
                doc_versions[package] = line

    for package in packages:
        assert setup_versions[package] == doc_versions[package]


def test_readthedocs_python_version():
    """The build docs Python version == workflow step Python version."""
    with open(".readthedocs.yml", "r", encoding="utf-8") as frtd:
        rtd = yaml.safe_load(frtd)
    with open(".github/workflows/ci.yml", "r", encoding="utf-8") as fwrk:
        workflow = yaml.safe_load(fwrk)
    step = workflow["jobs"]["docs"]["steps"][1]
    assert "Setup Python" in step["name"]
    workflow_version = step["with"]["python-version"]
    assert rtd["python"]["version"] == workflow_version


@pytest.mark.skipif(sys.version_info < (3, 7), reason="requires >=py3.7")
def test_trailing_whitespace():
    """Expose files in repository that have lines with trailing spaces.

    Note- The IDE and/or git may be configurable to prevent trailing spaces
    making this test redundant.
    To run just this test: pytest -v tests -k test_trailing_whitespace
    """
    completed = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    files = completed.stdout.splitlines()
    found_trailing_spaces = False
    for name in files:
        text = Path(name).read_text(encoding="utf-8")
        lines = text.splitlines()
        for num, got in enumerate(lines, start=1):
            wanted = got.rstrip()
            if got != wanted:
                print(name, "line", num, "has trailing whitespace.")
                found_trailing_spaces = True
    assert not found_trailing_spaces, "Line has trailing whitespace."


def test_empty_output_block_report(example_tester, checker):
    """Empty output block get del'd."""
    simulator_status = example_tester(
        "phmdoctest tests/empty_output_block.md" " --report --outfile discarded.py",
        want_file_name=None,
        pytest_options=["--doctest-modules", "-v"],
    )
    assert simulator_status.runner_status.exit_code == 0
    assert simulator_status.pytest_exit_code == 0
    stdout = simulator_status.runner_status.stdout
    want = Path("tests/empty_output_report.txt").read_text(encoding="utf-8")
    checker(a=want, b=stdout)


def test_empty_code_block_report(example_tester, checker):
    """Empty code block and associated output block get del'd."""
    simulator_status = example_tester(
        "phmdoctest tests/empty_code_block.md" " --report --outfile discarded.py",
        want_file_name=None,
        pytest_options=["--doctest-modules", "-v"],
    )
    assert simulator_status.runner_status.exit_code == 0
    assert simulator_status.pytest_exit_code == 0
    stdout = simulator_status.runner_status.stdout
    want = Path("tests/empty_code_report.txt").read_text(encoding="utf-8")
    checker(a=want, b=stdout)


def test_no_markdown_fenced_code_blocks(example_tester):
    """Show --report works when there is nothing to report."""
    simulator_status = example_tester(
        "phmdoctest tests/no_fenced_code_blocks.md" " --report --outfile discarded.py",
        want_file_name=None,
        pytest_options=["--doctest-modules", "-v"],
    )
    assert simulator_status.runner_status.exit_code == 0
    assert simulator_status.pytest_exit_code == 0
    stdout = simulator_status.runner_status.stdout
    assert "0 test cases." in stdout


def test_code_does_not_print_fails():
    """Show empty stdout mis-compares with non-empty output block."""
    command = "phmdoctest tests/does_not_print.md --outfile discarded.py"
    simulator_status = phmdoctest.simulator.run_and_pytest(
        well_formed_command=command, pytest_options=["--doctest-modules", "-v"]
    )
    assert simulator_status.runner_status.exit_code == 0
    assert simulator_status.pytest_exit_code == 1


def test_more_printed_than_expected_fails():
    """Show pytest fails when more lines are printed than expected."""
    command = "phmdoctest tests/missing_some_output.md --outfile discarded.py"
    simulator_status = phmdoctest.simulator.run_and_pytest(
        well_formed_command=command, pytest_options=["--doctest-modules", "-v"]
    )
    assert simulator_status.runner_status.exit_code == 0
    assert simulator_status.pytest_exit_code == 1


def test_more_expected_than_printed_fails():
    """Show pytest fails when more lines are printed than expected."""
    command = "phmdoctest tests/extra_line_in_output.md --outfile discarded.py"
    simulator_status = phmdoctest.simulator.run_and_pytest(
        well_formed_command=command, pytest_options=["--doctest-modules", "-v"]
    )
    assert simulator_status.runner_status.exit_code == 0
    assert simulator_status.pytest_exit_code == 1


def test_skip_same_block_twice():
    """Show identifying a skipped code block more than one time is OK."""
    command = (
        'phmdoctest doc/example2.md --skip "Python 3.7" --skip LAST'
        " --skip LAST --report --outfile discarded.py"
    )
    simulator_status = phmdoctest.simulator.run_and_pytest(
        well_formed_command=command, pytest_options=["--doctest-modules", "-v"]
    )
    assert simulator_status.runner_status.exit_code == 0
    assert simulator_status.pytest_exit_code == 0


def test_pytest_session_fails(example_tester):
    """Make sure pytest fails due to incorrect session output in the .md file.

    Generate a pytest that fails pytest.
    """
    simulator_status = example_tester(
        "phmdoctest tests/bad_session_output.md --outfile discarded.py",
        want_file_name=None,
        pytest_options=["--doctest-modules", "-v"],
    )
    assert simulator_status.pytest_exit_code == 1


def test_project_md(example_tester):
    """Make sure that project.md generates a file that passes pytest."""
    simulator_status = example_tester(
        "phmdoctest project.md --outfile discarded.py",
        want_file_name=None,
        pytest_options=["--doctest-modules", "-v"],
    )
    assert simulator_status.runner_status.exit_code == 0
    assert simulator_status.pytest_exit_code == 0


def test_example2_report(example_tester, checker):
    """Check example2_report.txt."""
    simulator_status = example_tester(
        'phmdoctest doc/example2.md --skip "Python 3.7" --skip LAST --report'
        " --outfile discarded.py",
        want_file_name=None,
        pytest_options=None,
    )
    assert simulator_status.runner_status.exit_code == 0
    assert simulator_status.pytest_exit_code is None
    stdout = simulator_status.runner_status.stdout
    want = Path("tests/example2_report.txt").read_text(encoding="utf-8")
    checker(a=want, b=stdout)


def test_setup_with_inline(example_tester):
    """Do inline annotations in setup and teardown blocks."""
    command = (
        "phmdoctest tests/setup_with_inline.md -u FIRST -d LAST --outfile discarded.py"
    )
    simulator_status = example_tester(
        well_formed_command=command,
        want_file_name="tests/test_setup_with_inline.py",
        pytest_options=["--doctest-modules", "-v"],
    )
    assert simulator_status.runner_status.exit_code == 0


def test_blanklines_in_output():
    """Expected output has empty lines and no doctest <BLANKLINE>."""
    command = "phmdoctest tests/output_has_blank_lines.md --outfile discarded.py"
    simulator_status = phmdoctest.simulator.run_and_pytest(
        well_formed_command=command,
        pytest_options=["--doctest-modules", "-v"],
    )
    assert simulator_status.runner_status.exit_code == 0
    assert simulator_status.pytest_exit_code == 0


def test_one_mark_skip():
    """A single <!--phmdoctest-mark.skip--> directive."""
    command = "phmdoctest tests/one_mark_skip.md --outfile discarded.py"
    simulator_status = phmdoctest.simulator.run_and_pytest(
        well_formed_command=command,
        pytest_options=["--doctest-modules", "-v"],
    )
    assert simulator_status.runner_status.exit_code == 0
    assert simulator_status.pytest_exit_code == 0


def test_no_namespace_manager_call_generated():
    """phmdoctest.cases.call_namespace_manager() returns empty string."""
    # In cases.py there is never a call to call_namespace_manager()
    # with neither share-names or clear-names directives.
    # Coverage reports a missing statement.
    # Fix by calling with a block that doesn't have those directives.
    with open("tests/direct.md", "r", encoding="utf-8") as fp:
        blocks = phmdoctest.fenced.convert_nodes(phmdoctest.tool.fenced_block_nodes(fp))
    code_line = phmdoctest.cases.call_namespace_manager(blocks[0])
    assert code_line == ""


def test_fenced_role_skipping():
    """Check FencedBlock.skip() for blocks with different roles."""
    # Obtain a single FencedBlock instance to try with different roles.
    # Make a copy of the first block below, modify the role,
    # and call skip() on it.  The good roles don't raise an assertion,
    # the bad roles do.
    with open("tests/direct.md", "r", encoding="utf-8") as fp:
        blocks = phmdoctest.fenced.convert_nodes(phmdoctest.tool.fenced_block_nodes(fp))
    good_roles = [
        Role.CODE,
        Role.OUTPUT,
        Role.SESSION,
        Role.SKIP_CODE,
        Role.SKIP_OUTPUT,
        Role.SKIP_SESSION,
    ]
    for role in good_roles:
        block = copy.copy(blocks[0])
        block.role = role
        block.skip(pattern="no-assertion-expected")

    bad_roles = [
        Role.UNKNOWN,
        Role.SETUP,
        Role.TEARDOWN,
        Role.DEL_CODE,
        Role.DEL_OUTPUT,
    ]
    for role in bad_roles:
        block = copy.copy(blocks[0])
        block.role = role
        with pytest.raises(AssertionError) as exc_info:
            block.skip(pattern="assertion-is-expected")
        assert "cannot skip a block with " + str(role) in str(exc_info.value)

    # Assure that every Role enum value gets tested.
    number_of_roles_tried = len(set(good_roles + bad_roles))
    assert len(Role) == number_of_roles_tried, "missed some roles"
