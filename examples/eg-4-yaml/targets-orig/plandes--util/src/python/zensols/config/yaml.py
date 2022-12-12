"""Application configuration classes parsed from YAML files.

"""
__author__ = 'Paul Landes'

from typing import Dict, Tuple, Set, Any, Union, Optional, List, Type
import logging
from pathlib import Path
from io import TextIOBase
import yaml
from zensols.config import (
    ConfigurableFileNotFoundError, Configurable, Dictable
)

logger = logging.getLogger(__name__)


class YamlConfig(Configurable, Dictable):
    """Just like :class:`.IniConfig` but parse configuration from YAML files.
    Variable substitution works just like ini files, but you can set what
    delimiter to use and keys are the paths of the data in the hierarchy
    separated by dots.

    See the test cases for example.

    """
    CLASS_VER = 0

    def __init__(self, config_file: Union[str, Path, TextIOBase] = None,
                 default_section: str = None, default_vars: str = None,
                 delimiter: str = '$', sections_name: str = 'sections',
                 sections: Set[str] = None):
        """Initialize this instance.  When sections are not set, and the sections are
        not given in configuration file at location :obj:`sections_name` the
        root is made a singleton section.

        :param config_file: the configuration file path to read from; if the
                            type is an instance of :class:`io.TextIOBase`, then
                            read it as a file object

        :param default_section: used as the default section when non given on
                                the get methds such as :meth:`get_option`;
                                which defaults to ``defualt``

        :param default_vars: **depreciated**; artifact from the old
                             configuration defaults based INI config

        :param delimiter: the delimiter used for template replacement with dot
                          syntax, or ``None`` for no template replacement

        :param sections_name: the dot notated path to the variable that has a
                              list of sections

        :param sections: used as the set of sections for this instance

        """
        super().__init__(default_section)
        if isinstance(config_file, str):
            self.config_file = Path(config_file)
        else:
            self.config_file = config_file
        self.default_vars = default_vars if default_vars else {}
        self.delimiter = delimiter
        self.sections_name = sections_name
        if sections is not None:
            self.sections = sections

    @classmethod
    def _is_primitive(cls, obj) -> bool:
        return isinstance(obj, (float, int, bool, str, set,
                                list, tuple, Type, Path))

    def _flatten(self, context: Dict[str, Any], path: str,
                 n: Dict[str, Any], sep: str = '.'):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'path: {path}, n: <{n}>, context: <{context}>')
        if n is None:
            context[path] = None
        elif self._is_primitive(n):
            context[path] = n
        elif isinstance(n, dict):
            for k, v in n.items():
                k = path + sep + k if len(path) else k
                self._flatten(context, k, v, sep)
        else:
            self._raise(f'Unknown yaml type {type(n)}: {n}')

    def _parse(self) -> Tuple[str, Dict[str, str], Dict[str, str]]:
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'parsing: {self.config_file}')
        cfile = self.config_file
        if not cfile.is_file():
            raise ConfigurableFileNotFoundError(cfile)
        if isinstance(cfile, TextIOBase):
            content = cfile
        else:
            with open(cfile) as f:
                content = f.read()
        struct = yaml.load(content, yaml.FullLoader)
        context = {}
        context.update(self.default_vars)
        self._flatten(context, '', struct)
        self._all_keys = set(context.keys())
        return content, struct, context

    def _make_class(self) -> type:
        class_name = 'YamlTemplate{}'.format(self.CLASS_VER)
        self.CLASS_VER += 1
        # note we have to give the option of different delimiters since the
        # default '$$' (use case=OS env vars) is always resolved to '$' given
        # the iterative variable substitution method
        #
        # Yes, this really is necessary.  From the string.Template
        # documentation: Advanced usage: you can derive subclasses of Template
        # to customize the placeholder syntax, delimiter character, or the
        # entire regular expression used to parse template strings. To do this,
        # you can override these class attributes:
        code = """\
from string import Template
class """ + class_name + """(Template):
     idpattern = r'[a-z][_a-z0-9.]*'
     delimiter = '""" + self.delimiter + '\''
        exec(code)
        cls = eval(class_name)
        return cls

    def _compile(self) -> Dict[str, Any]:
        content, struct, context = self._parse()
        prev = None
        if self.delimiter is not None:
            cls = self._make_class()
            while prev != content:
                prev = content
                # TODO: raise here for missing keys embedded in the file rather
                # than KeyError
                content = cls(content).substitute(context)
        return yaml.load(content, yaml.FullLoader)

    @property
    def config(self) -> Dict[str, Any]:
        if not hasattr(self, '_config'):
            self._config = self._compile()
        return self._config

    def _from_dictable(self, recurse: bool, readable: bool,
                       class_name_param: str = None) -> Dict[str, Any]:
        return self.config

    def _find_node(self, n: Union[Dict, Any], path: str, name: str):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'search: n={n}, path={path}, name={name}')
        if path == name:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'found: <{n}>')
            return n
        elif isinstance(n, dict):
            for k, v in n.items():
                k = path + '.' + k if len(path) else k
                v = self._find_node(v, k, name)
                if v is not None:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'found {name} -> {v}')
                    return v
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('not found: {}'.format(name))

    def get_tree(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get the YAML tree for a node in the configuration.

        :param name: the doted notation indicating which node in the tree to
                     retrieve

        """
        if name is None:
            return self.config
        return self._find_node(self.config, '', name)

    def _get_option(self, name: str) -> str:
        node = self.get_tree(name)
        if self._is_primitive(node):
            return node
        elif self.default_vars is not None and name in self.default_vars:
            return self.default_vars[name]
        elif node is None:
            # values in YAML can be set to ``null``
            return None
        else:
            self._raise(f'Unknown type or state: {name} ({type(node)})')

    def set_option(self, name: str, value: str, section: str = None):
        """This is a no-op for now as client's don't expect an exception."""
        pass

    @property
    def options(self) -> Dict[str, Any]:
        if not hasattr(self, '_options'):
            self.config
            self._options = {}
            for k in self._all_keys:
                self._options[k] = self._get_option(k)
        return self._options

    def reload(self):
        if hasattr(self, '_options'):
            del self._options
            del self._all_keys

    def has_option(self, name: str):
        opts = self.options
        return name in opts

    def get_option(self, name: str, section: str = None) -> str:
        """Return an option using a dot encoded path.

        :param section: ignored

        """
        if self.default_vars is not None and name in self.default_vars:
            return self.default_vars[name]
        else:
            ops = self.options
            if name in ops:
                return ops[name]
            else:
                self._raise(f'No such option: {name}')

    def get_options(self, name: str = None) -> Dict[str, Any]:
        name = self.default_section if name is None else name
        if self.default_vars is not None and name in self.default_vars:
            return self.default_vars[name]
        else:
            node = self.get_tree(name)
            if not isinstance(node, str) or isinstance(node, list):
                return node
            elif name in self.default_vars:
                return self.default_vars[name]
            else:
                self._raise(f'No such option: {name}')

    @property
    def root(self) -> str:
        """Return the (first) root name of the Yaml configuration file.

        """
        if not hasattr(self, '_root'):
            root_keys = self.config.keys()
            self._root = next(iter(root_keys))
        return self._root

    def _get_at_depth(self, node: Any, s_level: int, level: int,
                      path: List[str]) -> Set[str]:
        def map_node(x: Tuple[str, Any]) -> str:
            k, v = x
            if isinstance(v, dict):
                if len(path) > 0:
                    k = '.'.join(path) + '.' + k
            else:
                k = None
            return k

        nodes: Set[str] = set()
        if isinstance(node, dict):
            if level < s_level:
                for k, child in node.items():
                    path.append(k)
                    ns = self._get_at_depth(child, s_level, level+1, path)
                    path.pop()
                    nodes.update(ns)
            elif level == s_level:
                return set(filter(lambda x: x is not None,
                                  map(map_node, node.items())))
        return nodes

    def _find_sections(self) -> Set[str]:
        secs: Set[str]
        sec_key = f'{self.root}.{self.sections_name}'
        if self.has_option(sec_key):
            secs: Dict[str, Any] = self.get_tree(sec_key)
            if isinstance(secs, str):
                secs = self.get_option_list(sec_key)
            elif isinstance(secs, int):
                secs = self._get_at_depth(self.get_tree(None), secs, 0, [])
            secs = frozenset(secs)
        else:
            secs = self._get_at_depth(self.get_tree(None), 0, 0, [])
        return secs

    @property
    def sections(self) -> Set[str]:
        """Return the sections by finding the :obj:`section_name` based from the
        :obj:`root`.

        """
        if not hasattr(self, '_sections'):
            self._sections = self._find_sections()
        return self._sections

    @sections.setter
    def sections(self, sections: Set[str]):
        self._sections = sections
