import yaml
import concurrent.futures
import boto3
import time
import random


from stackuchin.create import create
from stackuchin.delete import delete
from stackuchin.update import update

import warnings
warnings.filterwarnings("ignore")


def perform_parallel_changes(stack):
    time.sleep(random.randint(0, 30))

    if stack['action'] == 'create':
        return create(
            stack['profile_name'],
            stack['stack_file'],
            stack["stack_name"],
            stack['secrets'],
            stack['slack_webhook_url'],
            stack['s3_bucket'],
            stack['s3_prefix'],
            stack['only_errors'],
            True)

    if stack['action'] == 'update':
        return update(
            stack['profile_name'],
            stack['stack_file'],
            stack["stack_name"],
            stack['secrets'],
            stack['slack_webhook_url'],
            stack['s3_bucket'],
            stack['s3_prefix'],
            stack['only_errors'],
            True)

    if stack['action'] == 'delete':
        return delete(
            stack['profile_name'],
            stack['stack_file'],
            stack["stack_name"],
            stack['slack_webhook_url'],
            stack['only_errors'],
            True)

    return True


def start_pipeline(profile_name, stack_file, pipeline_file,
                   slack_webhook_url, s3_bucket, s3_prefix, only_errors):

    pipeline_type = 'sequential'

    pipeline = None
    try:
        with open(pipeline_file, 'r') as pipeline_stream:
            pipeline = yaml.safe_load(pipeline_stream)
            pipeline = pipeline['pipeline']
    except yaml.YAMLError as exc:
        print(exc)
        exit(1)

    if 'pipeline_type' in pipeline:
        pipeline_type = pipeline['pipeline_type']

    if profile_name is not None:
        boto3.setup_default_session(profile_name=profile_name)

    if pipeline_type == "sequential":
        # First create new stacks (if any)
        if "create" in pipeline:
            for stack in pipeline["create"]:
                secrets = []
                if "secrets" in stack:
                    for hidden in stack["secrets"]:
                        secrets.append(
                            "{}={}".format(hidden["Name"], hidden["Value"])
                        )
                create(profile_name, stack_file, stack["stack_name"], secrets,
                       slack_webhook_url, s3_bucket, s3_prefix, only_errors, True)

        # Then update existing stacks (if any)
        if "update" in pipeline:
            for stack in pipeline["update"]:
                secrets = []
                if "secrets" in stack:
                    for hidden in stack["secrets"]:
                        secrets.append(
                            "{}={}".format(hidden["Name"], hidden["Value"])
                        )
                update(profile_name, stack_file, stack["stack_name"], secrets,
                       slack_webhook_url, s3_bucket, s3_prefix, only_errors, True)

        # And finally delete stacks (if any)
        if "delete" in pipeline:
            for stack in pipeline["delete"]:
                delete(profile_name, stack_file, stack["stack_name"], slack_webhook_url, only_errors, True)

    else:
        # Build array of executions
        stacks = []

        # Check if any stacks to create
        if "create" in pipeline:
            for stack in pipeline["create"]:
                secrets = []
                if "secrets" in stack:
                    for hidden in stack["secrets"]:
                        secrets.append(
                            "{}={}".format(hidden["Name"], hidden["Value"])
                        )
                stacks.append({
                    "action": "create",
                    "profile_name": profile_name,
                    "stack_file": stack_file,
                    "stack_name": stack["stack_name"],
                    "secrets": secrets,
                    "slack_webhook_url": slack_webhook_url,
                    "s3_bucket": s3_bucket,
                    "s3_prefix": s3_prefix,
                    "only_errors": only_errors
                })

        # Check if any stacks to update
        if "update" in pipeline:
            for stack in pipeline["update"]:
                secrets = []
                if "secrets" in stack:
                    for hidden in stack["secrets"]:
                        secrets.append(
                            "{}={}".format(hidden["Name"], hidden["Value"])
                        )
                stacks.append({
                    "action": "update",
                    "profile_name": profile_name,
                    "stack_file": stack_file,
                    "stack_name": stack["stack_name"],
                    "secrets": secrets,
                    "slack_webhook_url": slack_webhook_url,
                    "s3_bucket": s3_bucket,
                    "s3_prefix": s3_prefix,
                    "only_errors": only_errors
                })

        # Check if any stacks to delete
        if "delete" in pipeline:
            for stack in pipeline["delete"]:
                secrets = []
                if "secrets" in stack:
                    for hidden in stack["secrets"]:
                        secrets.append(
                            "{}={}".format(hidden["Name"], hidden["Value"])
                        )
                stacks.append({
                    "action": "delete",
                    "profile_name": profile_name,
                    "stack_file": stack_file,
                    "stack_name": stack["stack_name"],
                    "secrets": secrets,
                    "slack_webhook_url": slack_webhook_url,
                    "s3_bucket": s3_bucket,
                    "s3_prefix": s3_prefix,
                    "only_errors": only_errors
                })

        # Execute parallel deployments
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=len(stacks)) as executor:
            results = {
                executor.submit(perform_parallel_changes, stack): stack
                for stack in stacks
            }
            for future in concurrent.futures.as_completed(results):
                future.result()

