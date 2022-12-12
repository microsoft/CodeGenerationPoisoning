'''
Created on November 22, 2020

@author: welling
'''

import requests
import json
import yaml
from typing import Union, List, Iterable, Dict, Any, TypeVar
from requests.exceptions import TooManyRedirects
from pprint import pprint
from .singleton_metaclass import SingletonMetaClass

BoolOrNone = Union[bool, None]

StringOrNone = Union[str, None]

StrOrListStr = TypeVar('StrOrListStr', str, List[str])

JSONType = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]

"""Some example type data for use by the dummy type client"""
DUMMY_CLIENT_YAML = """
salmon_rnaseq_bulk:
#RNAseq-bulk_salmon:
    description: Bulk RNA-seq [Salmon]
#    alt-names: [salmon_rnaseq_bulk]
    alt-names: []
    primary: false
    contains-pii: false
    vitessce-hints: []

CODEX:
    description: CODEX
    alt-names: []
    primary: true
    contains-pii: false
    vitessce-hints: []

codex_cytokit:
    description: CODEX [Cytokit + SPRM]
    alt-names: []
    primary: false
    contains-pii: false
    vitessce-hints: ['codex', 'is_image', 'is_tiled']

image_pyramid:
    description: Image Pyramid
    alt-names: []
    primary: false
    contains_pii: false
    vis-only: true
    vitessce-hints: ['is_image', 'pyramid']

SNARE-ATACseq2:
    description: snATACseq (SNARE-seq2)
    alt-names: ['SNAREseq', 'SNARE2-ATACseq']
    primary: true
    contains-pii: true
    vitessce-hints: []

SNARE-RNAseq2:
    description: snRNAseq (SNARE-seq2)
    alt-names: ['SNARE2-RNAseq']
    primary: true
    contains-pii: true
    vitessce-hints: []

sc_atac_seq_snare_lab:
    description: snATAC-seq (SNARE-seq2) [Lab Processed]
    alt-names: []
    primary: false
    vitessce-hints: []

sc_rna_seq_snare_lab:
    description: snRNA-seq (SNARE-seq2) [Lab Processed]
    alt-names: []
    primary: false
    vitessce-hints: []

salmon_rnaseq_snareseq:
    description: snRNA-seq (SNARE-seq2) [Salmon]
    alt-names: []
    primary: false
    contains-pii: false
    vitessce-hints: ['is_sc', 'rna']

sc_atac_seq_snare:
    description: snATAC-seq (SNARE-seq2) [SnapATAC]
    alt-names: []
    primary: false
    contains-pii: false
    vitessce-hints: ['is_sc', 'atac']

scRNA-Seq-10x:
    description: scRNA-seq (10x Genomics)
    alt-names: []
    primary: true
    contains-pii: true
    vitessce-hints: []

scRNA-Seq-10x_salmon:
    description: scRNA-seq (10x Genomics) [Salmon]
    alt-names: [salmon_rnaseq_10x]
    primary: false
    contains-pii: false
    vitessce-hints: ['is_sc', 'rna']

PAS:
    description: PAS Stained Microscopy
    alt-names: []
    primary: true
    contains-pii: false
    vitessce-hints: []

PAS_pyramid:
    description: PAS Stained Microscopy [Image Pyramid]
    alt-names: [["PAS", "Image Pyramid"], ["Image Pyramid", "PAS"]]
    primary: false
    contains-pii: false
    vis-only: true
    vitessce-hints: ['is_image', 'pyramid']

"""


class _AssayType(object):
    """
    A class representing a single assay type, accessible only via
    TypeClient.getAssayType and .iterAssays
    """
    name: str
    description: str
    primary: bool

    def __init__(self, info: Dict[str, Any]):
        """
        The instance is initialized based on a dict provided by TypeClient.
        The dict must match the format produced by self.to_json().
        """
        # Needs to set self.name, self.description, self.primary
        self.name = info['name']
        self.description = info['description']
        self.primary = info['primary']
        self.vitessce_hints = info.get('vitessce-hints', [])
        self.contains_pii = info.get('contains-pii',
                                     True) # Fail True for safety
        self.vis_only = info.get('vis-only',
                                 False)  # False is more common.

    def to_json(self) -> Dict[str, Any]:
        """
        Returns a JSON-compatible representation of the assay type
        """
        return {'name': self.name, 'primary': self.primary,
                'description': self.description,
                'vitessce-hints': self.vitessce_hints,
                'contains-pii': self.contains_pii,
                'vis-only': self.vis_only}

    def __str__(self) -> str:
        return(f'AssayType({self.description})')

    def __repr__(self) -> str:
        return(f'AssayType({self.to_json()})')

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.to_json() == other.to_json()
        else:
            raise NotImplementedError()

    def __ne__(self, other):
        if isinstance(other, type(self)):
            return self.to_json() != other.to_json()
        else:
            raise NotImplementedError()


class TypeClient(object, metaclass=SingletonMetaClass):
    """
    This is a singleton- only a single instance of this class is ever created.
    If the constructor is called again, it returns the same instance as before.
    This is for convenience in initializing the service.
    """
    app_config: Dict[str, Any]

    def __init__(self, type_webservice_url: StringOrNone = None):
        """
        type_webservice_url must be provided the first time the constructor is
        called.  Thereafter, all calls return the same instance and are already
        initialized with that service URL.
        """
        if type_webservice_url is None:
            if not (hasattr(self, 'app_config')
                    and 'TYPE_WEBSERVICE_URL' in self.app_config):
                raise RuntimeError('TypeClient has not been initialized')
        else:
            self.app_config = {}
            if not type_webservice_url.endswith('/'):
                type_webservice_url += '/'  # Avoid a common config problem
            self.app_config['TYPE_WEBSERVICE_URL'] = type_webservice_url

    def _wrapped_transaction(self, url, data=None, method="GET") -> JSONType:
        """
        Provide error and exception handling for requests.
        """
        try:
            if method == "GET":
                assert data is None, "No message body for GET transactions"
                r = requests.get(url,
                                 headers={'Content-Type': 'application/json'})
            elif method == "POST":
                r = requests.post(url,
                                  headers={'Content-Type': 'application/json'},
                                  json=data)
            else:
                raise RuntimeError("Unsupported transaction type")
            if r.ok is True:
                return json.loads(r.content.decode())
            else:
                msg = ('HTTP Response: ' + str(r.status_code) + ' msg: '
                       + str(r.text))
                raise Exception(msg)
        except ConnectionError as connerr:
            # "connerr"...get it? like "ConAir"... chb69
            pprint(connerr)
            raise connerr
        except TimeoutError as toerr:
            pprint(toerr)
            raise toerr
        except TooManyRedirects as toomany:
            pprint(toomany)
            raise toomany
        except Exception as e:
            pprint(e)
            raise e

    def getAssayType(self, name: StrOrListStr) -> _AssayType:
        """
        Given an assay name, return the associated assay type.  If a deprecated
        alt-name is provided, the returned assay type will use the up-to-date
        name.
        """
        url = self.app_config['TYPE_WEBSERVICE_URL'] + 'assayname'
        data = self._wrapped_transaction(url, method='POST',
                                         data={'name': name})
        assert isinstance(data, Dict)
        return _AssayType(data)

    def iterAssayNames(self, primary: BoolOrNone = None) -> Iterable[str]:
        """
        Return an iterator over valid assay name strings.

        primary: controls the subset of valid names, as follows:
            None or not specified: return all valid names.
            True: return only the names of primary assay types, that is,
                those for which no parent is an assay.
            False: return only the names of non-primary assay types.
        """
        url = self.app_config['TYPE_WEBSERVICE_URL'] + 'assaytype?simple=true'
        if primary is not None:
            if primary:
                url += '&primary=true'
            else:
                url += '&primary=false'
        data = self._wrapped_transaction(url)
        assert isinstance(data, Dict) and 'result' in data
        assert isinstance(data['result'], List)
        for elt in data['result']:
            assert isinstance(elt, str)
            yield elt

    def iterAssays(self, primary: BoolOrNone = None) -> Iterable[_AssayType]:
        """
        Return an iterator over valid assay types.

        primary: controls the subset of valid assay types, as follows:
            None or not specified: return all valid types.
            True: return only primary assay types, that is, those for which no
                parent is an assay.
            False: return only non-primary assay types.
        """
        url = self.app_config['TYPE_WEBSERVICE_URL'] + 'assaytype?simple=false'
        if primary is not None:
            if primary:
                url += '&primary=true'
            else:
                url += '&primary=false'
        data = self._wrapped_transaction(url)
        assert isinstance(data, Dict) and 'result' in data
        assert isinstance(data['result'], List)
        for elt in data['result']:
            assert isinstance(elt, Dict)
            yield _AssayType(elt)


class DummyTypeClient(object, metaclass=SingletonMetaClass):
    """
    This local-only version of TypeClient is provided for testing purposes.

    This is a singleton- only a single instance of this class is ever created.
    If the constructor is called again, it returns the same instance as before.
    This is for convenience in initializing the service.
    """
    app_config: Dict[str, Any]

    def __init__(self, type_webservice_url: StringOrNone = None):
        """
        type_webservice_url must be provided the first time the constructor is
        called.  Thereafter, all calls return the same instance and are already
        initialized with that service URL.
        """
        if type_webservice_url is None:
            if not (hasattr(self, 'app_config')
                    and 'TYPE_WEBSERVICE_URL' in self.app_config):
                raise RuntimeError('TypeClient has not been initialized')
        else:
            self.app_config = {}
            if not type_webservice_url.endswith('/'):
                type_webservice_url += '/'  # Avoid a common config problem
            self.app_config['TYPE_WEBSERVICE_URL'] = type_webservice_url
            self.examples = yaml.safe_load(DUMMY_CLIENT_YAML)
            for nm in self.examples:
                self.examples[nm]['name'] = nm
            map = {}
            for k, v in self.examples.items():
                for nm in v['alt-names']:
                    safe_nm = nm if isinstance(nm, str) else tuple(nm)
                    map[safe_nm] = k
            self.alt_name_map = map

    def getAssayType(self, name: StrOrListStr) -> _AssayType:
        """
        Given an assay name, return the associated assay type.  If a deprecated
        alt-name is provided, the returned assay type will use the up-to-date
        name.
        """
        safe_name = name if isinstance(name, str) else tuple(name)
        if safe_name in self.examples:
            type_name = safe_name
        elif safe_name in self.alt_name_map:
            type_name = self.alt_name_map[safe_name]
        else:
            raise RuntimeError(
                f'No such assay_type {name}, even as alternate name')
        return _AssayType(self.examples[type_name])

    def iterAssayNames(self, primary: BoolOrNone = None) -> Iterable[str]:
        """
        Return an iterator over valid assay name strings.

        primary: controls the subset of valid names, as follows:
            None or not specified: return all valid names.
            True: return only the names of primary assay types, that is,
                those for which no parent is an assay.
            False: return only the names of non-primary assay types.
        """
        if primary is None:
            for name in self.examples:
                yield name
        else:
            if primary:
                for name in [nm for nm, v in self.examples.items()
                             if v['primary']]:
                    yield name
            else:
                for name in [nm for nm, v in self.examples.items()
                             if not v['primary']]:
                    yield name

    def iterAssays(self, primary: BoolOrNone = None) -> Iterable[_AssayType]:
        """
        Return an iterator over valid assay types.

        primary: controls the subset of valid assay types, as follows:
            None or not specified: return all valid types.
            True: return only primary assay types, that is, those for which no
                parent is an assay.
            False: return only non-primary assay types.
        """
        for name in self.iterAssayNames(primary=primary):
            yield _AssayType(self.examples[name])
