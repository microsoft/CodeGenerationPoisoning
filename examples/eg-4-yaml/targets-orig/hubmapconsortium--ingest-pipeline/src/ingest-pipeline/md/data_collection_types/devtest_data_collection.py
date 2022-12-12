#! /usr/bin/env python

import os
import json
import glob
import pandas as pd
import numpy as np
import types
import yaml
from pprint import pprint

from data_collection import DataCollection

class DEVTESTDataCollection(DataCollection):
    category_name = 'DEVTEST'
    match_priority = 1.0 # >= 0.0; higher is better

    # expected_file pairs are (globable name, filetype key)
    expected_files = [('test.yml', "YAML"),
                      ]
    
    optional_files = [('*.ome.tiff', 'OME_TIFF')]
    
    @classmethod
    def test_match(cls, path):
        """
        Does the given path point to the top directory of a directory tree
        containing data of this collection type?
        """
        for match, _ in cls.expected_files:
            print('testing %s' % match)
            if not any(glob.iglob(os.path.join(path, match))):
                print('not found!')
                return False
        assert 'test.yml' in [a for a, b in cls.expected_files], 'name of my info file has changed?'
        with open(os.path.join(path, 'test.yml'), 'r') as f:
            md = yaml.safe_load(f)
            if 'collectiontype' not in md or md['collectiontype'] != 'devtest':
                return False
        
        return True
    
    def __init__(self, path):
        """
        path is the top level directory of the collection
        """
        super().__init__(path)
    

    def collect_metadata(self):
        rslt = {}
        md_type_tbl = self.get_md_type_tbl()
        for match, md_type in self.expected_files + self.optional_files:
            print('collect match %s' % match)
            for fpath in glob.iglob(os.path.join(self.topdir, match)):
                print('collect from path %s' % fpath)
                this_md = md_type_tbl[md_type](fpath).collect_metadata()
                if this_md is not None:
                    rslt[os.path.relpath(fpath, self.topdir)] = this_md
        cl = []
        for fname in os.listdir(self.topdir):
            fullname = os.path.join(self.topdir, fname)
            if fname.endswith('.yml'):
                cl.append(fname)
        rslt['components'] = cl
        rslt['collectiontype'] = 'devtest'
        print('after collect:')
        pprint(rslt)
        return rslt
    
    def filter_metadata(self, metadata):
        """
        This extracts the metadata which is actually desired downstream from the bulk of the
        metadata which has been collected.
        
        """
        rslt = {k : metadata[k] for k in ['collectiontype', 'components']}
        for cmp in metadata['components']:
            rslt.update(metadata[cmp])
        other_d = {}
        for k in metadata:
            if k not in rslt:
                other_d[k] = metadata[k]
        rslt['other_meta'] = other_d  # for debugging
        return rslt
            
        
