"""
Project: py-ispyb.

https://github.com/ispyb/py-ispyb

This file is part of py-ispyb software.

py-ispyb is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

py-ispyb is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along
"""


__license__ = "LGPLv3+"


import os


from functools import lru_cache
from pydantic import BaseSettings, BaseModel
import yaml


PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
RESOURCES_ROOT = os.path.join(PROJECT_ROOT, "resources")


def get_env_file():
    res = os.getenv("ISPYB_ENVIRONMENT", None)
    if res is None or res == "":
        return "config/.env"
    v = f"config/{res}.env"
    if os.path.exists(v):
        return v

    raise Exception(f"Config file {v} could not be found.")


class Settings(BaseSettings):
    static_root: str = os.path.join(PROJECT_ROOT, "static")
    queries_dir: str = os.path.join(RESOURCES_ROOT, "queries")

    api_root: str
    service_name: str

    sqlalchemy_database_uri: str
    query_debug: bool

    auth = {}
    auth_config: str

    jwt_coding_algorithm: str
    token_exp_time: int  # in minutes
    secret_key: str

    cors: bool = False

    simulation_config: str = None

    class Config:
        env_file = get_env_file()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

AUTH_CONFIG = os.path.realpath(os.path.join(PROJECT_ROOT, "..", settings.auth_config))
try:
    with open(AUTH_CONFIG) as f:
        yaml_settings = dict()
        yaml_settings.update(yaml.safe_load(f))
        settings.auth = yaml_settings["AUTH"]
except IOError:
    raise Exception(f"Could not access auth config: {AUTH_CONFIG}")


class LogConfig(BaseModel):
    """Logging configuration to be set for the server"""

    LOGGER_NAME: str = "pyispyb"
    LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | %(name)s | %(message)s"
    LOG_LEVEL: str = "INFO"

    version = 1
    disable_existing_loggers = False
    formatters = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
    loggers = {
        "root": {"handlers": ["default"], "level": LOG_LEVEL},
        "ispyb": {"handlers": ["default"], "level": LOG_LEVEL},
        "db": {"handlers": ["default"], "level": "DEBUG"},
    }
