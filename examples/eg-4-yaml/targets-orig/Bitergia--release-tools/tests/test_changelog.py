#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2019 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>..
#
# Authors:
#     Santiago Dueñas <sduenas@bitergia.com>
#     Venu Vardhan Reddy Tekula <venu@bitergia.com>
#

import os
import unittest
import unittest.mock

import click.testing
import yaml

from release_tools import changelog
from release_tools.repo import RepositoryError

CHANGELOG_ENTRIES_DIR_ERROR = (
    "Error: Changelog entries directory is needed to continue."
)
CHANGELOG_ENTRY_ALREADY_EXISTS_ERROR = (
    "Error: Changelog entry new-change.yml already exists. Use '--overwrite' to replace it."
)
EMPTY_CONTENT_ERROR = (
    "Error: Aborting due to empty entry content"
)
INVALID_TITLE_ERROR = (
    r"Error: Invalid value for \"|\'-t\"|\' / \"|\'--title\"|\': title cannot be empty"
)
INVALID_CATEGORY_ERROR = [
    "Error",
    r" Invalid value for \"|\'-c\"|\' / \"|\'--category\"|\'",
    " valid options are ['added', 'fixed', 'changed', 'deprecated', 'removed', 'security', 'performance', 'other']"
]
INVALID_CATEGORY_INDEX_ERROR = (
    r"Error: Invalid value for \"|\'-c\"|\' / \"|\'--category\"|\': please select an index between 1 and 8"
)
MOCK_OS_ERROR = (
    "Error: Unable to create directory. mock os error"
)
MOCK_REPOSITORY_ERROR = (
    "Error: mock repository error"
)
CHANGELOG_ENTRY_CONTENT = (
    """---\ntitle: new change\ncategory: fixed\nauthor: null\nissue: null\nnotes: null"""
)


class TestChangelog(unittest.TestCase):
    """Unit tests for changelog script"""

    @unittest.mock.patch('release_tools.changelog.Project')
    def test_entry_is_created(self, mock_project):
        """Check whether a changelog entry is created"""

        runner = click.testing.CliRunner()
        user_input = "new change\n1\ny"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath

            result = runner.invoke(changelog.changelog, ['--no-editor'],
                                   input=user_input)
            self.assertEqual(result.exit_code, 0)

            # Check entry and contents
            filepath = os.path.join(dirpath, 'new-change.yml')

            self.assertEqual(os.path.exists(filepath), True)

            with open(filepath, mode='r') as fd:
                entry = yaml.safe_load(fd)
                self.assertEqual(entry['title'], 'new change')
                self.assertEqual(entry['category'], 'added')
                self.assertEqual(entry['author'], None)
                self.assertEqual(entry['issue'], None)
                self.assertEqual(entry['notes'], None)

    @unittest.mock.patch('release_tools.changelog.Project')
    def test_entry_repository_error(self, mock_project):
        """Check if it stops working when it encounters RepositoryError exception"""

        runner = click.testing.CliRunner(mix_stderr=False)
        user_input = "new change\n1\ny"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.side_effect = RepositoryError('mock repository error')

            result = runner.invoke(changelog.changelog, ['--no-editor'],
                                   input=user_input)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertEqual(lines[-2], MOCK_REPOSITORY_ERROR)

            # Nothing was created in the directory
            self.assertEqual(len(os.listdir(fs)), 0)

    @unittest.mock.patch('release_tools.changelog.Project')
    def test_entry_dry_run(self, mock_project):
        """Check if a changelog entry is created when --dry-run flag is enabled"""

        runner = click.testing.CliRunner(mix_stderr=False)
        user_input = "y\n"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath

            # Create an entry first
            params = [
                '--title', 'new change',
                '--category', 'fixed',
                '--no-editor', '--dry-run'
            ]
            result = runner.invoke(changelog.changelog, params,
                                   input=user_input)
            self.assertEqual(result.exit_code, 0)

            self.assertEqual(os.path.exists(dirpath), True)

            filepath = os.path.join(dirpath, 'new-change.yml')
            self.assertEqual(os.path.exists(filepath), False)

            lines = result.stdout.split('\n\n')
            self.assertEqual(lines[-2], CHANGELOG_ENTRY_CONTENT)

    @unittest.mock.patch('release_tools.changelog.Project')
    def test_entry_is_not_overwritten(self, mock_project):
        """Check whether an existing changelog entry is not replaced"""

        runner = click.testing.CliRunner(mix_stderr=False)
        user_input = "y\n"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath

            # Create an entry first
            params = [
                '--title', 'new change',
                '--category', 'fixed',
                '--no-editor'
            ]
            result = runner.invoke(changelog.changelog, params,
                                   input=user_input)
            self.assertEqual(result.exit_code, 0)

            # Try to replace it
            params = [
                '--title', 'new change',
                '--category', 'added',
                '--no-editor'
            ]
            result = runner.invoke(changelog.changelog, params)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertEqual(lines[-2], CHANGELOG_ENTRY_ALREADY_EXISTS_ERROR)

            # Check entry and contents. They did not change.
            filepath = os.path.join(dirpath, 'new-change.yml')

            with open(filepath, mode='r') as fd:
                entry = yaml.safe_load(fd)
                self.assertEqual(entry['title'], 'new change')
                self.assertEqual(entry['category'], 'fixed')
                self.assertEqual(entry['author'], None)
                self.assertEqual(entry['issue'], None)
                self.assertEqual(entry['notes'], None)

    @unittest.mock.patch('release_tools.changelog.Project')
    def test_overwrite_entry(self, mock_project):
        """Check if it overwrites am existing changelog entry when the proper flag is set"""

        runner = click.testing.CliRunner(mix_stderr=False)
        user_input = "y\n"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath

            # Create an entry first
            params = [
                '--title', 'new change',
                '--category', 'fixed',
                '--no-editor'
            ]
            result = runner.invoke(changelog.changelog, params,
                                   input=user_input)
            self.assertEqual(result.exit_code, 0)

            # Check entry and contents
            filepath = os.path.join(dirpath, 'new-change.yml')

            with open(filepath, mode='r') as fd:
                entry = yaml.safe_load(fd)
                self.assertEqual(entry['title'], 'new change')
                self.assertEqual(entry['category'], 'fixed')
                self.assertEqual(entry['author'], None)
                self.assertEqual(entry['issue'], None)
                self.assertEqual(entry['notes'], None)

            # Try to replace it
            params = [
                '--title', 'new change',
                '--category', 'added',
                '--overwrite', '--no-editor'
            ]
            result = runner.invoke(changelog.changelog, params)
            self.assertEqual(result.exit_code, 0)

            # Check entry and contents. They should have changed
            with open(filepath, mode='r') as fd:
                entry = yaml.safe_load(fd)
                self.assertEqual(entry['title'], 'new change')
                self.assertEqual(entry['category'], 'added')
                self.assertEqual(entry['author'], None)
                self.assertEqual(entry['issue'], None)
                self.assertEqual(entry['notes'], None)

    @unittest.mock.patch('release_tools.changelog.Project')
    @unittest.mock.patch('release_tools.changelog.click.edit')
    def test_abort_entry_empty(self, mock_edit, mock_project):
        """Check if it stops the process when the content of the entry to create is empty"""

        runner = click.testing.CliRunner(mix_stderr=False)
        user_input = "new change\n1\ny"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath

            mock_edit.return_value = ""

            result = runner.invoke(changelog.changelog,
                                   input=user_input)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertEqual(lines[-2], EMPTY_CONTENT_ERROR)

    @unittest.mock.patch('release_tools.changelog.Project')
    def test_create_entries_dir(self, mock_project):
        """Check if the entries dir is created when it does not exist"""

        runner = click.testing.CliRunner()

        # 'y' means the user wants to create the dir when asked
        user_input = "new change\n1\ny"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath

            result = runner.invoke(changelog.changelog, ['--no-editor'],
                                   input=user_input)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(os.path.exists(dirpath), True)

            filepath = os.path.join(dirpath, 'new-change.yml')
            self.assertEqual(os.path.exists(filepath), True)

    @unittest.mock.patch('release_tools.changelog.Project')
    def test_entries_dir_not_created(self, mock_project):
        """Check if it stops working when the entries dir is not created"""

        runner = click.testing.CliRunner(mix_stderr=False)

        # 'n' means the user refuses to create the dir when asked
        user_input = "new change\n1\nn"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath

            result = runner.invoke(changelog.changelog, ['--no-editor'],
                                   input=user_input)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertEqual(lines[-2], CHANGELOG_ENTRIES_DIR_ERROR)

            # Nothing was created in the directory
            self.assertEqual(len(os.listdir(fs)), 0)

    @unittest.mock.patch('release_tools.changelog.Project')
    @unittest.mock.patch('release_tools.changelog.os.makedirs')
    def test_entries_dir_os_error(self, mock_os, mock_project):
        """Check if it stops working when it encounters OSError exception"""

        runner = click.testing.CliRunner(mix_stderr=False)

        user_input = "new change\n1\ny"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_os.side_effect = OSError('mock os error')
            mock_project.return_value.unreleased_changes_path = dirpath

            result = runner.invoke(changelog.changelog, ['--no-editor'],
                                   input=user_input)
            self.assertEqual(result.exit_code, 1)

            lines = result.stderr.split('\n')
            self.assertEqual(lines[-2], MOCK_OS_ERROR)

            # Nothing was created in the directory
            self.assertEqual(len(os.listdir(fs)), 0)

    def test_validate_content(self):
        """Check if the content of the entry file is valid."""

        good_entry = "---\ntitle: new change\ncategory: fixed\n"
        good_entry += "author: john\nissue: 2\nnotes: null\n"

        result = changelog.validate_changelog_content(content=good_entry)
        self.assertEqual(result, True)

        bad_entry = "---\ntitle: new change\ncategory: fixed\n"
        bad_entry += "author: :\nissue: 2\nnotes: null\n"

        result = changelog.validate_changelog_content(content=bad_entry)
        self.assertEqual(result, False)

    @unittest.mock.patch('release_tools.changelog.Project')
    @unittest.mock.patch('release_tools.changelog.validate_changelog_content')
    def test_validate_good_entry(self, mock_content, mock_project):
        """Check if it creates the file if the content is invalid."""

        runner = click.testing.CliRunner(mix_stderr=False)
        user_input = "new change\n1\ny"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath
            mock_content.return_value = True

            result = runner.invoke(changelog.changelog, ['--no-editor'],
                                   input=user_input)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(os.path.exists(dirpath), True)

            filepath = os.path.join(dirpath, 'new-change.yml')
            self.assertEqual(os.path.exists(filepath), True)

    @unittest.mock.patch('release_tools.changelog.Project')
    @unittest.mock.patch('release_tools.changelog.validate_changelog_content')
    def test_validate_bad_entry(self, mock_content, mock_project):
        """Check if it doesn't create the file if the content is invalid."""

        runner = click.testing.CliRunner(mix_stderr=False)

        # 'n' means the user refuses to edit the entry when there is an error
        user_input = "new change\n1\ny\nn"

        with runner.isolated_filesystem() as fs:
            dirpath = os.path.join(fs, 'releases', 'unreleased')
            mock_project.return_value.unreleased_changes_path = dirpath
            mock_content.return_value = False

            result = runner.invoke(changelog.changelog, ['--no-editor'],
                                   input=user_input)
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(os.path.exists(dirpath), True)

            filepath = os.path.join(dirpath, 'new-change.yml')
            self.assertEqual(os.path.exists(filepath), False)

    @unittest.mock.patch('release_tools.changelog.click')
    def test_edit_invalid_changelog_entry(self, mock_click):
        """Check if it gives an option to edit the file if the content is invalid."""

        good_entry = "---\ntitle: new change\ncategory: fixed\n"
        good_entry += "author: john\nissue: 2\nnotes: null\n"

        bad_entry = "---\ntitle: new change\ncategory: fixed\n"
        bad_entry += "author: :\nissue: 2\nnotes: null\n"

        mock_click.edit.return_value = good_entry

        result = changelog.validate_changelog_entry(bad_entry)
        self.assertEqual(result, good_entry)

    def test_invalid_title(self):
        """Check whether title param is validated correctly"""

        runner = click.testing.CliRunner(mix_stderr=False)

        # Empty titles are not allowed
        result = runner.invoke(changelog.changelog, ['--title', ''])
        self.assertEqual(result.exit_code, 2)

        lines = result.stderr.split('\n')
        self.assertRegex(lines[-2], INVALID_TITLE_ERROR)

        # Only whitespaces are not allowed
        result = runner.invoke(changelog.changelog, ['--title', ' '])
        self.assertEqual(result.exit_code, 2)

        lines = result.stderr.split('\n')
        self.assertRegex(lines[-2], INVALID_TITLE_ERROR)

        # Only control characters are not allowed
        result = runner.invoke(changelog.changelog, ['--title', '\n\r\n'])
        self.assertEqual(result.exit_code, 2)
        self.assertRegex(lines[-2], INVALID_TITLE_ERROR)

    def test_invalid_category(self):
        """Check whether category param is validated correctly"""

        runner = click.testing.CliRunner(mix_stderr=False)

        # Invalid categories are not allowed
        result = runner.invoke(changelog.changelog, ['--category', 'invalid'])
        self.assertEqual(result.exit_code, 2)

        lines = result.stderr.split('\n')
        lines = lines[-2].split(':')
        self.assertEqual(lines[0], INVALID_CATEGORY_ERROR[0])
        self.assertRegex(lines[1], INVALID_CATEGORY_ERROR[1])
        self.assertEqual(lines[2], INVALID_CATEGORY_ERROR[2])

        # Invalid indexes are not allowed
        result = runner.invoke(changelog.changelog, ['--category', '42'])
        self.assertEqual(result.exit_code, 2)

        lines = result.stderr.split('\n')
        self.assertRegex(lines[-2], INVALID_CATEGORY_INDEX_ERROR)


if __name__ == '__main__':
    unittest.main()
