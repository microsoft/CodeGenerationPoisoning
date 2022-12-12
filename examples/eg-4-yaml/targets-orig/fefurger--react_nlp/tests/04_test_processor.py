#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import unittest
import yaml

from unitex import UnitexConstants
from unitex.config import UnitexConfig
from unitex.tools import compress, grf2fst2
from unitex.processor import UnitexProcessor



class Arguments:

    def __init__(self, language=None):
        self.__arguments = {}

        self.__arguments["config"] = "data/unitex.yaml"

        self.__arguments["alphabet"] = "data/Alphabet.txt" 

        self.__arguments["dic"] = "data/dictionary.dic"
        self.__arguments["bin"] = "data/dictionary.bin"
        self.__arguments["inf"] = "data/dictionary.inf"

        self.__arguments["grf"] = "data/grammar.grf"
        self.__arguments["fst2"] = "data/grammar.fst2"

        self.__arguments["txt"] = "data/corpus.txt"
        self.__arguments["tag"] = "data/corpus.tag"
        self.__arguments["xml"] = "data/corpus.xml"

    def __getitem__(self, key):
        if key not in self.__arguments:
            raise KeyError("Argument '%s' not found ..." % key)
        return self.__arguments[key]



class TestUnitexIO(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self._arguments = Arguments()

        dictionary = self._arguments["dic"]

        kwargs = {}
        kwargs["output"] = None
        kwargs["flip"] = False
        kwargs["semitic"] = False
        kwargs["version"] = UnitexConstants.DICTIONARY_VERSION_1

        ret = compress(dictionary, **kwargs)

        grammar = self._arguments["grf"]
        alphabet = self._arguments["alphabet"]

        kwargs = {}
        kwargs["loop_check"] = False
        kwargs["char_by_char"] = False
        kwargs["pkgdir"] = None
        kwargs["no_empty_graph_warning"] = False
        kwargs["tfst_check"] = False
        kwargs["silent_grf_name"] = False
        kwargs["named_repositories"] = None
        kwargs["debug"] = False
        kwargs["check_variables"] = False

        ret = grf2fst2(grammar, alphabet, **kwargs)

    @classmethod
    def tearDownClass(self):
        if os.path.exists(self._arguments["bin"]):
            os.remove(self._arguments["bin"])

        if os.path.exists(self._arguments["inf"]):
            os.remove(self._arguments["inf"])

        if os.path.exists(self._arguments["fst2"]):
            os.remove(self._arguments["fst2"])

        if os.path.exists(self._arguments["tag"]):
            os.remove(self._arguments["tag"])

        if os.path.exists(self._arguments["xml"]):
            os.remove(self._arguments["xml"])

    def test_01_processor_txt(self):
        options = None
        with open(self._arguments["config"], "r") as f:
            options = yaml.load(f)

        config = UnitexConfig()
        config.load(options)

        processor = UnitexProcessor(config)
        processor.open(self._arguments["txt"], mode="srtlf", tagged=False)

        kwargs = {}
        kwargs["xml"] = False

        ret = processor.tag(self._arguments["fst2"], self._arguments["tag"], **kwargs)

        processor.close(clean=True, free=True)
        self.assertTrue(ret, "Tagging process failed (txt format)!")

    def test_02_processor_xml(self):
        options = None
        with open(self._arguments["config"], "r") as f:
            options = yaml.load(f)

        config = UnitexConfig()
        config.load(options)

        processor = UnitexProcessor(config)
        processor.open(self._arguments["txt"], mode="srtlf", tagged=False)

        kwargs = {}
        kwargs["xml"] = True

        ret = processor.tag(self._arguments["fst2"], self._arguments["xml"], **kwargs)

        processor.close(clean=True, free=True)
        self.assertTrue(ret, "Tagging process failed (xml format)!")



if __name__ == '__main__':
    unittest.main()
