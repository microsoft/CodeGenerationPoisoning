"""
Beancount to Ledger converter
"""

# SPDX-FileCopyrightText: © 2020 Software in the Public Interest, Inc.
# SPDX-FileCopyrightText: © 2020 Martin Michlmayr <tbm@cyrius.com>

# SPDX-License-Identifier: GPL-2.0-or-later

__license__ = "GPL-2.0-or-later"

import argparse
import contextlib
import locale
from pathlib import Path
import os
import sys
from tempfile import NamedTemporaryFile
import yaml

import beancount2ledger


def get_config(user_config):
    """
    Get config from config file
    """

    if user_config:
        return yaml.safe_load(user_config)
    all_config = []
    all_config.append(Path(".beancount2ledger.yaml"))
    xdg = Path.expanduser(Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")))
    all_config.append(xdg / "beancount2ledger" / "config.yaml")
    for config in all_config:
        if config.exists():
            with open(config, "r") as config_stream:
                return yaml.safe_load(config_stream)
    return {}


def cli():
    """
    Main function for CLI access.
    """

    if "hledger" in sys.argv[0]:
        default = "hledger"
    else:
        default = "ledger"

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-f",
        "--format",
        dest="format",
        action="store",
        choices=("ledger", "hledger"),
        default=default,
        help=f"output format (default: {default})",
    )
    parser.add_argument("file", help="beancount file", type=str)
    parser.add_argument(
        "-c", "--config", help="config file", type=argparse.FileType("r")
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {beancount2ledger.__version__}",
    )

    with contextlib.ExitStack() as stack:
        args = parser.parse_args()
        in_file = args.file

        # beancount loader does not accept file objects, hence to support reading from
        # stdin we write its content to a tempfile and call the loader on its path
        if in_file == "-":
            tmpfile = stack.enter_context(
                NamedTemporaryFile(
                    prefix="tmp.beancount2ledger.",
                    mode="w",
                    encoding=locale.getpreferredencoding(),
                )
            )
            tmpfile.write(sys.stdin.read())
            tmpfile.flush()
            in_file = tmpfile.name

        config = get_config(args.config)
        output = beancount2ledger.convert_file(in_file, args.format, config=config)
        print(output)


if __name__ == "__main__":
    cli()
