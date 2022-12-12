import argparse
import contextlib
import datetime
import json
import logging
import os

from kafka import KafkaConsumer

import opl.args
import opl.data
import opl.db
import opl.skelet

import psycopg2
import psycopg2.extras

import yaml


class GetKafkaTimes():

    def __init__(self, args, status_data, custom_methods):
        storage_db_conf = {
            'host': args.storage_db_host,
            'port': args.storage_db_port,
            'database': args.storage_db_name,
            'user': args.storage_db_user,
            'password': args.storage_db_pass,
        }
        self.connection = psycopg2.connect(**storage_db_conf)
        self.status_data = status_data
        self.kafka_hosts = [f"{args.kafka_host}:{args.kafka_port}"]
        self.kafka_group = args.kafka_group
        self.kafka_topic = args.kafka_topic
        self.kafka_timeout = args.kafka_timeout
        self.kafka_max_poll_records = 100
        self.queries_definition = yaml.load(args.tables_definition,
                                            Loader=yaml.SafeLoader)['queries']
        self.custom_methods = custom_methods

        # Number of items we are still missing set by "remaining_count" query
        self.remaining_count = None
        self.update_remaining_count()

        # Store into DB in batches this big
        self.batches_size = 500
        # Maximum seconds before we give up waiting for useful message
        self.max_quiet_period = args.max_quiet_period

        # Number of items we store
        self.stored_counter = 0
        # Buffer of messages we received and not stored to DB yet
        self.waiting_items = []

        # Which messages to show during processing
        self.show_processed_messages = args.show_processed_messages
        self.show_dropped_messages = args.show_dropped_messages

    def update_remaining_count(self):
        """
        Number of items that are still missing in the DB
        """
        cursor = self.connection.cursor()
        sql = self.queries_definition[self.custom_methods['query_remaining_count']()]
        cursor.execute(sql)
        self.remaining_count = int(cursor.fetchone()[0])
        cursor.close()
        logging.debug(f"Remains to get {self.remaining_count} items")

    def dt_now(self):
        return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

    def kafka_ts2dt(self, timestamp):
        return datetime.datetime.utcfromtimestamp(float(timestamp) / 1000).replace(tzinfo=datetime.timezone.utc)

    def create_consumer(self):
        # Store Kafka config to status data
        self.status_data.set('parameters.kafka.bootstrap', self.kafka_hosts[0])
        self.status_data.set('parameters.kafka.group', self.kafka_group)
        self.status_data.set('parameters.kafka.topic', self.kafka_topic)
        self.status_data.set('parameters.kafka.timeout', self.kafka_timeout)

        # Create Kafka consumer
        consumer = KafkaConsumer(
            self.kafka_topic,
            bootstrap_servers=self.kafka_hosts,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id=self.kafka_group,
            max_poll_records=self.kafka_max_poll_records,
            session_timeout_ms=50000,
            heartbeat_interval_ms=10000,
            consumer_timeout_ms=self.kafka_timeout)
        logging.debug(f"Created Kafka consumer for {self.kafka_hosts} for {self.kafka_topic} topic in group {self.kafka_group} with {self.kafka_timeout} ms timeout")
        return consumer

    def store_now(self):
        """
        Store waiting items

        Query is supposed to only update existing records, not add new ones.
        """
        cursor = self.connection.cursor()
        sql = self.queries_definition[self.custom_methods['query_store_info']()]
        psycopg2.extras.execute_values(
            cursor, sql, self.waiting_items, template=None, page_size=self.batches_size)
        try:
            updated = cursor.fetchall()
        except psycopg2.ProgrammingError as e:
            logging.warning(f"Hit psycopg2.ProgrammingError when fetching number of updated items: {e}")
            updated = []
        self.connection.commit()
        cursor.close()

        self.waiting_items.clear()

        if updated is None:
            updated = 0
        else:
            updated = len(updated)
            self.stored_counter += updated
            self.last_stored_at = self.dt_now()
            self.update_remaining_count()
        logging.debug(f"Updated {updated} items")

        return updated

    def store_item(self, item):
        self.waiting_items.append(item)

        if len(self.waiting_items) >= self.batches_size or \
           len(self.waiting_items) >= self.remaining_count:
            self.store_now()

    def process_messages(self):
        # Quit if we have all the data in the DB
        if self.remaining_count == 0:
            logging.info("All in, nothing to collect")
            return 0

        # Last time when we inserted something into DB
        self.last_stored_at = self.dt_now()

        with contextlib.closing(self.create_consumer()) as consumer:
            while True:
                msg_pack = consumer.poll(timeout_ms=5000, max_records=self.kafka_max_poll_records, update_offsets=True)
                for topic, messages in msg_pack.items():
                    for message in messages:
                        key = message.key.decode('utf-8') if message.key is not None else None
                        value = json.loads(message.value.decode('utf-8'))
                        logging.debug(f"Received {message.timestamp} {topic.topic} {topic.partition} {message.offset} {str(value)[:100]}...")

                        if self.custom_methods['message_validation'](value):
                            if self.show_processed_messages:
                                print(f"Processing {message.timestamp} {topic.topic} {topic.partition} {message.offset} {str(value)[:100]}...")

                            # Construct item to be saved
                            new_value = self.custom_methods['process_message'](
                                self.kafka_ts2dt(message.timestamp), key, value)
                            self.store_item(new_value)
                        else:
                            if self.show_dropped_messages:
                                print(f"Dropping {message.timestamp} {topic.topic} {topic.partition} {message.offset} {str(value)[:100]}...")

                # Quit if we have all the data in the DB
                if self.remaining_count == 0:
                    logging.info(f"All {self.stored_counter} messages received")
                    break

                # Quit if we have not got enough useful data for too long
                quiet_period = self.dt_now() - self.last_stored_at
                if quiet_period > self.max_quiet_period:
                    updated = self.store_now()
                    if updated > 0:
                        logging.warning(f"It was quiet for {quiet_period}, but we have saved {updated} items so lets wait some more.")
                        continue
                    else:
                        logging.warning(f"It was quiet here for {quiet_period}. Skipping remaining items as they are not coming.")
                        break

        self.store_now()

        return self.stored_counter

    def get_biggest(self):
        cursor = self.connection.cursor()
        sql = self.queries_definition[self.custom_methods['query_get_biggest']()]
        cursor.execute(sql)
        last = cursor.fetchone()[0]
        cursor.close()
        return last

    def print_stats(self):
        if self.custom_methods['start_end_col_table_name']() is not None:
            start_column, end_column, table = \
                self.custom_methods['start_end_col_table_name']()

            durations = opl.db.get_timedelta_between_columns(
                self.connection, [end_column, start_column], table=table)
            end_ats = opl.db.get_timestamps(
                self.connection, end_column, table=table)
            end_rps = opl.data.get_rps(end_ats)

            print(f"Start -> end duration stats: {opl.data.data_stats(durations)}")
            opl.data.visualize_hist(durations)
            self.status_data.set(
                f"{self.custom_methods['stats_sd_name']()}.duration_stats",
                opl.data.data_stats(durations))

            print(f"End RPS: {opl.data.data_stats(end_rps)}")
            opl.data.visualize_hist(end_rps)
            self.status_data.set(
                f"{self.custom_methods['stats_sd_name']()}.rps_stats",
                opl.data.data_stats(end_rps))

    def work(self):
        count = self.process_messages()
        self.status_data.set(self.custom_methods['count_sd_name'](), count)
        last = self.get_biggest()
        self.status_data.set(self.custom_methods['biggest_sd_name'](), last)
        if 'start_sd_name' in self.custom_methods:
            start = self.status_data.get_date(self.custom_methods['start_sd_name']())
            if start is not None and last is not None:
                duration = (last - start).total_seconds()
                self.status_data.set('results.duration', duration)
                simple_rps = count / duration
                self.status_data.set('results.simple_rps', simple_rps)
        self.print_stats()


def get_kafka_times(custom_methods):
    parser = argparse.ArgumentParser(
        description='Listen for Kafka messages and put timestamps into DB',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--kafka-topic',
                        default=os.getenv('KAFKA_TOPIC', 'platform.receptor-controller.responses'),
                        help='Consume from this topic (also use env variable KAFKA_TOPIC)')
    parser.add_argument('--max-quiet-period', type=int,
                        default=int(os.getenv('MAX_QUIET_PERIOD', 300)),
                        help='Stop waiting for useful messages if none has appeared in this amount of seconds (also use env variable MAX_QUIET_PERIOD)')
    parser.add_argument('--show-dropped-messages', action='store_true',
                        help='Show messages which did not passed validation filter')
    parser.add_argument('--show-processed-messages', action='store_true',
                        help='Show messages which passed validation filter and will be processed')
    opl.args.add_storage_db_opts(parser)
    opl.args.add_kafka_opts(parser)
    opl.args.add_tables_def_opts(parser)

    # GetKafkaTimes needs these methods in the custom_methods dict
    assert 'message_validation' in custom_methods
    assert 'process_message' in custom_methods
    assert 'count_sd_name' in custom_methods
    assert 'biggest_sd_name' in custom_methods
    assert 'start_end_col_table_name' in custom_methods

    # These have its defaults
    if 'query_remaining_count' not in custom_methods:
        custom_methods['query_remaining_count'] = lambda: 'remaining_count'
    if 'query_store_info' not in custom_methods:
        custom_methods['query_store_info'] = lambda: 'store_info'
    if 'query_get_biggest' not in custom_methods:
        custom_methods['query_get_biggest'] = lambda: 'get_biggest'

    with opl.skelet.test_setup(parser) as (args, status_data):
        args.max_quiet_period = \
            datetime.timedelta(seconds=args.max_quiet_period)

        get_kafka_times_object = GetKafkaTimes(
            args, status_data, custom_methods)
        get_kafka_times_object.work()
