import click
import json
import multiprocessing
import os
import yaml

from cdislogging import get_logger

from gen3utils.deployment_changes.generate_comment import (
    comment_deployment_changes_on_pr,
)
from gen3utils.manifest.manifest_validator import validate_manifest as val_manifest
from gen3utils.etl.etl_validator import validate_mapping
from gen3utils.gitops.gitops_validator import val_gitops
from gen3utils.utils import comment_on_pr


logger = get_logger("gen3utils", log_level="info")


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


@click.group()
def main():
    """Utils for Gen3 cdis-manifest management."""


@main.command()
@click.argument("etl_mapping_file", type=str, nargs=1, required=True)
@click.argument("manifest_file", type=str, nargs=1, required=True)
@click.argument("portal_config_file", type=str, nargs=1, required=True)
@click.argument("repository", type=str, nargs=1, required=False)
@click.argument("pull_request_number", type=int, nargs=1, required=False)
def validate_portal_config(
    etl_mapping_file, manifest_file, portal_config_file, repository, pull_request_number
):
    """Validate a PORTAL_CONFIG_FILE against the dictionary specified in the MANIFEST_FILE
    and an ETL_MAPPING_FILE"""

    logger.info("Validating portal config file {}".format(portal_config_file))
    dictionary_url = None
    with open(manifest_file, "r") as f1:
        manifest = json.loads(f1.read())
        dictionary_url = manifest.get("global", {}).get("dictionary_url")
        hostname = manifest.get("global", {}).get("hostname")
        if dictionary_url is None:
            logger.error("No dictionary URL in manifest {}".format(manifest_file))
            return

    recorded_errors, ok = val_gitops(
        dictionary_url, etl_mapping_file, portal_config_file
    )

    if recorded_errors:
        for err in recorded_errors:
            logger.error("  - {}".format(err))
        if repository and pull_request_number:
            if not "GITHUB_TOKEN" in os.environ:
                logger.warning("Missing GITHUB_TOKEN: not commenting on pull request.")
            else:
                message_header = (
                    "{}\n :x: etlMapping.yaml - gitops.json mismatch".format(hostname)
                )
                comment_on_pr(
                    repository,
                    pull_request_number,
                    message_header,
                    recorded_errors,
                )

    if not ok:
        raise AssertionError(
            "Portal configuration mapping validation failed. See errors in previous logs."
        )
    else:
        logger.info("  OK!")


@main.command()
@click.argument("manifest_files", type=str, nargs=-1, required=True)
def validate_manifest(manifest_files):
    """Validate one or more MANIFEST_FILES against a REQUIREMENTS_FILE."""

    requirements_file = os.path.join(CURRENT_DIR, "manifest", "validation_config.yaml")
    with open(requirements_file, "r") as f:
        requirements = yaml.safe_load(f.read())

    failed_validation = False
    for f_name in manifest_files:
        logger.info("Validating manifest {}".format(f_name))
        try:
            with open(f_name, "r") as f:
                cdis_manifest = json.loads(f.read())
            val_manifest(cdis_manifest, requirements)
        except AssertionError as e:
            logger.error("{}: {}".format(type(e).__name__, e))
            failed_validation = True
    if failed_validation:
        raise AssertionError("manifest validation failed. See errors in previous logs.")


@main.command()
@click.argument("etl_mapping_file", type=str, nargs=1, required=True)
@click.argument("manifest_file", type=str, nargs=1, required=True)
def validate_etl_mapping(etl_mapping_file, manifest_file):
    """Validate an ETL_MAPPING_FILE against the dictionary specified in the MANIFEST_FILE."""

    logger.info("Validating ETL mapping {}".format(etl_mapping_file))
    with open(manifest_file, "r") as f1:
        manifest = json.loads(f1.read())
        dictionary_url = manifest.get("global", {}).get("dictionary_url")
        if dictionary_url is None:
            logger.error("No dictionary URL in manifest {}".format(manifest_file))
            return

        logger.info("  Using dictionary: {}".format(dictionary_url))
        recorded_errors = validate_mapping(dictionary_url, etl_mapping_file, manifest)

        if recorded_errors:
            logger.error("  ETL mapping validation failed:")
            for err in recorded_errors:
                logger.error("  - {}".format(err))
            raise AssertionError(
                "ETL mapping validation failed. See errors in previous logs."
            )
        else:
            logger.info("  OK!")


@main.command()
@click.argument("repository", type=str, nargs=1, required=True)
@click.argument("pull_request_number", type=int, nargs=1, required=True)
def post_deployment_changes(repository, pull_request_number):
    """
    Comment on a pull request with any deployment changes when updating manifest services. Also comment a warning if a service is on a branch.
    """
    comment_deployment_changes_on_pr(repository, pull_request_number)


@main.command()
@click.argument("bucket")
@click.argument("prefix")
@click.argument("script")
@click.option("--region", default="us-east-1", show_default=True)
@click.option(
    "--access-key-id", default=os.environ.get("ACCESS_KEY_ID"), show_default=True
)
@click.option(
    "--secret-access-key",
    default=os.environ.get("SECRET_ACCESS_KEY"),
    show_default=True,
)
@click.option(
    "-c",
    "--concurrency",
    type=int,
    default=multiprocessing.cpu_count() + 1,
    show_default=True,
)
@click.option("--progress/--no-progress", default=True, show_default=True)
def s3log(*args, **kwargs):
    """Run SCRIPT in Gen3 logs under S3 BUCKET:PREFIX.

    The SCRIPT should be importable defining a method like this:

    \b
        def handle_row(obj, line):
            if 1 + 1 == 2:
                return line

    The returning results will be joined with newline into the stdout.
    """
    try:
        from gen3utils.s3log.s3log import S3Log
    except ImportError as e:
        print(e, '\nInstall with `poetry install --extras "s3log"` to run this command')
        exit(1)

    S3Log(*args, **kwargs).run()


if __name__ == "__main__":
    main()
