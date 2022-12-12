import datetime
import logging
import os
import yaml
from string import Template

logger = logging.getLogger('fddc.annex_a.config')


class Config(dict):

    def __init__(self, *config_files, local_required=False, local_warn=False):

        self.load_config("./localconfig.yml", conditional=~local_required, warn=local_warn)

        for file in config_files:
            self.load_config(file, conditional=False)

        self['config_date'] = datetime.datetime.now().isoformat()
        try:
            self['username'] = os.getlogin()
        except OSError:
            # This happens when tests are not run under a login shell, e.g. CI pipeline
            pass

    def load_config(self, filename, conditional=False, warn=False):
        """
        Load configuration from yaml file. Any loaded configuration
        is only set if the values don't already exist in CONFIG.

        Files can contain ${} placeholders following the Python string.Template format.
        The context will include any keys already existing in the configuration, any keys
        from the current file - however, if these include placeholders, the placeholders
        will not be replaced. Finally, environment variables can be referenced with
        `os_environ_VARIABLE_NAME`.

        Keyword arguments:
        filename -- Filename to load from
        conditional -- If True, ignore file if it doesn't exist. If False, fail. (default False)
        """
        if conditional and not os.path.isfile(filename):
            if warn:
                logger.warning('Missing optional file {}'.format(filename))

            return

        with open(filename) as FILE:
            user_config = yaml.load(FILE, Loader=yaml.FullLoader)

        logger.info("Loading {} configuration values from '{}'.".format(len(user_config), filename))

        environment_dict = {'os_environ_{}'.format(k): v for k, v in os.environ.items()}

        variables = dict(self)
        variables.update(user_config)
        variables.update(environment_dict)

        with open(filename, 'rt') as FILE:
            user_config_string = FILE.read()

        user_config_template = Template(user_config_string)
        user_config_string = user_config_template.substitute(variables)

        user_config = yaml.load(user_config_string, Loader=yaml.FullLoader)

        self.update(user_config)


class ConfigError(UserWarning):
    """
    An error with a configuration, such as a missing or invalid value.
    """
