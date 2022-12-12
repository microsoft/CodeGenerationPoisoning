from abc import ABC, abstractmethod
from contextlib import contextmanager
import logging
import os
import pkg_resources
from typing import Any

import yaml

from ..config import settings
from ..app.extensions.database.session import _session

logger = logging.getLogger(__name__)


def load_config() -> dict[str, Any]:
    if not settings.simulation_config:
        raise RuntimeError("`SIMULATION_CONFIG` environment variable is not defined")

    if not os.path.exists(settings.simulation_config):
        raise AttributeError(f"Cannot find config file: `{settings.simulation_config}`")

    config = {}
    with open(settings.simulation_config, "r") as stream:
        config = yaml.safe_load(stream)

    return config


class Simulation(ABC):
    def __init__(self):
        self._config = load_config()

    @property
    def config(self) -> dict[str, Any]:
        return self._config

    @contextmanager
    def session(self):
        db_session = _session()
        try:
            yield db_session
            db_session.commit()
        except Exception as e:  # noqa
            db_session.rollback()
            raise
        finally:
            db_session.close()

    @property
    def beamlines(self) -> list[str]:
        return self.config["sessions"].keys()

    @property
    def experiment_types(self) -> list[str]:
        return self.config["experiments"].keys()

    def before_start(self, dataCollectionId: int) -> None:
        for entry in pkg_resources.iter_entry_points(
            "ispyb.simulator.before_datacollection"
        ):
            fn = entry.load()
            logger.info(f"Executing before start plugin `{entry.name}`")
            fn(dataCollectionId)

    def after_end(self, dataCollectionId: int) -> None:
        for entry in pkg_resources.iter_entry_points(
            "ispyb.simulator.after_datacollection"
        ):
            fn = entry.load()
            logger.info(f"Executing after end plugin `{entry.name}`")
            fn(dataCollectionId)

    def do_run(self, *args, **kwargs) -> None:
        self.run(*args, **kwargs)

    @abstractmethod
    def run(self, *args, **kwargs) -> None:
        pass
