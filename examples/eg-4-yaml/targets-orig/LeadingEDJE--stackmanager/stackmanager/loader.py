from .exceptions import ValidationError
from .config import Config, TEMPLATE, PREVIOUS_PARAMETERS, PARAMETERS, USE_PREVIOUS_VALUE, CHANGE_SET_NAME, \
    CHANGE_SET_ID, EXISTING_CHANGES, AUTO_APPLY
import yaml


def load_config(config_file, arg_config, environment, check_template=True, **kwargs):
    """
    Build hierarchy of configurations by loading multi-document config file.
    There must be a matching config for the environment name and region.
    :param str config_file: Path to config file
    :param Config arg_config: Argument config
    :param str environment: Environment being updated
    :param bool check_template: Check Template exists when validating config
    :param kwargs: Other arguments to be added to arg config
    :return: Top of Config hierarchy
    :raises validationException: If config file not found, matching environment not found in config or config is invalid
    """
    populate_arg_config(arg_config, environment, kwargs)

    try:
        with open(config_file) as c:
            raw_configs = yaml.safe_load_all(c)
            all_config = None
            env_config = None
            for rc in raw_configs:
                config = Config(rc)
                if Config.is_all(config.environment):
                    all_config = config
                elif config.environment == environment and config.region == arg_config.region:
                    env_config = config

            if not env_config:
                raise ValidationError(f'Environment {environment} for {arg_config.region} not found in {config_file}')

            env_config.parent = all_config
            arg_config.parent = env_config

            # Validate before returning
            arg_config.validate(check_template)
            return arg_config
    except FileNotFoundError:
        raise ValidationError(f'Config file {config_file} not found')


def populate_arg_config(arg_config, environment, kwargs):
    """
    Populate Configuration from the command line arguments, used as top of hierarchy to
    optionally override template and parameters.
    :param Config arg_config: Argument Config
    :param str environment: Environment
    :param dict kwargs: Other arguments to be added to arg config
    """
    arg_config.environment = environment

    if TEMPLATE in kwargs:
        arg_config.template = kwargs[TEMPLATE]
    if PREVIOUS_PARAMETERS in kwargs:
        previous = {p: USE_PREVIOUS_VALUE for p in kwargs[PREVIOUS_PARAMETERS]}
        arg_config.add_parameters(previous)
    if PARAMETERS in kwargs:
        arg_config.add_parameters(kwargs[PARAMETERS])
    if CHANGE_SET_NAME in kwargs:
        arg_config.change_set_name = kwargs[CHANGE_SET_NAME]
    if CHANGE_SET_ID in kwargs:
        arg_config.change_set_id = kwargs[CHANGE_SET_ID]
    if EXISTING_CHANGES in kwargs:
        arg_config.existing_changes = kwargs[EXISTING_CHANGES]
    if AUTO_APPLY in kwargs:
        arg_config.auto_apply = kwargs[AUTO_APPLY]
