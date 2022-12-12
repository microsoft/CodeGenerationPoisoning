import yaml
import multiprocessing

from mockito import any, mock, unstub, verify, when
from unittest import TestCase

from src.Multiprocess import Multiprocess

class TestMultiprocess(TestCase):

    def setUp(self):
        self.config = yaml.load(open("conf/dev/conf.yaml", 'r').read(), Loader=yaml.Loader)
        self.news_sources = {"news_id": ["news_url_0",
                                        "news_url_1",
                                        "news_url_2"]}
        self.multiproc = Multiprocess(self.config, "news_id", self.news_sources)

    def tearDown(self):
        unstub()

    def test_setup_process(self):
        mock_func = mock()
        mock_process_1 = mock()
        mock_process_2 = mock()
        mock_process_3 = mock()
        when(multiprocessing).Process(target=any(), args=("news_url_0",)).thenReturn(mock_process_1)
        when(multiprocessing).Process(target=any(), args=("news_url_1",)).thenReturn(mock_process_2)
        when(multiprocessing).Process(target=any(), args=("news_url_2",)).thenReturn(mock_process_3)

        self.multiproc.setup_processes(mock_func)

        expected_processes = {
            "news_id_0": mock_process_1,
            "news_id_1": mock_process_2,
            "news_id_2": mock_process_3,
        }
        self.assertEquals(expected_processes, self.multiproc.processes)
