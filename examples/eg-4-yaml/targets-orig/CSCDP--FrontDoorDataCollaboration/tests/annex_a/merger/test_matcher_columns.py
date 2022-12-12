import unittest
from dacite import from_dict
import yaml
import numpy as np

import fddc.annex_a.merger.matcher_report
from fddc.annex_a.merger import matcher
from fddc.annex_a.merger.configuration import RegexMatcherConfig
from fddc.annex_a.merger.matcher import MatchedSheet
from fddc.annex_a.merger.workbook_util import WorkSheetHeaderItem


class TestConfiguration(unittest.TestCase):

    def test_match_header(self):
        header_list = [
            WorkSheetHeaderItem(value="Test", column_index=0),
            WorkSheetHeaderItem(value="Dummy", column_index=1),
            WorkSheetHeaderItem(value="Header 1", column_index=2),
            WorkSheetHeaderItem(value="Header 2", column_index=3),
        ]

        matcher_list = [
            RegexMatcherConfig('/Header 1/i'),
            RegexMatcherConfig('/Header X/i')
        ]

        result = matcher._match_header(header_list, matcher_list)
        self.assertEqual(result, header_list[2])

    def test_match_single_column(self):
        sheet = self._get_test_sheet()

        result_sheet_list = matcher.match_columns(sheet)
        self.assertEqual(len(result_sheet_list), 1)
        self.assert_sheet(result_sheet_list[0], sheet)

    def test_match_multiple_column(self):
        sheet = self._get_test_sheet()

        result_sheet_list = matcher.match_columns([sheet])
        self.assertEqual(len(result_sheet_list), 1)
        self.assert_sheet(result_sheet_list[0], sheet)

    def test_column_report(self):
        sheet = self._get_test_sheet()
        result_sheet_list = matcher.match_columns([sheet])
        report = fddc.annex_a.merger.matcher_report.column_report(result_sheet_list)

        self.assertEqual([
            'filename',
            'sort_key',
            'header_starts',
            'sheetname',
            'table',
            'column_name',
            'header_name',
        ], report.columns.tolist())
        self.assertEqual(report.column_name.tolist(), ['Header 1', 'Header X', 'Header Y', np.nan])
        self.assertEqual(report.header_name.tolist(), ['Header 1', 'Header   X', '', 'Header T'])

    def assert_sheet(self, result_sheet, sheet):
        self.assertEqual(result_sheet.sheet, sheet)
        self.assertEqual(len(result_sheet.columns), 2)
        self.assertEqual(result_sheet.columns[0].header.column_index, 2)
        self.assertEqual(result_sheet.columns[1].header.column_index, 1)

    @staticmethod
    def _get_test_sheet():
        sheet = """
source_config:
    name: Test Source
    columns:
        - name: Header 1
        - name: Header X
        - name: Header Y
sheet_detail:
    filename: Test Name
    headers:
        - value: Header T
          column_index: 0
        - value: Header   X
          column_index: 1
        - value: Header 1
          column_index: 2
        """
        return from_dict(data_class=MatchedSheet, data=yaml.safe_load(sheet))
