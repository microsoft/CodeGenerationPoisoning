import sys
import versioneer
from pathlib import Path

from platform import processor


try:
    from setuptools import setup

except ImportError:
    print("Needs 'setuptools' to install")
    sys.exit(1)

try:
    import yaml

except ImportError:
    print("Needs 'yaml' to install")
    sys.exit(1)


# +-----------------------------------------------------------------------------
# | CONSTRUCT PARAMETERS FOR setuptools
# +-----------------------------------------------------------------------------

def trunc_lines(s):
    parts = s.split('\n')
    while len(parts[0]) == 0:
        parts = parts[1:]

    while len(parts[-1]) == 0:
        parts = parts[:-1]

    parts = [part for part in parts if len(part) > 0]

    return ''.join(parts)


def build_keyword_dictionary(prefs):
    keywords = {}

    for key in [
  'name', 'license', 'url', 'download_url', 'packages', 'package_dir',
  'platforms', 'description', 'install_requires', 'long_description',
  'scripts', 'package_data', 'include_package_data', ]:

        if key in prefs:
            keywords[key] = prefs[key]

    keywords['author_email'] = ', '.join(prefs['emails'])

    keywords['author'] = ', '.join(
        prefs['authors'][:-1]) + ' and ' \
        + prefs['authors'][-1]

    keywords["package_dir"] = \
        {package: '/'.join(package.split('.'))
         for package in prefs['packages']}

    keywords['long_description'] = \
        trunc_lines(keywords['long_description'])

    output = ""
    first_tab = 40
    second_tab = 60
    for key in sorted(keywords.keys()):
        value = keywords[key]
        output += key.rjust(first_tab) + \
            str(value).rjust(second_tab) + ""

    return keywords


# load settings from setup.yaml
with open('setup.yaml') as f:
    yaml_string = ''.join(f.readlines())
    preferences = yaml.safe_load(yaml_string)


setup_args = build_keyword_dictionary(preferences)
setup_args['version'] = versioneer.get_version()
setup_args['cmdclass'] = versioneer.get_cmdclass()

myarch = processor()
if "ppc64" in myarch:
    # Dirty solution here...
    import subprocess, shlex, os
    olddir = Path(".").resolve()
    os.chdir("..")
    subprocess.call(shlex.split("conda install cython scipy"))
    subprocess.call(shlex.split("git clone https://github.com/jrossyra/mdtraj-nogeo"))
    os.chdir("mdtraj-nogeo")
    subprocess.call(shlex.split("pip install -e ."))
    os.chdir(str(olddir))

setup(**setup_args)

