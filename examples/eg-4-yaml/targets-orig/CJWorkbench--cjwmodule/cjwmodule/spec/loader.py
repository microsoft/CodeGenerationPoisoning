from __future__ import annotations

import importlib.resources
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

import jsonschema
import yaml

from .paramfield import ParamField
from .paramschema import ParamSchema
from .paramschemaparser import parse as parse_param_schema
from .types import ModuleSpec

__all__ = [
    "load_spec",
    "load_spec_file",
]


MODULE_ALLOWED_SECRETS = {
    "googlesheets": ["google"],  # OAuth2: generate temporary access token
    "intercom": ["intercom"],  # OAuth2: pass user's long-lasting access token
    "twitter": ["twitter"],  # OAuth1: give module consumer_key+consumer_secret
}
"""Mapping from module slug to OAUTH_SERVICES key mangling `fetch(secrets=...)`."""


_spec_yaml = importlib.resources.read_text(__package__, "schema.yaml")
_spec_validator = jsonschema.Draft7Validator(
    yaml.safe_load(_spec_yaml), format_checker=jsonschema.FormatChecker()
)


def _validate_secret_param(module_id_name, param) -> None:
    """Raise ValueError rather than leak global secrets to an untrusted module.

    SECURITY: this is ... a hack. First, let's describe The Vision; then Reality.

    The Vision: each module ought to have its own security tokens. There should
    not be an OAUTH_SERVICES global variable. A sysadmin should register an app
    with Twitter/Google/whatever at module-installation time. When we have that,
    we can delete MODULE_ALLOWED_SECRETS.

    Reality: [2019-10-16] today isn't the revamp day. Consumer secrets are
    global; and in the case of OAuth1.0a (Twitter), the module can read those
    secrets. If a new module, "eviltwitter," comes along with a
    "twitter_credentials" parameter, the module author will gain Workbench's
    Twitter credentials -- and the user's credentials, too.

    From the user's perspective:

        1. Add "twitter" step
        2. Sign in; grant (global-variable) Workbench access to Twitter stuff
        3. Add "eviltwitter" module
        4. Sign in again?

    Results (The Vision): step 4 prompts the user to trust "eviltwitter".
    Results (SECURITY disaster): step 4 re-uses the grant from step 2.
    Results (alternate SECURITY disaster): step 4 prompts the user, NOT
                                           mentioning "eviltwitter != twitter".
    Results (Reality, 2019-10-16): "eviltwitter" does not validate because it
                                   isn't in MODULE_ALLOWED_SECRETS. Not fun,
                                   but not a security disaster.
    """
    allowed_secrets = MODULE_ALLOWED_SECRETS.get(module_id_name, [])
    if param["secret_logic"]["provider"] == "string":
        return
    if param["secret_logic"]["service"] in allowed_secrets:
        return
    else:
        raise ValueError(
            "Denied access to global %r secrets" % param["secret_logic"]["service"]
        )


def _validate_spec_dict(spec: Dict[str, Any]) -> None:
    """Raise ValueError if the spec is invalid.

    "Valid" means:

    * `spec` adheres to jsonschema `schema.yaml`
    * `spec.parameters[*].id_name` are unique
    * Only whitelisted secrets are allowed (ref: cjworkbench/settings.py)
    * `spec.parameters[*].visible_if[*].id_name` are valid
    * If `spec.parameters[*].options` and `default` exist, `default` is valid
    * `spec.parameters[*].visible_if[*].value` is/are valid if it's a menu
    * `spec.parameters[*].tab_parameter` point to valid params
    * `spec.parameters[*].secret` is correct
    """
    # No need to do i18n on these errors: they're only for admins. Good thing,
    # too -- most of the error messages come from jsonschema, and there are
    # _plenty_ of potential messages there.
    messages = []

    for err in _spec_validator.iter_errors(spec):
        messages.append(err.message)
    if messages:
        # Don't bother validating the rest. The rest of this method assumes
        # the schema is valid.
        raise ValueError("; ".join(messages))

    param_lookup = {}
    for param in spec["parameters"]:
        id_name = param["id_name"]

        if id_name in param_lookup:
            messages.append(f"Param '{id_name}' appears twice")
        else:
            param_lookup[id_name] = param

    # check 'default' is valid in menu/radio
    for param in spec["parameters"]:
        if "default" in param and "options" in param:
            options = [
                o["value"] for o in param["options"] if isinstance(o, dict)
            ]  # skip 'separator'
            if param["default"] not in options:
                messages.append(
                    f"Param '{param['id_name']}' has a 'default' that is not "
                    "in its 'options'"
                )

    # Check that secrets are in global whitelist.
    #
    # This is to prevent malicious modules from stealing our global secrets.
    # A better approach would be to nix global secrets altogether and configure
    # OAuth per-module. So far we've been too lazy to do this.
    for param in spec["parameters"]:
        if param["type"] == "secret":
            _validate_secret_param(spec["id_name"], param)

    # Now that check visible_if refs
    for param in spec["parameters"]:
        try:
            visible_if = param["visible_if"]
        except KeyError:
            continue

        try:
            ref_param = param_lookup[visible_if["id_name"]]
        except KeyError:
            messages.append(
                f"Param '{param['id_name']}' has visible_if "
                f"id_name '{visible_if['id_name']}', which does not exist"
            )
            continue

        if "options" in ref_param and not isinstance(visible_if["value"], list):
            messages.append(
                f"Param '{param['id_name']}' needs its visible_if.value "
                f"to be an Array of Strings, since '{visible_if['id_name']}' "
                "has options."
            )

        if "options" in ref_param:
            if_values = visible_if["value"]
            if isinstance(if_values, list):
                if_values = set(if_values)
            else:
                if_values = set(if_values.split("|"))

            options = set(
                o["value"] for o in ref_param["options"] if isinstance(o, dict)
            )  # skip 'separator'

            missing = if_values - options
            if missing:
                messages.append(
                    f"Param '{param['id_name']}' has visible_if values "
                    f"{repr(missing)} not in '{ref_param['id_name']}' options"
                )

    # Check tab_parameter refs
    for param in spec["parameters"]:
        try:
            tab_parameter = param["tab_parameter"]
        except KeyError:
            continue  # we aren't referencing a "tab" parameter

        if tab_parameter not in param_lookup:
            messages.append(
                f"Param '{param['id_name']}' has a 'tab_parameter' "
                "that is not in 'parameters'"
            )
        elif param_lookup[tab_parameter]["type"] != "tab":
            messages.append(
                f"Param '{param['id_name']}' has a 'tab_parameter' "
                "that is not a 'tab'"
            )

    # Check secret refs
    for param in spec["parameters"]:
        try:
            secret_parameter = param["secret_parameter"]
        except KeyError:
            continue  # we aren't referencing a "secret" parameter

        if secret_parameter not in param_lookup:
            messages.append(
                f"Param '{param['id_name']}' has a 'secret_parameter' "
                "that is not a 'secret'"
            )
        else:
            secret = param_lookup[secret_parameter]
            if secret["type"] != "secret":
                messages.append(
                    f"Param '{param['id_name']}' has a 'secret_parameter' "
                    "that is not a 'secret'"
                )
            elif param["type"] == "gdrivefile" and (
                secret["secret_logic"]["provider"] != "oauth2"
                or secret["secret_logic"]["service"] != "google"
            ):
                messages.append(
                    f"Param '{param['id_name']}' 'secret_parameter' "
                    "does not refer to a 'google', 'oauth2' secret"
                )

    if messages:
        raise ValueError("; ".join(messages))


def load_spec(jsonish: Dict[str, Any]) -> ModuleSpec:
    """Convert a JSON-ish data structure to a ModuleSpec.

    Raise ValueError if the JSON-ish data structure has an error.
    """
    _validate_spec_dict(jsonish)

    loads_data = jsonish.get("loads_data", False)
    uses_data = jsonish.get("uses_data", not loads_data)
    param_fields = [ParamField.from_dict(d) for d in jsonish["parameters"]]
    if "param_schema" in jsonish:
        # Deprecated behavior: Module author wrote a schema in the YAML,
        # to define storage of 'custom' parameters
        param_schema = parse_param_schema(
            dict(type="dict", properties=jsonish["param_schema"])
        )
    else:
        # Usual case: infer schema from module parameter types
        param_schema = ParamSchema.Dict(
            {
                f.id_name: f.to_schema()
                for f in param_fields
                if f.to_schema() is not None
            }
        )

    return ModuleSpec(
        id_name=jsonish["id_name"],
        name=jsonish["name"],
        category=jsonish["category"],
        deprecated=jsonish.get("deprecated"),
        icon=jsonish.get("icon", ""),
        link=jsonish.get("link", ""),
        description=jsonish.get("description", ""),
        loads_data=loads_data,
        uses_data=uses_data,
        html_output=jsonish.get("html_output", False),
        has_zen_mode=jsonish.get("has_zen_mode", False),
        row_action_menu_entry_title=jsonish.get("row_action_menu_entry_title", ""),
        help_url=jsonish.get("help_url", ""),
        param_fields=param_fields,
        param_schema=param_schema,
    )


def load_spec_file(path: Path) -> ModuleSpec:
    """Load a ModuleSpec from a .yaml or .json file.

    Raise ValueError on validation error.

    Raise OSError on read error.
    """
    # raise OSError, ValueError
    with path.open("rb") as f:
        jsonish = yaml.safe_load(f)

    # raise ValueError
    return load_spec(jsonish)


if __name__ == "__main__":
    import sys

    filename = sys.argv[1]

    path = Path(filename)
    spec = load_spec_file(path)

    def repr_ParamField(dumper, data):
        return dumper.represent_mapping(type(data).__name__, asdict(data))

    def repr_NamedTuple(dumper, data):
        return dumper.represent_mapping(type(data).__name__, data._asdict())

    yaml.add_multi_representer(ParamField, repr_ParamField)
    yaml.add_multi_representer(tuple, repr_NamedTuple)
    print(yaml.dump(spec))
