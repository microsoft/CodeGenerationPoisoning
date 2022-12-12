# Copyright (c) 2020-20201, LE GOFF Vincent
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.

"""YAML concrete parser.

This parser uses the YAML format to read and write blueprints.  It uses
the filesystem to store and retrieve data.

Options:
    directory (str): the directory name where blueprints are stored on
            disk.  To change this setting, edit "BLUEPRINT_DIRECTORY".
    backup (bool): whether to use a backup mode or not.  It is
            recommended to do so.  A backup mode will ensure that
            files are not completely lost for each iteration.
            To set this setting, change "BLUEPRINT_BACKUP".
            By default, the backup mode is enabled.

"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import yaml

from data.base import db
from data.blueprints.blueprint import Blueprint
from data.blueprints.log import logger
from data.blueprints.parser.base import AbstractParser
from data.handlers.blueprints import BlueprintHandler

def str_presenter(dumper, data):
    """Force using the | format with multiline strings."""
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data,
                style='|')

    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, str_presenter)

class YAMLParser(AbstractParser):

    """
    YAML parser for blueprints.

    This parser uses the YAML format to read and write individual
    documents.  It stores these documents in files.

    Options:
        directory (str): the location of the YML blueprint files.
                         Default to 'blueprints/'.
        backup (bool): whether to use a backup mode.
                       Default to `true`.

    """

    def __init__(self, records: dict, directory: Optional[str] = "blueprints",
            backup: Optional[bool] = True):
        self.records = records
        directory = str(directory)
        if Path(directory).is_absolute():
            self.directory = Path(directory)
        else:
            self.directory = Path().absolute() / directory
        self.backup = backup
        self.blueprints = {}
        self.paths = {}
        BlueprintHandler.current_parser = self

    def retrieve_blueprints(self) -> List[Blueprint]:
        """
        Return a list of blueprints the parser can read and build.

        Blueprints are to be read entirely at this point.  A list
        of blueprints is returned.

        """
        paths = list(self.directory.rglob("*.yml"))
        logger.debug(
            f"{len(paths)} file{'s' if len(paths) > 1 else ''} "
            f"could be found in {self.directory}."
        )
        for path in paths:
            relative = path.relative_to(self.directory)

            # Read the file
            with path.open("r", encoding="utf-8") as file:
                documents = yaml.safe_load_all(file.read())
                parent = relative.parent
                if str(parent) == ".":
                    unique_name = str(relative.stem)
                else:
                    unique_name = str(parent / relative.stem)

                blueprint = Blueprint(unique_name, list(documents))

            num_docs = len(blueprint.documents)
            logger.info(
                f"Loading {num_docs} "
                f"document{'s' if num_docs > 1 else ''} "
                f"from {relative}"
            )
            self.blueprints[unique_name] = blueprint
            self.paths[blueprint] = relative

    def apply(self):
        """
        Apply blueprints selectively.

        This method should check that applying the blueprint is
        expected and can interact with data.blueprint.Blueprint, which
        is a database table used to "remember" what blueprint
        was applied at what time.

        """
        for blueprint, relative in self.paths.items():
            blueprint.register()
            path = self.directory / relative
            record = self.records.get(blueprint.name)
            last_modified = datetime.fromtimestamp(
                    path.stat().st_mtime)
            if record is None:
                should_apply = True
                record = db.BlueprintRecord(name=blueprint.name,
                        modified=last_modified)
            else:
                should_apply = last_modified > record.modified
                record.modified = last_modified

            if should_apply:
                blueprint.apply()
                num_docs = blueprint.applied
                logger.info(
                    f"{relative}: applied {num_docs} "
                    f"document{'s' if num_docs > 1 else ''}"
                )
            else:
                logger.debug(f"{relative}: the file was ignored.")

    def store_blueprint(self, blueprint: Blueprint):
        """
        Store the specified blueprint, to disk or similar.

        The blueprint should be "written", in the parser's format,
        and stored in a system where it can be retrieved later,
        like a file.

        Args:
            blueprint (Blueprint): the blueprint to store.

        """
        path = self.directory / self.paths[blueprint]
        if self.backup:
            path.replace(str(path)[:-4] + ".old")

        documents = blueprint.dictionaries
        with path.open("w", encoding="utf-8") as file:
            yaml.dump_all(documents, file, sort_keys=False,
                    allow_unicode=True)

    def store_blueprints(self):
        """Store all blueprints."""
        pass

