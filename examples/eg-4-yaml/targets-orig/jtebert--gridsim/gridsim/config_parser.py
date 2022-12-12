"""
The ``ConfigParser`` is an optional class to help separate your code for experimental configurations
by using `YAML <https://yaml.org/>`_ files for configuration. This imposes very few restrictions on
the way you set up your configuration files; it mostly makes it easier to access their contents and
save the configuration parameters with your data using the :class:`~gridsim.logger.Logger`.

This is useful for managing both values that are fixed through all experiments (e.g., dimensions of
the arena) and experimental values that vary between conditions (e.g., number of robots). The latter
may be saved as an array and a single value used for different conditions.

While the ``ConfigParser`` can load any valid YAML files, the largest restriction is what
configuration parameter types can be saved to log files. For details, see the
:meth:`~gridsim.logger.Logger.log_config` documentation.

"""

from typing import Any, Optional
import warnings

import yaml


class ConfigParser:
    """
    Class to handle YAML configuration files.

    This can be directly passed to the :meth:`~gridsim.logger.Logger.log_config` to save all
    configuration values with the trial data.

    Parameters
    ----------
    config_filename : str
        Location and filename of the YAML config file
    show_warnings : bool
        Whether to print a warning if trying to ``get`` a value that returns None (useful for
        debugging), by default ``False``.
    """

    def __init__(self, config_filename: str, show_warnings: bool = False):
        self._show_warnings = show_warnings
        with open(config_filename) as f:
            self._params = yaml.load(f, Loader=yaml.FullLoader)

    def get(self, key: Optional[str] = None, default: Any = None) -> Any:
        """
        Get a parameter value from the configuration, or get a dictionary of the parameters if no
        parameter name (key) is specified.

        Note
        ----
        If no default is specified and the key is *not* found in the configuration file,
        this will return ``None`` instead of rasing an exception.

        Parameters
        ----------
        key : str, optional
            Name of the parameter to retrieve, by default None. If not specified, a dictionary of
            all parameters will be returned.
        default : Any, optional
            Default value to return if the key is not found in the configuration, by default
            ``None``.

        Returns
        -------
        Any
            Parameter value for the given key, or the default value is the key is not found. If no
            key is given, a dictionary of all parameters is returned.
        """
        if key is None:
            return self._params
        else:
            val = self._params.get(key, default)
            if val is None and self._show_warnings:
                warnings.warn(f'Configuration value for key "{key}" is None')
            return val
