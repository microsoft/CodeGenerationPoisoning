import click

import logging
import markus
import pymysql
import sys
import yaml

from DBUtils.PooledDB import PooledDB
from plutus.budget_manager.verify import (
    verify_project_yaml,
    verify_parent_yaml,
    verify_labels_yaml,
    # verify_default_yaml
)

from google.cloud.billing.budgets_v1.services.budget_service import BudgetServiceClient
from google.cloud import resource_manager
from google.cloud import storage

from plutus.lib.constants import (
    APP,
    PLUTUS_CONFIG_TYPE_PROJECT,
    PLUTUS_CONFIG_TYPE_PARENT,
    PLUTUS_CONFIG_TYPE_LABEL,
    # PLUTUS_CONFIG_TYPE_DEFAULT
)

from plutus.lib.mysql import upsert_budget, count_budgets
from plutus.lib.gcp_helper import GcpHelper
from plutus.budget_manager.project_budget import ProjectBudget

log = logging.getLogger(APP)
metrics = markus.get_metrics(APP)


@click.command()
@click.option("--gcs-bucket", envvar="GCS_BUCKET", default=None)  # Without the gs://
@click.option("--gcs-file-path", envvar="GCS_FILE_PATH", default=None)
@click.option("--billing-account-id", envvar="BILLING_ACCOUNT_ID", default=None)
@click.option(
    "--default-pubsub-topic",
    default="projects/moz-fx-data-dataops/topics/plutus-budget-notifications",
)
@click.option("--mysql-host", envvar="MYSQL_HOST", default="localhost")
@click.option("--mysql-port", envvar="MYSQL_PORT", default="3306")
@click.option("--mysql-user", envvar="MYSQL_USER", default="root")
@click.option("--mysql-pass", envvar="MYSQL_PASS", default="secret")
@click.option("--mysql-db", envvar="MYSQL_DB", default="plutus")
@click.option(
    "--statsd-host",
    envvar="STATSD_HOST",
    default="prod-statsd-telegraf.influx.svc.cluster.local",
)
# Used for local testing without container, and without using gcs file
# Local mode loads config file from filesystem
@click.option("--local-mode", is_flag=True, default=False)
@click.option("--dry-run", is_flag=True, default=False)
def main(
    gcs_bucket,
    gcs_file_path,
    billing_account_id,
    default_pubsub_topic,
    mysql_host,
    mysql_port,
    mysql_user,
    mysql_pass,
    mysql_db,
    statsd_host,
    local_mode,
    dry_run,
):
    logformat = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=logformat)

    # TODO - troubleshoot metric uploading with local container, and test it works on GKE as well.
    # Remove this line to see WARNINGs
    logging.getLogger("datadog.dogstatsd").setLevel(logging.ERROR)

    # Load config.yaml file
    if local_mode:
        if gcs_bucket is not None or gcs_file_path is not None:
            log.warn(
                f"You are using local mode, and gcs_bucket ({gcs_bucket}) and gcs_file_path ({gcs_file_path}) will not be used."
            )

        with open("/app/config.yaml", "r") as f:
            budget_dict = yaml.load(f, Loader=yaml.SafeLoader)

        setup_metrics("localhost")
    else:
        # Load yaml configuration file from GCS
        gcs_client = storage.Client()
        bucket = gcs_client.bucket(gcs_bucket)
        blob = bucket.blob(gcs_file_path)
        yaml_string = blob.download_as_string()
        budget_dict = yaml.load(yaml_string, Loader=yaml.SafeLoader)
        # Setup metrics with configured statsd host
        setup_metrics(statsd_host)

    # Setup gcp helper
    billing_client = BudgetServiceClient()
    resource_manager_client = resource_manager.Client()
    gcp = GcpHelper(billing_client, resource_manager_client)

    # Setup mysql connection pool
    pool = PooledDB(
        creator=pymysql,
        host=mysql_host,
        user=mysql_user,
        password=mysql_pass,
        database=mysql_db,
        autocommit=True,
        blocking=True,
        maxconnections=5,
    )
    mysql_conn = pool.connection()

    # Iterate over all configured project budgets
    for project_dict in budget_dict["projects"]:
        config_type = PLUTUS_CONFIG_TYPE_PROJECT

        if verify_project_yaml(project_dict):
            project = ProjectBudget(
                project_dict, config_type, billing_account_id, default_pubsub_topic
            )

            if dry_run:
                log.info(
                    f"Dry run: would have ran get_and_update_or_create_budget for project: {project.project_id}"
                )
            else:
                log.info(f"Processing project: {project.project_id}...")
                budget = gcp.get_and_update_or_create_budget(project)

                if budget is not None:
                    with mysql_conn.cursor() as mysql_cursor:
                        upsert_budget(
                            mysql_cursor,
                            budget,
                            project.project_id,
                            config_type,
                            project.alert_emails,
                            project.alert_slack_channel_id,
                        )

        else:
            log.error("Project config verification failed.")
            metrics.incr(
                "error_count",
                tags=[
                    "type:misconfig",
                    f"project_id:{project.project_id}",
                    f"config_type:{config_type}",
                ],
            )
            sys.exit(1)

    # Iterate over all configured parent folder id budgets
    for parent_dict in budget_dict["parent_folders"]:
        parent_id = parent_dict["parent_folder_id"]
        config_type = PLUTUS_CONFIG_TYPE_PARENT

        if verify_parent_yaml(parent_dict):
            parent_filter = {"parent.id": parent_id}

            for p in resource_manager_client.list_projects(parent_filter):
                # Overwrite 'project_id' key for each project under parent folder
                parent_dict["project_id"] = p.project_id
                project = ProjectBudget(
                    parent_dict, config_type, billing_account_id, default_pubsub_topic
                )

                existing_project_budget_id = gcp.has_existing_project_budget(project)

                if existing_project_budget_id is None:
                    # No project one off budget configured for this projectid
                    if dry_run:
                        log.info(
                            f"Dry run (parent folders): would have ran get_and_update_or_create_budget for project: {project.project_id}"
                        )
                    else:
                        log.info(
                            f"Processing parent_id: {parent_id}, project: {project.project_id}..."
                        )
                        budget = gcp.get_and_update_or_create_budget(project)

                        if budget is not None:
                            with mysql_conn.cursor() as mysql_cursor:
                                upsert_budget(
                                    mysql_cursor,
                                    budget,
                                    project.project_id,
                                    config_type,
                                    project.alert_emails,
                                    project.alert_slack_channel_id,
                                )
                else:
                    log.info(
                        f"Skipping creating parent project budget for \
                              {p.project_id} since existing plutus project budget found."
                    )

                    existing_parent_budget_id = gcp.has_existing_parent_budget(
                        parent_id, project
                    )
                    if existing_parent_budget_id is not None:
                        # We have a configured plutus project budget. Delete parent budget
                        gcp.delete_budget(existing_parent_budget_id)

        else:
            log.error("Parent folder config verification failed.")
            metrics.incr(
                "error_count",
                tags=[
                    "type:misconfig",
                    f"parent_id:{parent_id}",
                    f"config_type:{config_type}",
                ],
            )
            sys.exit(1)

    # Iterate over all configured label budgets
    for label_dict in budget_dict["labels"]:
        config_type = PLUTUS_CONFIG_TYPE_LABEL

        if verify_labels_yaml(label_dict):

            labels_filter = {}
            for row in label_dict["label_list"]:
                for key in row:
                    labels_filter[f"labels.{key}"] = row[key]

            # Find projects that match the labels
            for p in resource_manager_client.list_projects(filter_params=labels_filter):
                # Overwrite the 'project_id' key for each project that matches labels
                label_dict["project_id"] = p.project_id
                project = ProjectBudget(
                    label_dict, config_type, billing_account_id, default_pubsub_topic
                )

                existing_project_budget_id = gcp.has_existing_project_budget(project)

                if existing_project_budget_id is None:
                    # No project one off budget configured for this projectid
                    if dry_run:
                        log.info(
                            f"Dry run (labels): would have ran get_and_update_or_create_budget for project: {project.project_id}"
                        )
                    else:
                        log.info(
                            f"Processing labels: {labels_filter}, project: {project.project_id}..."
                        )
                        budget = gcp.get_and_update_or_create_budget(project)

                        if budget is not None:
                            with mysql_conn.cursor() as mysql_cursor:
                                upsert_budget(
                                    mysql_cursor,
                                    budget,
                                    project.project_id,
                                    config_type,
                                    project.alert_emails,
                                    project.alert_slack_channel_id,
                                )
                else:
                    log.info(
                        f"Skipping creating label project budget for \
                              {p.project_id} since existing plutus project budget found."
                    )

                    existing_labels_budget_id = gcp.has_existing_labels_budget(project)
                    if existing_labels_budget_id is not None:
                        # We have a configured plutus project budget. Delete labels budget
                        gcp.delete_budget(existing_labels_budget_id)

        else:
            log.error("Labels config verification failed.")
            metrics.incr(
                "error_count", tags=["type:misconfig", f"config_type:{config_type}"]
            )
            sys.exit(1)

    # Default logic removed for now because it will create hundreds of budgets
    # And we need to decide good thresholds for this
    """
    default_dict = budget_dict['default']
    config_type = PLUTUS_CONFIG_TYPE_DEFAULT

    if verify_default_yaml(default_dict):
    ## Query for all projects. If no budget exists for project, add a default budget
        for p in resource_manager_client.list_projects():
            project_id = p.project_id
            project_number = gcp.get_project_number(project_id)
            if project_number is not None:
                budgets = gcp.get_budgets_by_project(project, project_number)
                if len(budgets) == 0:
                    # No budget exists for this project, so we create one
                    default_dict['project_id'] = project_id

                    # TODO - add and test, also add dry_run logic
                    # project = ProjectBudget(default_dict, config_type,
                    #           billing_account_id, default_pubsub_topic)
                    log.info(f"Creating default budget for plutus-default-{project_id}")
                    # budget = gcp.create_budget(project)
                    # metrics.incr("default_budget_created_count", tags=[])

                    # if budget is not None:
                    #    with mysql_conn.cursor() as mysql_cursor:
                    #        upsert_budget(mysql_cursor, budget, project.project_id,
                    #                      config_type, project.alert_emails)

                    # TODO - delete plutus-default budget if > 1 budget
                elif len(budgets) > 1:
                    # TODO - if one of the budgets is a plutus-default, delete via API and in Mysql
                    pass

    else:
        log.error("Default config verification failed.")
        metrics.incr("error_count", tags=["type:misconfig", f"config_type:{config_type}"])
        sys.exit(1)
    """

    # Count budgets for gauge metric
    with mysql_conn.cursor() as mysql_cursor:
        count_budgets(mysql_cursor)

    log.info("Plutus run complete.")


def setup_metrics(statsd_host):
    markus.configure(
        backends=[
            {
                # Log metrics to statd to telegraf to influx.
                # We use datadog backend class to get support for tags and histograms
                # https://github.com/willkg/markus/blob/master/markus/backends/statsd.py#L58-L64
                "class": "markus.backends.datadog.DatadogMetrics",
                "options": {
                    "statsd_host": statsd_host,
                    "statsd_port": 8125,
                    "statsd_namespace": "influx",
                },
            }
        ]
    )


if __name__ == "__main__":
    main()
