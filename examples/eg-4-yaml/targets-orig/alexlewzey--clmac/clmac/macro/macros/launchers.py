"""
automates opening frequently used websites across multiple chrome browsers
"""
import time
import webbrowser
from pathlib import Path
from typing import Iterable

import pyperclip
import yaml

from clmac.config.definitions import URLS_YAML, LAUNCH_TXT

path = Path.cwd()

rest = 0.3


def open_urls(urls: Iterable[str]) -> None:
    """launches a list of urls with webdriver"""
    for url in urls:
        webbrowser.open(url)
        time.sleep(rest)
    time.sleep(rest)


def morning_sites() -> None:
    with LAUNCH_TXT.open() as f:
        urls = f.read().splitlines()
        open_urls(urls)


def guitar_practice():
    """open the guitar practice urls in browser"""
    with URLS_YAML.open('r') as f:
        urls = yaml.load(f)['guitar']
    open_urls(urls.values())


def clipboard2browser():
    """open the current clipboard item as a url in a browser"""
    cb = pyperclip.paste()
    url = cb if cb.startswith('http') else 'http://' + cb
    webbrowser.open(url)
