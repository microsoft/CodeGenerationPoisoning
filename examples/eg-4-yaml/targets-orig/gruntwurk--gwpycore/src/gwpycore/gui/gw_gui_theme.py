import logging
from typing import List, Optional, Tuple, Dict, Union
import yaml
from pathlib import Path
from enum import Enum
from abc import ABC, abstractmethod

from ..core.gw_exceptions import GWConfigError
from ..core.gw_config import GWConfigParser


# TODO Move all PyQT support to a seperate module (gwpyqt)

LOG = logging.getLogger("main")

Color = Optional[Tuple[int, int, int]]


class ThemeMetaData:
    def __init__(self, name="", author="", filename="") -> None:
        self.name = name
        self.author = author
        self.filename = filename
        self.description = ""
        self.credit = ""
        self.url = ""
        self.license = ""
        self.license_url = ""


class ThemeStructure(Enum):
    NO_THEME = 'no_theme'
    ICON_SET = 'icon_set'
    SKIN = "skin"
    SYNTAX = "syntax"
    KEYMAP = "key_map"

    @classmethod
    def possibleValues(cls) -> str:
        return ', '.join([e.name for e in cls])

    def uses_base16(self):
        return self in [ThemeStructure.SKIN, ThemeStructure.SYNTAX]

    def uses_conf(self):
        return self in [ThemeStructure.SKIN, ThemeStructure.SYNTAX]

    def uses_csv(self):
        return self in [ThemeStructure.KEYMAP]

    def by_folder_alone(self):
        return self in [ThemeStructure.ICON_SET]


class GWAssets(ABC):
    """
    Base class for the various asset-management classes (SkinAssets, IconAssets, KeyMapAssets, ImageAssets,
    FontAssets, SyntaxHighlightAssets).
    Some of these have user-selectable themes: SkinAssets, IconAssets, KeyMapAssets, and SyntaxHighlightAssets.
    In many cases, a theme consist of a single file (e.g. a Base16 color scheme called "deep_purple.yaml" is all it takes to create a "Deep Purple" skin.)
    In other cases, a theme consists of a sub-folder full of assets (e.g. a set of icons).
    Some assets contain metadata (*.yaml, *.conf), in which case the theme name is pulled from there;
    otherwise, the theme name defaults to the name of the folder or file.

    ?? style.qss
    """
    def __init__(self, asset_path: Union[Path, str]):
        if isinstance(asset_path, Path):
            self.asset_path = asset_path
        else:
            self.asset_path = Path(asset_path)
        if not self.asset_path.is_dir():
            raise GWConfigError(f"{asset_path} is not a directory or does not exist.")

        self.theme_structure = ThemeStructure.NO_THEME
        self.conf_name = ""
        self.theme_name = ""
        self.fallback_theme = ""
        self.excluded_themes = []
        self.available_themes: Dict[str, ThemeMetaData] = []
        self.on_change =None

    def _set_theme(self, theme_name) -> bool:
        """
        Called by apply_theme() to declare which theme is being set up.

        Returns True if the caller should continue, or False if the named
        theme has already been set, so there's nothing to do.
        """
        if (not theme_name) or self.theme_name == theme_name:
            return False

        if not self.theme_structure:
            raise GWConfigError("Attempted to set a theme name for an asset class that doesn't use themes.")
        self.theme_name = theme_name
        LOG.debug(f"self.theme_name set to: {self.theme_name}")
        return True

    def connect_on_change(self, callback):
        self.on_change = callback

    @abstractmethod
    def apply_theme(self, theme_name):
        """
        (First, call themes() to see what's available.)
        """
        pass

    def set_fallback(self, fallback_theme: str, excluded_themes: List[str] = []):
        """
        If the asset has a fallback theme, name it here.
        If there are multiple fallback asset folders, then list them in the exclusions.
        """
        self.fallback_theme = fallback_theme
        self.excluded_themes = excluded_themes

    def theme_metadata(self):
        """
        Returns the ThemeMetaData for the currently set theme.
        """
        if not self.theme_structure:
            raise GWConfigError("Attempted to retrieve theme data for an asset class that doesn't use themes.")
        if self.theme_name and (self.theme_name != "default"):
            return self.available_themes[self.theme_name]
        else:
            return ThemeMetaData()

    def theme_citation(self):
        citation = " by " + self.theme_metadata().author if self.theme_metadata().author else ""
        return (self.theme_name, citation)

    def themes(self) -> Dict[str, ThemeMetaData]:
        """
        Scans the themes folder and returns a dictionary of all available themes
        (minus exclusions), along with their metadata.
        """
        if not self.theme_structure:
            raise GWConfigError("Attempted to retrieve theme data for an asset class that doesn't use themes.")
        if self.available_themes:
            return self.available_themes

        self.available_themes = self.find_themes()
        for fallback in self.excluded_themes:
            if fallback in self.available_themes:
                del self.available_themes[fallback]
        if self.theme_name not in self.available_themes:
            self.theme_name = ""
        return self.available_themes

    def fetch_theme_metadata(self, parser: GWConfigParser) -> ThemeMetaData:
        theme_meta = ThemeMetaData()
        section = "Main"
        if parser.has_section(section):
            theme_meta.name = parser[section].gettext("name", "")
            theme_meta.description = parser[section].gettext("description", "")
            theme_meta.author = parser[section].gettext("author", "")
            theme_meta.credit = parser[section].gettext("credit", "")
            theme_meta.url = parser[section].gettext("url", "")
            theme_meta.license = parser[section].gettext("license", "")
            theme_meta.license_url = parser[section].gettext("licenseurl", "")
        return theme_meta

    def find_themes(self) -> Dict[str, ThemeMetaData]:
        """
        Recursively scans the specified folder for theme specs according to
        the ThemeStructure (e.g. a subfolder alone for icons, a .conf and/or
        .yaml file for skins).

        In the case of conf files, they need to be in INI format with a
        [Main] section that has the metadata for the scheme (a name at the very least).
        The rest of the contents (additional sections) depend on the asset class.

        In the case of yaml files, they are assumed to be "Base16" color schemes
        in yaml format. They have exacly 18 lines: a scheme name, an author, and a
        palette of 16 colors. These Base16 files are applicable as skin assets and
        syntax assets.

        The file names are meaningless as far as .conf and .yaml files go.
        The name that is in the metadata is what matters.
        Feel free to name them however you like and organize them by subfolder
        however you like.

        In the case of subfolder-alone (e.g. icons), the fold name is used as the
        theme name.
        """
        themes = {}
        if self.theme_structure.uses_base16():
            for child in self.asset_path.glob("**/*.yaml"):
                if child.name == "default":
                    raise GWConfigError(f"Illegal asset: {self.asset_path}/{child.name}.yaml -- 'default' is a reserved theme name.")
                # LOG.debug(f"yaml file found: {str(child)}")
                try:
                    with child.open("r") as f:
                        base16 = yaml.load(f.read())
                        # LOG.debug(f"base16 = {base16}")
                    theme_info = ThemeMetaData(base16["scheme"],base16["author"],filename = str(child))
                    themes[theme_info.name] = theme_info
                except Exception:
                    LOG.warning(f"Skipping: Unable to parse {str(child)}.")

        if self.theme_structure.uses_conf():
            parser = GWConfigParser()
            for child in self.asset_path.glob("**/*.conf"):
                if child.name == "default":
                    raise GWConfigError(f"Illegal asset: {self.asset_path}/{child.name}.conf -- 'default' is a reserved theme name.")
                LOG.debug(f"conf file found: {str(child)}")
                parser.parse_file(child)
                theme_info = self.fetch_theme_metadata(parser)
                theme_info.filename = str(child)
                themes[theme_info.name] = theme_info

        if self.theme_structure.uses_csv():
            for child in self.asset_path.glob("**/*.csv"):
                LOG.debug(f"CSV file found: {str(child)}")
                if child.name == "default":
                    raise GWConfigError(f"Illegal asset: {self.asset_path}/{child.name}.csv -- 'default' is a reserved theme name.")
                theme_info = ThemeMetaData(child.name, filename=str(child))
                themes[theme_info.name] = theme_info

        if self.theme_structure.by_folder_alone():
            for child in self.asset_path.iterdir():
                if child.is_dir():
                    if child.name == "default":
                        raise GWConfigError(f"Illegal asset: {self.asset_path}/{child.name} -- 'default' is a reserved theme name.")
                    LOG.debug(f"icon folder found: {child.name}")
                    theme_info = ThemeMetaData(child.name, filename=str(child))
                    themes[theme_info.name] = theme_info

        LOG.debug(f"Themes found: {themes.keys()}")
        return themes




