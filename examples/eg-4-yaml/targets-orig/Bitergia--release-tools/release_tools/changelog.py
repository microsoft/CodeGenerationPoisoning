#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Bitergia
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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     Santiago Dueñas <sduenas@bitergia.com>
#
# Note:
#
# This script is based on the work made by GitLab project to generate
# releases automatically. The code is licensed under the terms of the
# MIT license. For more info, please check:
#
#   * https://gitlab.com/gitlab-org/gitlab/blob/master/bin/changelog
#   * https://gitlab.com/gitlab-org/gitlab/blob/master/LICENSE
#

"""
Script to create unreleased Changelog entries.

This tool will create valid Changelog entries for a Git
repository. Entries will be YAML files, storing title,
type and author of the changes. Metadata can be also added.

The tool provides an interactive mode to help the user to
define the relevant fields.
"""

import os

import click
import yaml

from release_tools.entry import (CategoryChange,
                                 ChangelogEntry,
                                 determine_filepath)
from release_tools.project import Project
from release_tools.repo import RepositoryError


def title_prompt():
    """Prompt title to read the title of a change"""

    prompt_msg = ">> Please specify the title of your change"
    return prompt_msg


def category_prompt():
    """Prompt category to read the type of a change"""

    prompt_msg = ">> Please specify the category of your change\n\n"
    prompt_msg += "\n".join(["{}. {}".format(cat.value, cat.title) for cat in CategoryChange])
    prompt_msg += "\n\n"
    return prompt_msg


def validate_title(ctx, param, value):
    """Check title option values."""

    value = value.strip("\n\r ")

    if not value:
        raise click.BadParameter("title cannot be empty")
    return value


def validate_category(ctx, param, value):
    """Check category option values.

    Valid values for a category are integer indexes and
    strings.
    """
    # Check if the value is an index
    try:
        value = int(value)
    except ValueError:
        # The value is not an index.
        # Check if it is a valid category string.
        try:
            CategoryChange[value.upper()]
        except KeyError:
            msg = "valid options are {}".format(CategoryChange.values())
            raise click.BadParameter(msg)
        else:
            return value

    # Check if the index is in range.
    try:
        category = CategoryChange(value).category
        return category
    except ValueError:
        msg = "please select an index between 1 and {}".format(len(CategoryChange))
        raise click.BadParameter(msg)


@click.command()
@click.option('-t', '--title', prompt=title_prompt(),
              callback=validate_title,
              help="Title for the changelog entry.")
@click.option('-c', '--category', prompt=category_prompt(),
              callback=validate_category,
              help="The category of the change.")
@click.option('--dry-run', is_flag=True,
              help="Do not generate an entry. Print to the standard output instead.")
@click.option('--overwrite', is_flag=True,
              help="Force to replace an existing entry.")
@click.option('--editor/--no-editor', default=True,
              help="Open entry in the default editor.")
def changelog(title, category, dry_run, overwrite, editor):
    """Interactive tool to create unreleased Changelog entries.

    This tool will help you to create valid Changelog entries
    for a Git repository. You will need to run this script inside
    that repository.

    It will guide you to create a new entry. At the end of the process,
    a text editor will open to let you review the entry and make the
    final changes. The editor will be the default defined in your
    system.

    You can skip some parts of the process providing information
    in advance such as the title ('-t') or the category ('-c')
    of the entry.

    New entries will be stored in "releases/unreleased" directory.
    This directory must be available under the Git root path. If you
    don't want to create a new entry and see only the final result,
    please active '--dry-run' flag.

    In the case an entry with the same title already exists, an error
    will be raised. Use '--overwrite' to force to replace the existing
    entry.

    You can also use this tool to create entries in a Git submodule.
    Just run the script under the submodule directory.
    """
    click.echo()

    try:
        project = Project(os.getcwd())
    except RepositoryError as e:
        raise click.ClickException(e)

    dirpath = check_changelog_entries_dir(project)
    content = create_changelog_entry_content(title, category,
                                             run_editor=editor)
    content = validate_changelog_entry(content)

    click.echo()

    if dry_run:
        click.echo(content)
    else:
        write_changelog_entry(dirpath, title, content,
                              overwrite=overwrite)


def check_changelog_entries_dir(project):
    """Check and create the changelog directory."""

    dirpath = project.unreleased_changes_path

    if os.path.exists(dirpath):
        return dirpath

    click.echo("Error: Changelog entries directory does not exist.")

    if not click.confirm("Do you want to create it?"):
        msg = "Changelog entries directory is needed to continue."
        raise click.ClickException(msg)

    try:
        os.makedirs(dirpath, mode=0o755)
    except OSError as ex:
        msg = "Unable to create directory. {}".format(str(ex))
        raise click.ClickException(msg)
    else:
        click.echo("New directory {} created".format(dirpath))

    return dirpath


def create_changelog_entry_content(title, category, author=None, issue=None,
                                   run_editor=True):
    """Generates the content of a changelog entry."""

    entry = ChangelogEntry(title, category, author=author, issue=issue)
    contents = entry.to_dict()
    stream = yaml.dump(contents, sort_keys=False,
                       explicit_start=True)

    # Allow the user to edit the final content of the entry
    if run_editor:
        content = click.edit(stream)
    else:
        content = stream

    return content


def validate_changelog_content(content):
    """Validate the contents of an entry in a file."""

    if not content:
        msg = "Aborting due to empty entry content"
        raise click.ClickException(msg)

    try:
        data = yaml.safe_load(content)
        return True
    except yaml.YAMLError as exc:
        pm = exc.problem_mark
        click.echo("Error: Invalid format on line {} at position {}".format(pm.line, pm.column))
        return False


def validate_changelog_entry(content):
    """Checks if the file has a valid format."""

    is_valid = False
    while not is_valid:
        is_valid = validate_changelog_content(content)

        if not is_valid:
            if click.confirm("The changes will be lost if the file is invalid.\nDo you want to edit it?",
                             default=True, abort=True):
                # Allow the user to edit the content of the entry
                content = click.edit(content)

    return content


def write_changelog_entry(dirpath, title, content, overwrite=False):
    """Store the contents of an entry in a file."""

    filepath = determine_filepath(dirpath, title)

    mode = 'w' if overwrite else 'x'

    try:
        filename = os.path.basename(filepath)

        with open(filepath, mode=mode) as f:
            f.write(content)
    except FileExistsError:
        msg = "Changelog entry {} already exists. Use '--overwrite' to replace it.".format(filename)
        raise click.ClickException(msg)
    else:
        click.echo("Changelog entry '{}' created".format(filename))


if __name__ == '__main__':
    changelog()
