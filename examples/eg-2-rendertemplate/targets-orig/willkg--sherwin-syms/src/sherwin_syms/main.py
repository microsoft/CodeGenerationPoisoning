# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from flask import current_app, Flask, render_template, request

from sherwin_syms.cache import MemoryCacheManager
from sherwin_syms.downloader import Downloader
from sherwin_syms.symbols import Symbolicator


def create_app():
    app = Flask(__name__)

    mcm = MemoryCacheManager(maxsizekb=1024 * 1000)
    downloader = Downloader(source_urls=["https://symbols.mozilla.org/"])
    app.symbolicator = Symbolicator(downloader=downloader, cachemanager=mcm)

    @app.route("/")
    def hello():
        return render_template("index.html")

    @app.route("/symbolicate/v5", methods=["POST"])
    def symbolicate_v5():
        symbolicator = current_app.symbolicator

        payload = json.loads(request.get_data())

        if "jobs" in payload:
            jobs = payload["jobs"]
        else:
            jobs = [payload]

        results = []
        for job in jobs:
            stacks = job.get("stacks", [])
            modules = job.get("memoryMap", [])

            results.append(symbolicator.symbolicate(stacks, modules))
        return {"results": results}

    return app
