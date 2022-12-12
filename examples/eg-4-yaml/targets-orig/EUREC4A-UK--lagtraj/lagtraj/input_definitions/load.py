import difflib
import shutil
from pathlib import Path

import yaml

from .. import DATA_TYPE_PLURAL
from . import InvalidInputDefinition, build_input_definition_path
from . import examples as input_examples
from . import validate_input
from .examples import LAGTRAJ_EXAMPLES_PATH_PREFIX
from .examples import get_available as get_available_input_examples

FOLDER_STRUCTURE_EXAMPLE = """
data
├── domains
│   ├── eurec4a_circle.yaml
│   └── eurec4a_circle_data
│       ├── an_model_2020-01-01.nc
│       :
│       └── fc_single_2020-01-03.nc
├── forcings
│   ├── eure4a_20200103_lag_testcase.yaml
│   └── eure4a_20200103_lag_testcase.nc
└── trajectories
    ├── eure4a_20200103_lag_testcase.yaml
    └── eure4a_20200103_lag_testcase.nc
"""


def load_definition(
    input_name,
    input_type,
    root_data_path,
    required_fields,
    input_subtype=None,
    expected_local_path=None,
):
    params = None
    input_path = None
    requesting_lagtraj_bundled_input = input_name.startswith(
        LAGTRAJ_EXAMPLES_PATH_PREFIX
    )

    if requesting_lagtraj_bundled_input:
        try:
            if input_subtype is None:
                input_path = input_examples.get_path(
                    input_name=input_name, input_type=input_type
                )
            else:
                if input_type == "forcing":
                    # NB: this is a bit hacky, we're assuming that the
                    # "subtype" will refer to a converted forcing, but that is
                    # probably ok for now, it's unlikely that we will have other
                    # kinds of subtypes of forcings
                    try:
                        input_path = input_examples.get_path(
                            input_name=f"lagtraj://{input_subtype}",
                            input_type="forcings_conversion",
                        )
                    except input_examples.LagtrajExampleDoesNotExist:
                        raise NotImplementedError(
                            f"The requested `{input_subtype}` forcing sub-type "
                            "isn't currently included with lagtraj"
                        )
                else:
                    raise input_examples.LagtrajExampleDoesNotExist()
        except input_examples.LagtrajExampleDoesNotExist:
            input_type_plural = DATA_TYPE_PLURAL[input_type]
            print(
                "The requested {} ({}) isn't currently available "
                "in lagtraj\n(maybe you could add it with a pull-request"
                " at https://github.com/EUREC4A-UK/lagtraj/pulls)\n\n"
                "The {} currently defined in lagtraj are:"
                "".format(input_type, input_name, input_type_plural)
            )
            print()
            input_examples.print_available(input_types=[input_type_plural])
            raise
    else:
        if input_name.endswith(".yaml") or input_name.endswith(".yml"):
            # assume we've been passed a full path
            input_path = Path(input_name)
            if not input_path.exists():
                raise Exception(
                    "You provided an absolute path to an input"
                    " yaml file, but that file doesn't appear"
                    " to exist. Maybe you intended to just"
                    " load this input definition by name instead?"
                )
            # check that this provided yaml-file is in the correct folder
            # structure
            input_type_plural = DATA_TYPE_PLURAL[input_type]
            if not (
                input_path.parent.parent.name == "data"
                and input_path.parent.name == input_type_plural
            ):
                lagtraj_input_examples = list(
                    get_available_input_examples(input_types=[input_type])
                )
                s = ", ".join(lagtraj_input_examples[:3])  # show the first three only
                raise Exception(
                    "The yaml input-file you provided does not"
                    " exist in the correct direction structure."
                    " lagtraj assumes that all data is stored in"
                    " a directory structure as follows (so that"
                    " so that the relevant input data and output"
                    f" can be found by lagtraj): \n{FOLDER_STRUCTURE_EXAMPLE}"
                    f"{input_type_plural} input definitions bundled with `lagtraj` can be used as well (for example {s}"
                    " - see all available with `python -m lagtraj.input_definitions.examples`)"
                    "e.g. \n"
                    "python -m lagtraj.trajectory.create lagtraj://eurec4a_20200202_12_lag \n"
                    "The input files are then copied over to the data directory."
                )
        else:
            input_path = build_input_definition_path(
                root_data_path=root_data_path,
                input_name=input_name,
                input_type=input_type,
                input_subtype=input_subtype,
            )
            if not input_path.exists():
                input_type_plural = DATA_TYPE_PLURAL[input_type]
                raise Exception(
                    f"The requested {input_type} ({input_name}) wasn't found. "
                    f"To use a {input_type} with this name please define its "
                    f"parameters {input_path}\n"
                    "(or run `python -m lagtraj.input_definitions.examples` all available with"
                    "to see the ones currently bundled with lagtraj"
                )
            print()

    with open(input_path) as fh:
        params = yaml.load(fh, Loader=yaml.FullLoader)

    try:
        validate_input(input_params=params, required_fields=required_fields)
    except InvalidInputDefinition as ex:
        raise Exception(
            "There was a problem parsing the input-definition "
            f"stored in `{input_path}`: {ex}"
        )
    params["name"] = input_name

    if "version" not in params:
        params["version"] = "unversioned"

    if requesting_lagtraj_bundled_input:
        # when the user requests a lagtraj-bundled input definition we copy it
        # to their local `data/` directory, but we need to check if there's
        # already a file there and whether that has any modifications

        # we need to strip the `lagtraj://` prefix before we construct the path
        # since the data is stored locally
        if input_name.startswith(LAGTRAJ_EXAMPLES_PATH_PREFIX):
            input_name = input_name[len(LAGTRAJ_EXAMPLES_PATH_PREFIX) :]

        if expected_local_path is not None:
            input_local_path = Path(expected_local_path)
        else:
            input_local_path = build_input_definition_path(
                root_data_path=root_data_path,
                input_name=input_name,
                input_type=input_type,
                input_subtype=input_subtype,
            )

        if not input_local_path.exists():
            # if it doesn't exist we can just copy across no problem
            input_local_path.parent.mkdir(exist_ok=True, parents=True)
            shutil.copy(input_path, input_local_path)
        else:
            # otherwise we need to check the contents

            input_raw = open(input_path).read().splitlines()
            input_local_raw = open(input_local_path).read().splitlines()

            param_diff = list(
                difflib.unified_diff(
                    a=input_raw,
                    b=input_local_raw,
                    fromfile="lagtraj://",
                    tofile="local",
                    lineterm="",
                )
            )
            if len(param_diff) != 0:
                print("\n".join(param_diff))
                print()
                if Path(".").absolute() in input_local_path.parents:
                    p = input_local_path.relative_to(Path(".").absolute())
                else:
                    p = input_local_path
                raise Exception(
                    f"Your local of the `{input_name}` {input_type} "
                    f"input-definition in `{p}` "
                    "is different to what is included with "
                    "lagtraj (see the differences above). Either you can "
                    "use your local copy directly (by removing the `lagtraj://` "
                    "part in the command you just issued) or delete your "
                    "local copy and we'll copy over what's included with "
                    "lagtraj."
                )

    return params
