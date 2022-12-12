import threading
import time
import uuid
import yaml

from src.citron_scraper import CitronScraper
from src.twitter_scraper import TwitterScraper
from src.ftc_scraper import FTCScraper

class ScrapersController(object):
    def __init__(self, config, news_sources):
        self.all_scrapers = {
            "citron_scraper": CitronScraper(config, "citron", news_sources),
            "twitter_scraper": TwitterScraper(config, "twitter", news_sources),
            "ftc_scraper": FTCScraper(config, "ftc", news_sources)
            # "yahoo_finance_scraper": yahooFinanceScraper(config, news_sources)
        } 

    def execute_all_scrapers(self):
        for news_id in self.all_scrapers:
            scraper = self.all_scrapers[news_id]
            scraper.setup_processes(scraper.scrape)
            print("Scraper {0} finished setup".format(news_id))
            scraper.kickoff_processes()


def main(config, news_sources):
    '''
    news_sources = {
        "yahoo_finance": yahoo_finance_urls_list,
        "twitter": twitter_urls_list,
        ....
    }
    '''
    controller = ScrapersController(config, news_sources)
    controller.execute_all_scrapers()

if __name__ == '__main__':
    conf = yaml.load(open("conf/prod/conf.yaml", 'r').read(), Loader=yaml.Loader)
    news_urls = yaml.load(open("news_urls/news_urls.yaml", 'r').read(), Loader=yaml.Loader)
    print(news_urls)
    news_sources = {news_id: news_urls[news_id] for news_id in news_urls}
    '''
    news_sources = {
        "yahoo_finance": yahoo_finance_urls_list,
        "twitter": twitter_urls_list,
        ....
    }
    '''
    main(conf, news_sources)

