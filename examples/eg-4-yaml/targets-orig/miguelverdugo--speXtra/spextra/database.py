# -*- coding: utf-8 -*-
"""
Database for speXtra
"""
import os
import inspect
import shutil
from posixpath import join as urljoin

import yaml

from .utils import Config,  download_file, dict_generator

# Configurations

__all__ = ["Database", "SpecLibrary", "SpectrumContainer", "ExtCurvesLibrary",
           "ExtCurveContainer", "FilterSystem", "FilterContainer", "DefaultData"]

# Tables are displayed with a jsviewer by default
# Table.show_in_browser.__defaults__ = (5000, True, 'default', {'use_local_files': True},
#                                              None, 'display compact', None, 'idx')


class DataContainer:
    """
    Just a general container for the data

    It reads a YAML file and creates attributes with the kyes of the dictionary.

    Additionally it contains methods for nicely displaying the contents on the screen.
    """
    def __init__(self, filename):
        self.filename = filename
        with open(self.filename) as f:
            self.meta = yaml.safe_load(f)
        for key in self.meta:
            setattr(self, key, self.meta[key])

    def dump(self):
        """
        (Try to) nicely dump the contents of the library

        Returns
        -------

        """
        print(yaml.dump(self.meta,
                        indent=4, sort_keys=False, default_flow_style=False))


class Database(DataContainer):
    """
    This class contains the database.


    It also acts as a lazy fetcher for remote data.
    When asked for local absolute path to a file or directory, Database
    checks if the file or directory exists locally and, if so, returns it.
    If it doesn't exist, it first determines where to get it from.
    It first downloads the file ``{remote_root}/redirects.json`` and checks
    it for a redirect from ``{relative_path}`` to a full URL. If no redirect
    exists, it uses ``{remote_root}/{relative_path}`` as the URL.
    It downloads then downloads the URL to ``{rootdir}/{relative_path}``.
    For directories, ``.tar.gz`` is appended to the
    ``{relative_path}`` before the above is done and then the
    directory is unpacked locally.
    Parameters
    ----------
    rootdir : str or callable
        The local root directory, or a callable that returns the local root
        directory given no parameters. (The result of the call is cached.)
        Using a callable allows one to customize the discovery of the root
        directory (e.g., from a config file), and to defer that discovery
        until it is needed.
    remote_root : str
        Root URL of the remote server.
    """

    def __init__(self, silent=False):

        conf = Config()
        self.database_url = conf.get_database_url()

        if not self.database_url.endswith('/'):
            self.database_url = self.database_url + '/'

        self.data_dir = conf.get_data_dir()
        self.ymlfile = "index.yml"
        self.path = self.abspath(self.ymlfile, silent=silent)

        super().__init__(filename=self.path)

        self.liblist,  self.relpathlist = self._makelists()

    def abspath(self, relpath, reload=False, silent=False):
        """
        Return absolute path to file or directory, ensuring that it exists.
        If it doesn't exist it will download it from the remote host

        Otherwise, just look for ``{relpath}``.
        """

        abspath = os.path.join(self.data_dir, relpath)
        if (os.path.exists(abspath) is False) or (reload is True):
            print("updating/loading '%s'" % relpath )
            remote_path = relpath.split(os.sep)
            url = urljoin(self.database_url, *remote_path)
            download_file(url, abspath, silent=silent)

        return abspath

    def remove_database(self):
        """
        Remove database and all files
        """
        try:
            shutil.rmtree(self.data_dir)
            print("database at %s removed" % self.data_dir)
        except FileNotFoundError:
            print("database at %s doesn't exist" % self.data_dir)
            raise

    def update(self):
        """
        Force an update of the cached database file
        """
        self.abspath(self.ymlfile, reload=True,  silent=False)

    def _makelists(self):
        """
        just make lists of the libraries and paths in the database"
        """
        a = list(dict_generator(self.meta))
        separator = '/'
        libs = [e[1:] for e in a]
        liblist = [separator.join(e) for e in libs]
        relpathlist = [separator.join(e) for e in a]

        return liblist, relpathlist

    def __repr__(self):
        description = "Database:"
        remote = "url: " + self.database_url
        local = "path: " + self.data_dir

        return ' %s \n %s \n %s ' % (description, remote, local)

    def __dir__(self):
        str = "Database of spextra"
        return str


class DefaultData:
    """
    small class just to define defaults spectra and filters
    """
    def __init__(self, **kwargs):

        database = Database()
        self.default_filters_file = database.abspath("default_filters.yml")
        self.default_spectra_file = database.abspath("default_spectra.yml")
        self.default_curves_file = database.abspath("default_curves.yml")

        self.filters = self.setdict(self.default_filters_file, **kwargs)
        self.spectra = self.setdict(self.default_spectra_file, **kwargs)
        self.extcurves = self.setdict(self.default_curves_file, **kwargs)

    @staticmethod
    def setdict(ymlfile, **kwargs):
        database = Database()
        path = database.abspath(ymlfile, **kwargs)

        with open(path) as filename:
            dictionary = yaml.safe_load(filename)
        return dictionary

    @staticmethod
    def update():
        DefaultData(silent=False, reload=True)


class Library(DataContainer):
    """
    Class that contains the information of a Library, either spectral
    of a filter system, extinction curves, etc
    """
    def __init__(self, library_name):
        self.name = library_name
        database = Database()

        if library_name not in database.liblist:
            raise ValueError("Library '%s' not in the database" % library_name)
        else:
            index = database.liblist.index(library_name)
            self.relpath = database.relpathlist[index]

        self.ymlfile = "index.yml"
        self.path = database.abspath(os.path.join(self.relpath, self.ymlfile))
        self.dir = database.abspath(self.relpath)
        self.url = urljoin(database.data_dir, self.relpath, self.ymlfile)
        super().__init__(filename=self.path)

    def remove(self):
        """
        Remove library and all files.
        """
        try:
            shutil.rmtree(self.dir)
            print("library %s removed" % self.name)
        except FileNotFoundError:
            print("library %s doesn't exist" % self.name)
            raise

    def update(self):
        """
        Update the library file
        """
        database = Database()
        database.abspath(os.path.join(self.relpath, self.ymlfile), reload=True, silent=False)


class SpecLibrary(Library):

    def __init__(self, library_name):

        super().__init__(library_name)

        self.template_names = list(self.templates.keys())
        self.template_comments = list(self.templates.values())
        self.files = [t + self.file_extension for t in self.template_names]

    def download_all(self):
        """
        Download the whole library
        """

        database = Database()
        for template in self.template_names:
            database.abspath(os.path.join(self.library_name, template))

    def __repr__(self):
        description = "Spectral Library: " + self.library_name + " " + self.title
        spec_cov = "spectral coverage: " + str(self.spectral_coverage)
        units = "wave_unit: " + self.wave_unit + "  flux_unit: " + self.flux_unit
        templates = "Templates: " + str(self.template_names)

        return ' %s \n %s \n %s \n %s' % (description, spec_cov, units, templates)

    def __str__(self):
        return self.library_name


class FilterSystem(Library):
    """
        This class contains the information of a filter system

        """

    def __init__(self, filter_system):

        super().__init__(filter_system)

        self.filter_names = list(self.filters.keys())
        self.filter_comments = list(self.filters.values())
        self.files = [f + self.file_extension for f in self.filter_names]

    def download_all(self):
        """
        Download the whole library
        """

        database = Database()
        for filt in self.filter_names:
            database.abspath(os.path.join(self.filter_system, filt))

    def __repr__(self):
        description = "Filter system: " + self.filter_system + " " + self.title
        spec_cov = "spectral coverage: " + str(self.spectral_coverage)
        units = "wave_unit: " + self.wave_unit
        filters = "filters: " + str([self.name + "/" + k for k in self.filters.keys()])

        return ' %s \n %s \n %s \n %s' % (description, spec_cov, units, filters)

    def __str__(self):
        return self.filter_system


class ExtCurvesLibrary(Library):
    """
    Class that contains the information of the a Extinction Curve Library
    """
    def __init__(self, curve_library):

        super().__init__(curve_library)

        self.curve_names = list(self.curves.keys())
        self.curve_comments = list(self.curves.values())
        self.files = [e + self.file_extension for e in self.curve_names]

    def download_all(self):
        """
        Download the whole library
        """

        database = Database()
        for curve in self.curve_names:
            database.abspath(os.path.join(self.curve_name, curve))

    def __repr__(self):
        description = "Extinction Curves: " + self.name + " " + self.title
        units = "wave_unit: " + self.wave_unit + "  flux_unit: " + self.flux_unit
        templates = "Templates: " + str(self.curves)

        return ' %s \n %s \n %s \n %s' % (description, units, templates)

    def __str__(self):
        return self.curve_name


class SpectrumContainer(SpecLibrary):
    """
    A holder of spectral template information, including template characteristics and location
    """

    def __init__(self, template):
        self.template = template
        self.template_name = os.path.basename(self.template)

        library_name = os.path.dirname(self.template)
        super().__init__(library_name=library_name)

        if self.template_name not in self.template_names:
            raise ValueError("Template '%s' not in library" % self.template)

        self.datafile = self.template_name + self.file_extension

        database = Database()

        self.path = database.abspath(os.path.join(self.relpath, self.datafile))
        self.url = urljoin(database.database_url, self.relpath, self.datafile)
        self.template_comment = self.templates[self.template_name]
        self.filename = self.path
        self._update_attrs()

    def remove(self):
        """
        remove the file
        """
        try:
            shutil.rmtree(self.path)
            print("library %s removed" % self.path)
        except FileNotFoundError:
            print("file %s doesn't exist" % self.path)
            raise

    def _update_attrs(self):
        """
        Here to just delete unnecessary stuff
        Returns
        -------
        """
        self.meta.pop("templates", None)
        self.meta.pop("summary", None)
        self.__dict__.pop("templates", None)
        self.__dict__.pop("summary", None)
        self.__dict__.pop("template_names", None)
        self.__dict__.pop("template_comments", None)
        self.__dict__.pop("ymlfile", None)

    def __repr__(self):

        s1 = "Spectral template: %s" % (self.template)

        return s1


class FilterContainer(FilterSystem):

    def __init__(self, filter_name):

        self.filter_name = filter_name

        self.basename = os.path.basename(self.filter_name)
        filter_system = os.path.dirname(self.filter_name)

        super().__init__(filter_system=filter_system)
        if self.basename not in self.filters:
            raise ValueError("Filter %s not in library" % self.filter_name)

        database = Database()

        self.datafile = self.basename + self.file_extension
        self.path = database.abspath(os.path.join(self.relpath, self.datafile))
        self.url = urljoin(database.database_url, self.relpath, self.datafile)
        self.filter_comment = self.filters[self.basename]
        self.filename = self.path

        self._update_attrs()

    def remove(self):
        """
        remove the file
        """
        try:
            shutil.rmtree(self.path)
            print("file %s removed" % self.path)
        except FileNotFoundError:
            print("file %s doesn't exist" % self.path)
            raise

    def _update_attrs(self):
        """
        Here to just delete unnecessary stuff
        """
        self.meta.pop("filterrs", None)
        self.meta.pop("summary", None)
        self.__dict__.pop("filters", None)
        self.__dict__.pop("summary", None)
        self.__dict__.pop("filter_names", None)
        self.__dict__.pop("filter_comments", None)
        self.__dict__.pop("ymlfile", None)

    def __repr__(self):
        s = "Filter: " + self.filter_name
        return s


class ExtCurveContainer(ExtCurvesLibrary):

    def __init__(self, curve_name):

        self.curve_name = curve_name
        self.basename = os.path.basename(self.curve_name)
        curve_library = os.path.dirname(self.curve_name)

        super().__init__(curve_library=curve_library)

        if self.basename not in self.curve_names:
            raise ValueError("Extinction Curve '%s' not in library" % self.curve_name)

        database = Database()

        self.datafile = self.basename + self.file_extension
        self.path = database.abspath(os.path.join(self.relpath, self.datafile))
        self.url = urljoin(database.database_url, self.relpath, self.datafile)
        self.curve_comment = self.curves[self.basename]
        self.filename = self.path

        self._update_attrs()

    def remove(self):
        """
        remove the file
        """
        try:
            shutil.rmtree(self.path)
            print("file %s removed" % self.path)
        except FileNotFoundError:
            print("file %s doesn't exist" % self.path)
            raise

    def _update_attrs(self):
        """
        Here to just delete unnecessary stuff
        """
        self.meta.pop("curves", None)
        self.meta.pop("summary", None)
        self.__dict__.pop("curves", None)
        self.__dict__.pop("summary", None)
        self.__dict__.pop("curve_names", None)
        self.__dict__.pop("curve_comments", None)
        self.__dict__.pop("ymlfile", None)

    def __repr__(self):
        s = "Extinction curve: " + self.curve_name
        return s


# TODO: functions


def get_library(library_name):
    """
    Download library and all files
    """
    pass


def get_filter_system(filter_system):
    """
    download all filters of a system
    """
    pass


def get_extcurves(extinction_curves):
    """
    Download all extinction curves
    """
    pass


def download_database():
    """
    Download
    """
    pass


def set_root_dir(path):
    """
    Set the root dir where the files will be stored.
    Probably best way is to write a small file in the data directory.


    Also get root dir should be also able to read from that file.

    Database should be get rid of initialiting parameters or use them
    to set new directories
    """
    pass


#
def database_as_table():
    """
    Show the contents of the database as table
    Returns
    -------

    """

    pass


def database_as_tree():
    """
    Show the contents od the database as a tree
    Returns
    -------

    """
    pass



