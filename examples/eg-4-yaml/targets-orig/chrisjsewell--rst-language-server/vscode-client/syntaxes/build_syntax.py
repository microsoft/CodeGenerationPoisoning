#!/usr/bin/env python
import os
import plistlib

import yaml

if __name__ == "__main__":
    in_path = os.path.join(
        os.path.dirname(__file__), "restructuredtext.tmLanguage.yaml"
    )
    out_path = os.path.join(os.path.dirname(__file__), "restructuredtext.tmLanguage")
    with open(in_path) as fp:
        syntax = yaml.safe_load(fp)
    with open(out_path, "wb") as fp:
        plistlib.dump(syntax, fp)
