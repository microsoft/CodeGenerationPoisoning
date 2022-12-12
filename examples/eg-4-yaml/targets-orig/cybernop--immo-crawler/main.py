import argparse
import logging
import pathlib
import time

import yaml

import immocrawler.crawler as cwlr
import immocrawler.notifier as ntfr
from immocrawler import googlemaps

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def main():
    arg_parser = argparse.ArgumentParser()

    arg_parser.add_argument('--data-dir', default='.', help='directory where to store data')
    arg_parser.add_argument('--config', required=True, help='config yaml file')
    arg_parser.add_argument('--notifier-url', required=True, help='url of the notifier service')
    arg_parser.add_argument('--verbose', action='store_true', help='more verbose output')

    args = arg_parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(level=logging.DEBUG)

    if not pathlib.Path(args.config).exists():
        logging.error(f'config file does not exist {args.config}')
        exit(-1)

    with open(args.config, 'r', encoding='utf-8') as yml_file:
        cfg = yaml.load(yml_file, Loader=yaml.SafeLoader)

    notifier = ntfr.Client(args.notifier_url)

    gmaps_config = cfg['google']
    gmaps_client = googlemaps.Client(gmaps_config['api_key'], gmaps_config['travel_locations'])

    crawler = cwlr.Crawler(cfg, args.data_dir, notifier, gmaps_client)
    while True:
        crawler.crawl()
        time.sleep(cfg['update_interval'])


if __name__ == '__main__':
    main()
