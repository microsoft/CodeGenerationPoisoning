import argparse
import datetime
import logging
import os
import threading
import time

from kafka import KafkaProducer

import opl.args
import opl.data
import opl.db
import opl.skelet

import psycopg2
import psycopg2.extras

import yaml


"""
You want to use this helper if you want to achieve this:

    * you have a messages generator like the in OPL `generators/`
    * you want to produce them to Kafka topic
    * you want to record when each message was sent

To create a script using this helper, you can create this:

    import json
    import socket

    import opl.generators.inventory_egress
    import opl.post_kafka_times


    def func_add_more_args(parser):
        # This function allows to add more parameters to the tool besides
        # what opl.post_kafka_times.post_kafka_times defines - maybe because
        # you will need it later in func_return_generator.
        parser.add_argument(
            "--count",
            default=100,
            type=int,
            help="How many messages to prepare",
        )
        parser.add_argument(
            "--n-packages",
            default=500,
            type=int,
            help="How many packages addresses should each host have",
        )
        parser.add_argument(
            "--msg-type",
            default="created",
            choices=["created"],
            help="Type of the message",
        )


    def func_return_generator(args):
        # This function is supposed to return the generator and is given
        # arguments passed on command line.
        # Generator is supposed to return touple with message ID and message
        # when iterating over it.
        return opl.generators.inventory_egress.EgressHostsGenerator(
            count=args.count,
            n_packages=args.n_packages,
            msg_type=args.msg_type,
        )


    def func_return_message_payload(args, message_id, message):
        # This function is supposed to return payload usable by Kafka
        # producer when sending - i.e. simple `string`. Helper will just
        # encode it into `bytes`. If your producer returns strings, you
        # might go with just `return message`.
        # This function have access to arguments from argparse
        # and message_id and message as provided by generator.
        return json.dumps(message)


    def func_return_message_key(args, message_id, message):
        # This function is supposed to return message key. Just
        # `return None` if your topic/app does not require it.
        return message_id


    def func_return_message_headers(args, message_id, message):
        # This function is supposed to return message headers if your
        # app/topic needs it. If you do not need it, just use `return []`.
        _event_type = args.msg_type
        _request_id = message["platform_metadata"]["request_id"]
        _producer = socket.gethostname()
        _insights_id = message["host"]["insights_id"]
        return [
            ("event_type", _event_type),
            ("request_id", _request_id),
            ("producer", _producer),
            ("insights_id", _insights_id),
        ]


    if __name__ == "__main__":
        # Here we just create config for the helper...
        config = {
            "func_add_more_args": func_add_more_args,
            "query_store_info_produced": "query_store_info_produced",
            "func_return_generator": func_return_generator,
            "func_return_message_payload": func_return_message_payload,
            "func_return_message_headers": func_return_message_headers,
            "func_return_message_key": func_return_message_key,
        }
        # ...and run the helper
        opl.post_kafka_times.post_kafka_times(config)
"""


class PostKafkaTimes:
    """
    This class is meant to encapsulate producing generated messages to Kafka
    and record ID of the message and timestamp of when each message was sent
    to sorage DB.
    """

    def __init__(self, args, status_data, config):
        """
        Connect to the storage DB, load SQL query templates, initiate
        a BatchProcessor, instantate messages generator and start
        a Kafka producer.
        """
        self.args = args
        self.status_data = status_data

        # Sanitize and include args into status data file
        args_copy = vars(args).copy()
        args_copy["tables_definition"] = args_copy["tables_definition"].name
        self.status_data.set("parameters.produce_messages", args_copy)

        storage_db_conf = {
            "host": args.storage_db_host,
            "port": args.storage_db_port,
            "database": args.storage_db_name,
            "user": args.storage_db_user,
            "password": args.storage_db_pass,
        }
        self.connection = psycopg2.connect(**storage_db_conf)
        self.kafka_hosts = [f"{args.kafka_host}:{args.kafka_port}"]
        self.kafka_group = args.kafka_group
        self.kafka_topic = args.kafka_topic
        self.kafka_timeout = args.kafka_timeout
        self.kafka_max_poll_records = 100
        self.queries_definition = yaml.load(
            args.tables_definition, Loader=yaml.SafeLoader
        )["queries"]
        self.show_processed_messages = args.show_processed_messages
        self.rate = args.rate

        self.config = config

        sql = self.queries_definition[self.config["query_store_info_produced"]]
        logging.info(f"Creating storage DB batch inserter with {sql}")
        data_lock = threading.Lock()
        self.save_here = opl.db.BatchProcessor(
            self.connection, sql, batch=100, lock=data_lock
        )

        logging.info("Creating generator")
        self.generator = self.config["func_return_generator"](args)

        logging.info(f"Creating producer to {args.kafka_host}:{args.kafka_port}")
        self.produce_here = KafkaProducer(
            bootstrap_servers=[args.kafka_host + ":" + str(args.kafka_port)],
        )

    def dt_now(self):
        """
        Return current time in UTC timezone with UTC timezone.
        """
        return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

    def work(self):
        """
        Produce messages generated by generator to Kafka using the producer.
        """

        def handle_send_success(*args, **kwargs):
            self.save_here.add((kwargs["message_id"], self.dt_now()))

        def wait_for_next_second(second=int(time.perf_counter())):
            while second == int(time.perf_counter()):
                time.sleep(0.01)
            return int(time.perf_counter())

        logging.info("Started message generation")
        self.status_data.set_now("parameters.produce.started_at")

        in_second = 0  # how many messages we have sent in this second
        this_second = wait_for_next_second()  # second relevant for in_second

        for message_id, message in self.generator:
            # Message payload
            send_params = {
                "value": self.config["func_return_message_payload"](
                    self.args, message_id, message
                ).encode("UTF-8"),
            }

            # Do we need message key?
            i = self.config["func_return_message_key"](self.args, message_id, message)
            if i is not None:
                send_params["key"] = i.encode("UTF-8")

            # Do we need message headers?
            i = self.config["func_return_message_headers"](
                self.args, message_id, message
            )
            if i is not []:
                send_params["headers"] = [(i1, i2.encode("UTF-8")) for i1, i2 in i]

            future = self.produce_here.send(self.kafka_topic, **send_params)
            future.add_callback(handle_send_success, message_id=message_id)

            if int(time.perf_counter()) == this_second:
                in_second += 1
                if in_second == self.rate:
                    logging.debug(f"In second {this_second} sent {in_second} messages")
                    this_second = wait_for_next_second(this_second)
                    in_second = 0
            else:
                if self.rate != 0 and self.rate != in_second:
                    logging.warning(
                        f"In second {this_second} sent {in_second} messages (but wanted to send {self.rate})"
                    )
                    this_second = int(time.perf_counter())
                    in_second = 0

        self.status_data.set_now("parameters.produce.ended_at")
        logging.info("Finished message generation, producing and storing")

        self.produce_here.flush()

        self.save_here.commit()


def post_kafka_times(config):
    """
    This is the main helper function you should use in your code.
    It handles arguments, opening status data file and running
    the actual workload.
    """
    parser = argparse.ArgumentParser(
        description="Given a Kafka messages generator produce messages and put timestamps into DB",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--kafka-topic",
        default=os.getenv("KAFKA_TOPIC", "platform.upload.qpc"),
        help="Produce to this topic (also use env variable KAFKA_TOPIC)",
    )
    parser.add_argument(
        "--show-processed-messages",
        action="store_true",
        help="Show messages we are producing",
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=0,
        help="How many messages per second should we produce (0 for no limit)",
    )
    opl.args.add_storage_db_opts(parser)
    opl.args.add_kafka_opts(parser)
    opl.args.add_tables_def_opts(parser)

    # PostKafkaTimes needs this config keys in config dict
    assert "query_store_info_produced" in config
    assert "func_return_generator" in config
    assert "func_add_more_args" in config
    assert "func_return_message_payload" in config
    assert "func_return_message_key" in config
    assert "func_return_message_headers" in config

    # Add more args
    config["func_add_more_args"](parser)

    with opl.skelet.test_setup(parser) as (args, status_data):
        post_kafka_times_object = PostKafkaTimes(
            args,
            status_data,
            config,
        )
        post_kafka_times_object.work()
