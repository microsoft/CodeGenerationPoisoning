from collections import OrderedDict as OD
from pathlib import Path

import yaml
from asciitree import LeftAligned, drawing

from .. import DATA_TYPE_PLURAL

EXAMPLES_ROOT_PATH = Path(__file__).parent / "examples_files"
LAGTRAJ_EXAMPLES_PATH_PREFIX = "lagtraj://"


class LagtrajExampleDoesNotExist(Exception):
    pass


def get_path(input_name, input_type):
    if not input_name.startswith(LAGTRAJ_EXAMPLES_PATH_PREFIX):
        raise Exception(
            "All lagtraj example inputs should start with "
            f"`{LAGTRAJ_EXAMPLES_PATH_PREFIX}`"
        )

    input_name = input_name.replace(LAGTRAJ_EXAMPLES_PATH_PREFIX, "")
    input_type = DATA_TYPE_PLURAL.get(input_type, input_type)

    file_path = EXAMPLES_ROOT_PATH / input_type / (input_name + ".yaml")
    if not file_path.exists():
        raise LagtrajExampleDoesNotExist

    return file_path


def attempt_read(input_name, input_type):
    file_path = get_path(input_name=input_name, input_type=input_type)
    with open(file_path) as fh:
        params = yaml.load(fh, Loader=yaml.FullLoader)
    return params


def get_available(input_types="all"):
    def _visit_path(p_current):
        subpaths = p_current.glob("*")
        if p_current == EXAMPLES_ROOT_PATH and input_types != "all":
            subpaths = filter(lambda p_: p_.name in input_types, subpaths)

        valid_paths = []
        for p_sub in subpaths:
            if p_sub.is_file():
                if p_sub.name.endswith(".yaml"):
                    valid_paths.append((p_sub.name.replace(".yaml", ""), OD()))
            else:
                valid_paths.append((p_sub.name, OD(_visit_path(p_sub))))

        return OD(valid_paths)

    return _visit_path(EXAMPLES_ROOT_PATH)


def print_available(input_types="all"):
    examples_tree = {"lagtraj://": get_available(input_types=input_types)}

    box_tr = LeftAligned(draw=drawing.BoxStyle(gfx=drawing.BOX_LIGHT))
    print(box_tr(examples_tree))


def cli(args=None):
    print(
        "The following domain/forcing/trajectory definitions are"
        " currently included with lagtraj:"
    )
    print("")

    print_available()

    print("\n")
    print(
        "To use for example the `eurec4a_north_atlantic` domain definition\n"
        "for downloading domain data run lagtraj.domain.download as"
        " follows:\n"
        "\n"
        "    $> python -m lagtraj.domain.download"
        " lagtraj://eurec4a_20200202_first"
    )


if __name__ == "__main__":
    cli()
