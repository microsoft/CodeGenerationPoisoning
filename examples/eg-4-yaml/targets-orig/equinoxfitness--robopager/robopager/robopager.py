#!/usr/bin/env python
from datetime import datetime
import yaml
import json
import requests
import argparse
import schedule
import time
import threading
import redis
import sys
from datacoco_core.logger import Logger
from robopager.config_wrapper import ConfigWrapper
from robopager.check_type.daily_email_check import CheckEmails
from robopager.check_type.intraday_latency_check import CheckWF


# -------------------------------------------------------------

log = Logger()
KEY_PREFIX = "rp"

# -------------------------------------------------------------

# common functions


def parse_checklist(check_file):
    """
    reads yaml file into python object
    :param check_file:
    :return: checklist
    """
    with open(check_file, "r") as checklist_yaml:
        check_list = yaml.load(checklist_yaml)
    return check_list


def json_serial(obj):
    """
    JSON serializer for objects not serializable by default json code"
    :param obj:
    :return:
    """
    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")


def time_2_datetime(time):
    """
    turns time into datetime, basd on today's date
    :param time:
    :return:
    """
    today_time = datetime.combine(
        datetime.today(), datetime.strptime(time, "%H:%M").time()
    )
    return today_time


def str_to_bool(en):
    if en == "True":
        return True
    elif en == "False":
        return False
    else:
        raise ValueError("please enter correct boolean values to enable Redis")


# ----------------------------------------------------
# core robopager


class RedisInteraction:
    """
    Enable Redis to check and log
    """

    def __init__(self, redis_server, redis_db):
        # connect to redis
        self.rconn = redis.StrictRedis(
            host=redis_server, port=6379, db=redis_db
        )

    def check_last_run(self, incident, override=False, offset_sec=0):

        """
        check the incident key of last run
        :param incident:
        :param override:
        :param offset_sec:
        :return:
        """

        # we'll sleep by the offset seconds, assuming
        # we have a cluster of robopager servers for redundancy prevents
        # multiple robopager services from dispatching alerts at the same time
        log.l("offset: sleeping for %ss" % offset_sec)
        time.sleep(float(offset_sec))

        # first check to make sure it hasn't already been opened,
        # otherwise notifications will be annoying
        last_incident = None

        try:
            last_incident = self.rconn.hget(
                KEY_PREFIX + "." + incident, "incident_dt"
            )
            log.l("last incident time: " + str(last_incident))
        except Exception:
            pass
            log.l("issue connecting to redis")

        if last_incident is not None and not override:
            log.l("already a triggered incident")
            return

    def log_to_redis(self, key_name, detail):
        """
        log the new incident or check result to Redis
        :param key_name:
        :param detail:
        :return:
        """

        try:
            self.rconn.hmset(
                KEY_PREFIX + "." + key_name,
                {"result": detail, "status_dt": str(datetime.now())},
            )
        except Exception:
            pass
            log.l("issue logging to redis")


class NonRedisInteraction:
    """
    Disable to check and log
    """

    def check_last_run(self, incident, override=False, offset_sec=0):
        log.l("Redis disabled, no need to check last run")

    def log_to_redis(self, key_name, detail):
        log.l("Redis disabled, no need to log to Redis")


class PDInteraction:
    """
    wrapper for pager duty
    """

    def __init__(self, sub_domain, api_access_key):

        self.sub_domain = sub_domain
        self.headers = {
            "Authorization": "Token token={0}".format(api_access_key),
            "Content-type": "application/json",
        }

    def trigger_incident(
        self,
        pd_service,
        pd_description,
        error_detail,
        check="eqx",
        override=False,
        offset_sec=0,
    ):
        """
        triggers a new pager duty incident
        :param pd_service:
        :param pd_description:
        :param error_detail:
        :param check:
        :param override:
        :param offset_sec:
        :return:
        """
        incident = check + "-" + str(datetime.now().strftime("%Y%m%d-%H"))

        # check the incident key of last run
        ri.check_last_run(incident, override, offset_sec)

        # if nothing is found we trigger the incident
        payload = json.dumps(
            {
                "service_key": pd_service,
                "incident_key": incident,
                "event_type": "trigger",
                "description": pd_description,
                "client": "robopager",
                "details": error_detail,
            }
        )
        p = "https://events.pagerduty.com/generic/2010-04-15/create_event.json"
        r = requests.post(p, headers=self.headers, data=payload,)

        if r.status_code != 200:
            log.l("Error triggering pager duty")
            sys.exit()
        else:
            # log the newly-triggered incident to Redis
            ri.log_to_redis(incident, payload)

        log.l(r.status_code)
        log.l(r.reason)
        log.l(r.text)
        return r.status_code


class JobRunner:
    """
    wrapper for schedule module
    """

    def __init__(self):
        """
        """

    def schedule_job(self, job, params, schedule_time, interval):
        """
        adds job to schedule
        :param job:
        :param params:
        :param schedule_time:
        :param interval: will run job at this interval in seconds.
        0 will be a check once daily
        """
        kw = {"func": job, "param": params}
        if interval == 0:
            schedule.every().day.at(schedule_time).do(self.run_threaded, **kw)
        else:
            # note scheduler does not have a start time concept
            # so this will need to be handled in the job
            schedule.every(interval).seconds.do(self.run_threaded, **kw)

    @staticmethod
    def run_threaded(func, param):
        """
        runs job within thread
        :param func:
        :param param:
        """
        # job_thread = threading.Thread(target=func, args=param)
        job_thread = threading.Thread(target=func, kwargs=param)
        job_thread.start()

    @staticmethod
    def dispatcher():
        """
        starts scheduler
        """
        last_hour = datetime.now().strftime("%H")
        print(last_hour)
        while True:
            schedule.run_pending()
            time.sleep(1)
            this_hour = datetime.now().strftime("%H")
            if this_hour != last_hour:
                log.l("heartbeat --> still here homey!")
                last_hour = this_hour

    @staticmethod
    def get_jobs():
        """
        returns list of jobs scheduled
        """
        return schedule.jobs


def run_test(**kwargs):
    """
    a wrapper for running basic tests
    :param kwargs:
    :return:
    """
    failure_count = 0
    # extract shared variables
    pd_check = kwargs.get("check")
    check_type = kwargs.get("type", "daily_email")
    pd_service = kwargs.get("pd_service")
    pd_description = kwargs.get("pd_description")
    check_time = kwargs.get("check_time")

    # now run the appropriate check based on check type
    if check_type == "email":
        subjects = kwargs.get("subjects")
        senders = kwargs.get("senders")
        delivery_time = kwargs.get("delivery_time")
        e = CheckEmails(
            username, password, subjects, senders, timezone, delivery_time
        )
        e.get_emails()
        failure_count, results = e.check_missing_emails()
        e.close_session()

    elif check_type == "batchy":
        # since schedule module doesn't have a start time concept,
        # we'll implement here
        if datetime.now() > time_2_datetime(check_time):
            latency_min = kwargs.get("latency_min")
            pd_description = kwargs.get("pd_description")
            wf_name = kwargs.get("wf_name")
            wf = CheckWF(wf_name, batchy_server, batchy_port)
            failure_count, results = wf.check_batchy_wf(latency_min)
        else:
            return

    else:
        log.l("Invalid test type, please check yaml")
        return

    # log check result to redis
    try:
        ri.log_to_redis(pd_check, json.dumps(results, default=json_serial))
    except Exception:
        log.l("Error logging roboapger check result to Redis")

    # logging and pd alerts
    if check_type == "email" or failure_count != 0:
        log.l(
            "failure count: "
            + str(failure_count)
            + "\nresults:"
            + str(results)
        )

    if failure_count > 0:
        log.l("!!!!uh oh bro!!!!")
        PDInteraction(sub_domain, api_access_key).trigger_incident(
            pd_service,
            pd_description,
            json.dumps(
                {
                    "results": results,
                    "sender": str(senders),
                    "check_time": check_time,
                    "delivery_time": delivery_time,
                },
                default=json_serial,
                indent=4,
            ),
            pd_check,
        )
    else:
        return


if __name__ == "__main__":
    # parse args
    log.l("starting")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--check",
        help="enter a check referencing the yaml",
        default="cron",
    )
    parser.add_argument(
        "-y",
        "--checklist",
        help="enter a checklist file, default is checklist.yaml",
        default="cfg/checklist.yaml",
    )
    # add config parameter
    parser = ConfigWrapper.extend_parser(parser)

    args = parser.parse_args()
    check = args.check
    checklist = args.checklist

    conf = ConfigWrapper.process_config(args)

    # heartbeat alert
    heartbeat = conf["robopager"]["heartbeat_service"]

    # pd vars
    sub_domain = conf["pager_duty"]["subdomain"]
    api_access_key = conf["pager_duty"]["api_access_key"]

    # gmail vars
    username = conf["google_apps"]["email"]
    password = conf["google_apps"]["password"]

    # function type
    function_type = conf["function_type"]["type"]
    function_list = function_type.split(",")

    # batchy vars
    batchy_server = conf["batchy"]["server"]
    batchy_port = conf["batchy"]["port"]

    # timezone
    timezone = conf["timezone"]["timezone"]

    # enable redis
    enable_redis = conf["enable_redis"]["enable"]

    # enable & connect to redis
    print("\nRedis Enable Status: {}".format(enable_redis))

    if str_to_bool(enable_redis):
        redis_server = conf["redis"]["server"]
        redis_db = conf["redis"]["db"]
        # enable redis
        ri = RedisInteraction(redis_server, redis_db)
        log.l("Redis enabled")
    else:
        ri = NonRedisInteraction()
        log.l("Redis disabled")

    log.l("\n\nCHECKLIST: {}".format(checklist))

    # get list of tests and metadata
    check_list = parse_checklist(checklist)

    # check to see if we are running a specific check
    # via external cron or starting as a service
    if check != "cron":
        log.l("single job mode")
        if check not in check_list:
            log.l("invalid test, please review checklist.yaml")
            sys.exit()
        else:
            kw = check_list[check]
            kw["check"] = check
            run_test(**kw)
            sys.exit()
    else:
        log.l("service mode")

    # create job runner instance
    j = JobRunner()
    log.l("scheduled job type:" + function_type)

    # loop
    for c in check_list:
        # only schedule jobs of enabled function types
        check_type = check_list[c].get("type")
        if check_type not in function_list:
            continue
        # only schedule jobs with valid check_time
        check_time = check_list[c].get("check_time")
        if len(str(check_time)) != 5:
            continue
        poll_interval = check_list[c].get("poll_sec", 0)
        check_params = check_list[c]
        check_params["check"] = c
        j.schedule_job(run_test, check_params, check_time, poll_interval)

    jobs = sorted(j.get_jobs())

    startup_msg = (
        str(len(jobs))
        + " of "
        + str(len(check_list))
        + " have been scheduled:\n-"
        + "\n- ".join(str(v) for v in jobs)
    )
    startup_status = "OK" if len(jobs) == len(check_list) else "FAILURE"

    log.l(startup_msg)
    PDInteraction(sub_domain, api_access_key).trigger_incident(
        heartbeat,
        startup_status + ": Robopager Startup",
        startup_msg,
        override=True,
    )
    j.dispatcher()
