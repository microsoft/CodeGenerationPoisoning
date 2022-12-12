import boto3
from botocore.exceptions import WaiterError
import yaml
from datetime import datetime
import simplejson as json

from stackuchin.utilities import alert
from stackuchin.utilities import result

import warnings
warnings.filterwarnings("ignore")


def update(profile_name, stack_file, stack_name, secret, slack_webhook_url,
           s3_bucket, s3_prefix, only_errors, from_pipeline=False):
    aws_region = None
    aws_account = None
    stacks = None
    stack_template = None
    action = 'UPDATE'
    changeset = None
    client_token = datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")

    stacks = None
    try:
        with open(stack_file, 'r') as stack_stream:
            stacks = yaml.safe_load(stack_stream)
    except yaml.YAMLError as exc:
        print(exc)
        exit(1)

    if stack_name not in stacks:
        print("{} was not found in your stack file.".format(stack_name))
        if from_pipeline:
            alert(stack_name,
                  "{} was not found in your stack file {}.".format(
                      stack_name, stack_file),
                  None, None, action, profile_name, slack_webhook_url)
        exit(1)

    if 'Account' not in stacks[stack_name]:
        print("The Account property is missing from the stack definition.")
        if from_pipeline:
            alert(stack_name,
                  "The Account property is missing from the stack {} in stack_file {}.".format(
                      stack_name, stack_file),
                  None, None, action, profile_name, slack_webhook_url)
        exit(1)

    if 'Region' not in stacks[stack_name]:
        print("The Region property is missing from the stack definition.")
        if from_pipeline:
            alert(stack_name,
                  "The Region property is missing from the stack {} in stack_file {}.".format(
                      stack_name, stack_file),
                  None, None, action, profile_name, slack_webhook_url)
        exit(1)

    if 'Template' not in stacks[stack_name]:
        print("The Template property is missing from the stack definition.")
        if from_pipeline:
            alert(stack_name,
                  "The Template property is missing from the stack {} in stack_file {}.".format(
                      stack_name, stack_file),
                  None, None, action, profile_name, slack_webhook_url)
        exit(1)

    if 'Parameters' not in stacks[stack_name]:
        print("The Parameters property is missing from the stack definition.")
        print("Should you with to deploy a stack with no parameters, please define the property as: \n"
              "\"Parameters: {}\"")
        if from_pipeline:
            alert(stack_name,
                  "The Parameters property is missing from the stack "
                  "" + stack_name + " in stack_file " + stack_file + ".\n"
                  "Should you with to deploy a stack with no parameters, please simply define the property as: \n"
                  "Parameters: {}",
                  None, None, action, profile_name, slack_webhook_url)
        exit(1)

    template = None
    try:
        with open(stacks[stack_name]['Template'], 'r') as template_stream:
            template = json.load(template_stream)
    except Exception as e:
        try:
            with open(stacks[stack_name]['Template'], 'r') as template_stream:
                template = yaml.safe_load(template_stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(1)

    if 'Resources' not in template:
        print("The CloudFormation templates provided for this stack does not contain any Resources")
        if from_pipeline:
            alert(stack_name,
                  "The CloudFormation template {} for stack {} does not contain any Resources.".format(
                      stacks[stack_name]['Template'], stack_name),
                  None, None, action, profile_name, slack_webhook_url)
        exit(1)

    # Get auth
    if not from_pipeline:
        if profile_name is not None:
            try:
                boto3.setup_default_session(profile_name=profile_name)
            except Exception as exc:
                print(exc)
                exit(1)

    sts = boto3.client('sts')
    iam_user = sts.get_caller_identity()['Arn']

    # Verify integrity of stack
    stacks = None
    aws_role_arn = None
    try:
        with open(stack_file, 'r') as stack_stream:
            stacks = yaml.safe_load(stack_stream)
            aws_region = stacks[stack_name]['Region']
            aws_account = stacks[stack_name]['Account']
            stack_template = stacks[stack_name]['Template']
            if 'AssumedRoleArn' in stacks[stack_name]:
                aws_role_arn = stacks[stack_name]['AssumedRoleArn']
    except yaml.YAMLError as exc:
        print(exc)
        alert(stack_name,
              "Unable to verify required options for stack {} in stack file {}. Exception = {}".format(
                  stack_name, stack_file, exc),
              aws_region, aws_account, action, profile_name, slack_webhook_url)
        exit(1)

    # Set role
    role_session = None
    if aws_role_arn is not None:
        try:
            if profile_name is not None:
                boto3.setup_default_session(profile_name=profile_name)

            # Get current timestamp
            current_date = datetime.utcnow().isoformat()
            current_date = current_date.replace(':', '-').replace('.', '-')

            # Assume role
            sts_client = boto3.client('sts')
            assumed_role_object = sts_client.assume_role(
                RoleArn=aws_role_arn,
                RoleSessionName="AssumeRoleSession-{}".format(current_date)
            )
            credentials = assumed_role_object['Credentials']
            role_session = boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )
            iam_user = aws_role_arn
        except Exception as exc:
            print(exc)
            alert(stack_name,
                  "Unable to assume role {} for stack {}. Exception = {}".format(
                      aws_role_arn, stack_name, exc),
                  aws_region, aws_account, action, profile_name, slack_webhook_url)
            exit(1)

    # Connect to AWS CloudFormation
    cf_client = boto3.client('cloudformation', region_name=aws_region) if role_session is None else \
        role_session.client('cloudformation', region_name=aws_region)

    # Create AWS S3 Resource
    s3_session = boto3.resource('s3', region_name=aws_region) if role_session is None else \
        role_session.resource('s3', region_name=aws_region)

    # Get parameter and tags from stack
    stack_parameters, stack_tags, stack_template_url = result(stack_file, stack_name, secret,
                                                              s3_bucket, s3_prefix,
                                                              aws_region, aws_account,
                                                              action, profile_name, slack_webhook_url,
                                                              s3_session)

    # Create change set
    try:
        if stack_template_url['type'] == 'TemplateURL':
            changeset = cf_client.create_change_set(StackName=stack_name,
                                                    TemplateURL=stack_template_url['value'],
                                                    Parameters=stack_parameters,
                                                    Capabilities=[
                                                        'CAPABILITY_NAMED_IAM', 'CAPABILITY_IAM',
                                                        'CAPABILITY_AUTO_EXPAND'
                                                    ],
                                                    Tags=stack_tags,
                                                    ClientToken=client_token,
                                                    ChangeSetName="Changeset-{}".format(client_token))
        else:
            template_body = stack_template_url['value']
            if type(template_body) != str:
                template_body = json.dumps(template_body, default=str)
            changeset = cf_client.create_change_set(StackName=stack_name,
                                                    TemplateBody=template_body,
                                                    Parameters=stack_parameters,
                                                    Capabilities=[
                                                        'CAPABILITY_NAMED_IAM', 'CAPABILITY_IAM',
                                                        'CAPABILITY_AUTO_EXPAND'
                                                    ],
                                                    Tags=stack_tags,
                                                    ClientToken=client_token,
                                                    ChangeSetName="Changeset-{}".format(client_token))
    except Exception as exc:
        print(exc)
        alert(stack_name,
              "Unable to create change set. Exception = {}".format(exc),
              aws_region, aws_account, action, profile_name, slack_webhook_url, iam_user)
        exit(1)

    # Waiting for the change set to finish creating
    waiter = None
    try:
        waiter = cf_client.get_waiter('change_set_create_complete')
        waiter.wait(ChangeSetName=changeset['Id'])
    except WaiterError as exc:
        if 'Submit different information' in exc.last_response['StatusReason']:
            print("Nothing to update for stack {}".format(stack_name))
            if from_pipeline:
                return True
            exit(0)
        else:
            print(exc)
            alert(stack_name,
                  "Unable to create change set. Exception = {}".format(exc),
                  aws_region, aws_account, action, profile_name, slack_webhook_url, iam_user)
            exit(1)

    # Executing change set
    try:
        cf_client.execute_change_set(ChangeSetName=changeset['Id'], ClientRequestToken=client_token)
    except Exception as exc:
        print(exc)
        alert(stack_name,
              "Unable to start stack creation process. Exception = {}".format(exc),
              aws_region, aws_account, action, profile_name, slack_webhook_url, iam_user)
        exit(1)

    # Waiting for stack to finish updating
    if not only_errors:
        print("UPDATE_STARTED for stack {}".format(stack_name))
        alert(stack_name, None, aws_region, aws_account, "UPDATE_STARTED", profile_name, slack_webhook_url, iam_user)
    waiter = None
    try:
        waiter = cf_client.get_waiter('stack_update_complete')
        waiter.wait(StackName=stack_name)
    except Exception as exc:
        pass

    # Check final status of stack
    stack_events = cf_client.describe_stack_events(StackName=stack_name)
    failure_reasons = []
    for resource in stack_events["StackEvents"]:
        if "ClientRequestToken" in resource and \
            client_token == resource["ClientRequestToken"] and \
                "FAILED" in str(resource["ResourceStatus"]):

            failure_reasons.append("- *{}* <> {}".format(resource["LogicalResourceId"],
                                                         resource["ResourceStatusReason"]))
    if len(failure_reasons) > 0:
        print("UPDATE_FAILURE for stack {}".format(stack_name))
        alert(stack_name,
              'Stack creation process ended with status {}.\n'
              'Failure reasons :\n{}'.format(
                  "UPDATE_FAILED",
                  "\n".join(failure_reasons)
              ),
              aws_region, aws_account, action, profile_name, slack_webhook_url, iam_user)
        exit(1)

    if not only_errors:
        print("UPDATE_COMPLETE for stack {}".format(stack_name))
        alert(stack_name, None, aws_region, aws_account, "UPDATE_COMPLETE", profile_name, slack_webhook_url, iam_user)

    return True
