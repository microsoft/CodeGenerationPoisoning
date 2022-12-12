import logging
import json
import os
import yaml
from collections import namedtuple
import copy
from logging.handlers import RotatingFileHandler
from src.LabeledID import LabeledID
from src.prefixes import OMIM, OMIMPS, UMLS, SNOMEDCT, KEGGPATHWAY, KEGGREACTION, NCIT, ICD10

#loggers = {}
class LoggingUtil(object):
    """ Logging utility controlling format and setting initial logging level """
    @staticmethod
    def init_logging (name, level=logging.INFO, format='short', logFilePath=None, logFileLevel=None):
        logger = logging.getLogger(__name__)
        if not logger.parent.name == 'root':
            return logger

        FORMAT = {
            "short" : '%(funcName)s: %(message)s',
            "medium" : '%(funcName)s: %(asctime)-15s %(message)s',
            "long"  : '%(asctime)-15s %(filename)s %(funcName)s %(levelname)s: %(message)s'
        }[format]

        # create a stream handler (default to console)
        stream_handler = logging.StreamHandler()

        # create a formatter
        formatter = logging.Formatter(FORMAT)

        # set the formatter on the console stream
        stream_handler.setFormatter(formatter)

        # get the name of this logger
        logger = logging.getLogger(name)

        # set the logging level
        logger.setLevel(level)

        # if there was a file path passed in use it
        if logFilePath is not None:
            # create a rotating file handler, 100mb max per file with a max number of 10 files
            file_handler = RotatingFileHandler(filename=logFilePath + name + '.log', maxBytes=1000000, backupCount=10)

            # set the formatter
            file_handler.setFormatter(formatter)

            # if a log level for the file was passed in use it
            if logFileLevel is not None:
                level = logFileLevel

            # set the log level
            file_handler.setLevel(level)

            # add the handler to the logger
            logger.addHandler(file_handler)

        # add the console handler to the logger
        logger.addHandler(stream_handler)

        # return to the caller
        return logger

class Munge(object):
    @staticmethod
    def gene (gene):
        return gene.split ("/")[-1:][0] if gene.startswith ("http://") else gene
    
class Text:
    """ Utilities for processing text. """

    @staticmethod
    def get_curie (text):
        if isinstance(text,LabeledID):
            text = text.identifier
        return text.upper().split(':', 1)[0] if ':' in text else None

    @staticmethod
    def get_prefix (text):
        if isinstance(text,LabeledID):
            text = text.identifier
        return text.split(':', 1)[0] if ':' in text else None

    @staticmethod
    def recurie(text,new_prefix):
        """Given input CURIE and a new prefix, replace the old prefix with the new"""
        if isinstance(text, LabeledID):
            newident = f'{new_prefix}:{Text.un_curie(text.identifier)}'
            return LabeledID(newident,text.label)
        return f'{new_prefix}:{Text.un_curie(text)}'

    @staticmethod
    def un_curie (text):
        return ':'.join(text.split (':', 1)[1:]) if ':' in text else text
        
    @staticmethod
    def short (obj, limit=80):
        text = str(obj) if obj else None
        return (text[:min(len(text),limit)] + ('...' if len(text)>limit else '')) if text else None

    @staticmethod
    def path_last (text):
        return text.split ('/')[-1:][0] if '/' in text else text

    @staticmethod
    def obo_to_curie (text):
        """Converts /somthing/something/CL_0000001 to CL:0000001"""
        return ':'.join( text.split('/')[-1].split('_') )

    @staticmethod
    def opt_to_curie (text):
        if text is None:
            return None
        #grumble, I should be better about handling prefixes
        if text.startswith('http://purl.obolibrary.org') or text.startswith('http://www.orpha.net') or text.startswith('http://www.ebi.ac.uk/efo'):
            p = text.split('/')[-1].split('_')
            return ':'.join( p )
        if text.startswith('https://omim.org/'):
            ident = text.split("/")[-1]
            if ident.startswith('PS'):
                return f'{OMIMPS}:{ident[2:]}'
            return f'{OMIM}:{ident}'
        if text.startswith('http://linkedlifedata.com/resource/umls'):
            return f'{UMLS}:{text.split("/")[-1]}'
        if text.startswith('http://identifiers.org/'):
            p = text.split("/")
            return f'{p[-2].upper()}:{p[-1]}'
        if text.startswith('http://en.wikipedia.org/wiki'):
            return f'wikipedia.en:{text.split("/")[-1]}'
        if text.startswith('http://apps.who.int/classifications/icd10'):
            return f'{ICD10}:{text.split("/")[-1]}'
        if text.startswith('http://www.snomedbrowser.com/'):
            return f'{SNOMEDCT}:{text.split("/")[-1]}'
        if text.startswith('KEGG_PATHWAY'):
            return Text.recurie(text,KEGGPATHWAY)
        if text.startswith('NCIt'):
            return Text.recurie(text,NCIT)
        if text.startswith('KEGG_REACTION'):
            return Text.recurie(text,KEGGREACTION)
        return text

    @staticmethod
    def curie_to_obo (text):
        x = text.split(':')
        return f'<http://purl.obolibrary.org/obo/{x[0]}_{x[1]}>'


    @staticmethod
    def snakify(text):
        decomma = '_'.join( text.split(','))
        dedash = '_'.join( decomma.split('-'))
        resu =  '_'.join( dedash.split() )
        return resu

    @staticmethod
    def upper_curie(text):
        if ':' not in text:
            return text
        p = text.split(':', 1)
        return f'{p[0].upper()}:{p[1]}'



class Resource:
    @staticmethod
    def get_resource_path(resource_name):
        """ Given a string resolve it to a module relative file path unless it is already an absolute path. """
        resource_path = resource_name
        if not resource_path.startswith (os.sep):
            resource_path = os.path.join (os.path.dirname (__file__), resource_path)
        return resource_path
    @staticmethod
    def load_json (path):
        result = None
        with open (path, 'r') as stream:
            result = json.loads (stream.read ())
        return result

    @staticmethod
    def load_yaml (path):
        result = None
        with open (path, 'r') as stream:
            result = yaml.load (stream.read ())
        return result
    
    def get_resource_obj (resource_name, format='json'):
        result = None
        path = Resource.get_resource_path (resource_name)
        if os.path.exists (path):
            m = {
                'json' : Resource.load_json,
                'yaml' : Resource.load_yaml
            }
            if format in m:
                result = m[format](path)
        return result

    @staticmethod
    # Modified from:
    # Copyright Ferry Boender, released under the MIT license.
    def deepupdate(target, src, overwrite_keys = []):
        """Deep update target dict with src
        For each k,v in src: if k doesn't exist in target, it is deep copied from
        src to target. Otherwise, if v is a list, target[k] is extended with
        src[k]. If v is a set, target[k] is updated with v, If v is a dict,
        recursively deep-update it.

        Updated to deal with yaml structure: if you have a list of yaml dicts,
        want to merge them by "name"

        If there are particular keys you want to overwrite instead of merge, send in overwrite_keys
        """
        if type(src) == dict:
            for k, v in src.items():
                if k in overwrite_keys:
                    target[k] = copy.deepcopy(v)
                elif type(v) == list:
                    if not k in target:
                        target[k] = copy.deepcopy(v)
                    elif type(v[0]) == dict:
                        Resource.deepupdate(target[k],v,overwrite_keys)
                    else:
                        target[k].extend(v)
                elif type(v) == dict:
                    if not k in target:
                        target[k] = copy.deepcopy(v)
                    else:
                        Resource.deepupdate(target[k], v,overwrite_keys)
                elif type(v) == set:
                    if not k in target:
                        target[k] = v.copy()
                    else:
                        target[k].update(v.copy())
                else:
                    target[k] = copy.copy(v)
        else:
            #src is a list of dicts, target is a list of dicts, want to merge by name (yikes)
            src_elements = { x['name']: x for x in src }
            target_elements = { x['name']: x for x in target }
            for name in src_elements:
                if name in target_elements:
                    Resource.deepupdate(target_elements[name], src_elements[name],overwrite_keys)
                else:
                    target.append( src_elements[name] )


class DataStructure:
    @staticmethod
    def to_named_tuple (type_name, d):
        return namedtuple(type_name, d.keys())(**d)
