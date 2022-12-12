import os
import logging

import yaml


class Context:
    _keywords = {
        "host": "127.0.0.1",
        "port": 9090,
        "reload": False,
        "insecure_cors": False,
        "config_path": "otvl_web_config.yml",
        "content_path": "",
        "assets_path": "",
        "j24bots_path": ""
        }
    logger = logging.getLogger(__name__)

    def _get_val(self, kw, kwargs):
        v = self._keywords.get(kw)
        venv = f"OTVL_WEB_{kw.upper()}"
        if kw in kwargs:
            v = type(v)(kwargs[kw])
        elif os.getenv(venv) is not None:
            v = type(v)(os.getenv(venv))
        return v

    def __init__(self, **kwargs):
        for kw in self._keywords:
            v = self._get_val(kw, kwargs)
            if v is not None:
                setattr(self, kw, v)
        cfs = os.path.dirname(self.config_path)
        if cfs:
            cfs += "/"
        if self.content_path == "":
            self.content_path = cfs + "content"
        try:
            with open(self.config_path) as ysd:
                self.config = yaml.load(ysd, Loader=yaml.FullLoader)
            if self.assets_path == "":
                self.assets_path = self.config["server"].get("assets_path", cfs + "assets")
            if self.j24bots_path == "":
                self.j24bots_path = self.config["server"].get("j24bots_path", cfs + "j24bots")
        except Exception:
            self.config = None

        self.logger.debug(
            f"__init__ config {self.config_path} content_path {self.content_path} assets_path {self.assets_path}")
