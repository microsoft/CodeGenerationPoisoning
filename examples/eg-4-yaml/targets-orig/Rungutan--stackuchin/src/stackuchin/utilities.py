import yaml
import requests
from datetime import datetime
import simplejson as json


def get_parameters(stack_file, stack_name, secret, stack_region=None,
                   stack_account=None, action=None,
                   profile_name=None, slack_webhook_url=None):

    stacks = None
    try:
        with open(stack_file, 'r') as stack_stream:
            stacks = yaml.safe_load(stack_stream)
    except yaml.YAMLError as exc:
        print(exc)
        alert(stack_name, exc, stack_region, stack_account, action,
              profile_name, slack_webhook_url)
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

    # Get list of required parameters for stack
    required_params = []
    try:
        required_params = [k for k, v in template.get('Parameters', {}).items()]
    except Exception as exc:
        print(exc)
        alert(stack_name, "Unable to get list of required parameters. Exception = {}".format(str(exc)),
              stack_region, stack_account, action,
              profile_name, slack_webhook_url)
        exit(1)

    # Fill in output array with Parameters from stack file
    output_array = []
    try:
        if "Parameters" in template:
            for key in template['Parameters']:
                if key in stacks[stack_name]['Parameters']:
                    output_array.append({
                        "ParameterKey": key,
                        "ParameterValue": stacks[stack_name]['Parameters'][key]
                    })
    except Exception as exc:
        print(exc)
        alert(stack_name,
              "Unable to get parameter key/value definition from stack file. Exception = {}".format(str(exc)),
              stack_region, stack_account, action,
              profile_name, slack_webhook_url)
        exit(1)

    # Get list of secret arguments
    array_parameters_from_arguments = []
    try:
        no_echo_overrides = dict([pair.split('=') for pair in secret or []])
        for key in no_echo_overrides:
            array_parameters_from_arguments.append({
                    "ParameterKey": key,
                    "ParameterValue": no_echo_overrides[key]
                })
    except Exception as exc:
        print(exc)
        alert(stack_name,
              "Unable to get read of secret parameters from arguments. Exception = {}".format(str(exc)),
              stack_region, stack_account, action,
              profile_name, slack_webhook_url)
        exit(1)

    # If key with same name as secret is present in stack_file, overwrite it in output_array
    # If key with same name as secret is NOT present in stack_file, then just add it to output_array
    try:
        for i in range(len(array_parameters_from_arguments)):
            found = False
            for j in range(len(output_array)):
                if array_parameters_from_arguments[i]["ParameterKey"] == output_array[j]["ParameterKey"]:
                    output_array[j]["ParameterValue"] = array_parameters_from_arguments[i]["ParameterValue"]
                    found = True
                    break
            if not found:
                output_array.append({
                    "ParameterKey": array_parameters_from_arguments[i]["ParameterKey"],
                    "ParameterValue": array_parameters_from_arguments[i]["ParameterValue"]
                })
    except Exception as exc:
        print(exc)
        alert(stack_name,
              "Unable to get concatenate secret and stack file parameter definition. Exception = {}".format(str(exc)),
              stack_region, stack_account, action,
              profile_name, slack_webhook_url)
        exit(1)

    # If any template parameters are still required but not defined, then push them with "UsePreviousValue"
    try:
        for param in required_params:
            found = False
            for i in range(len(output_array)):
                if output_array[i]["ParameterKey"] == param:
                    found = True
                    break
            if not found:
                output_array.append({
                    "ParameterKey": param,
                    "UsePreviousValue": True
                })
    except Exception as exc:
        print(exc)
        alert(stack_name,
              "Unable to set non-defined parameters with UsePreviousValue logic. Exception = {}".format(str(exc)),
              stack_region, stack_account, action,
              profile_name, slack_webhook_url)
        exit(1)

    return output_array


def get_tags(stack_file, stack_name, stack_region=None,
             stack_account=None, action=None,
             profile_name=None, slack_webhook_url=None):

    stacks = None
    try:
        with open(stack_file, 'r') as stack_stream:
            stacks = yaml.safe_load(stack_stream)
    except yaml.YAMLError as exc:
        print(exc)
        alert(stack_name, exc, stack_region, stack_account, action,
              profile_name, slack_webhook_url)
        exit(1)

    tags = []
    try:
        tags = stacks[stack_name]['Tags']
    except Exception as exc:
        print(exc)
        alert(stack_name,
              "Unable to set tags based on stack file. Exception = {}".format(str(exc)),
              stack_region, stack_account, action,
              profile_name, slack_webhook_url)
        exit(1)

    return [{'Key': k, 'Value': v} for k, v in tags.items()]


def upload(stack_file, stack_name, s3_bucket, s3_prefix,
           stack_region=None, stack_account=None, action=None,
           profile_name=None, slack_webhook_url=None, s3_session=None):

    stacks = None
    try:
        with open(stack_file, 'r') as stack_stream:
            stacks = yaml.safe_load(stack_stream)
    except yaml.YAMLError as exc:
        print(exc)
        alert(stack_name, exc, stack_region, stack_account, action,
              profile_name, slack_webhook_url)
        exit(1)

    template_string = None
    try:
        with open(stacks[stack_name]['Template'], 'r') as template_stream:
            template_string = json.load(template_stream)
    except Exception as e:
        try:
            with open(stacks[stack_name]['Template'], 'r') as template_stream:
                template_string = yaml.safe_load(template_stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(1)

    output_object = {
        "type": "TemplateBody",
        "value": json.dumps(template_string, default=str)
    }

    template_key = None
    if s3_bucket is not None and stack_region is not None:
        timestamp_key = datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")
        template_key = '{}/{}/{}'.format(stack_name, timestamp_key, stacks[stack_name]['Template'])
        if s3_prefix is not None:
            while str(s3_prefix).endswith("/"):
                s3_prefix = str(s3_prefix)[:-1]
            template_key = '{}/{}/{}/{}'.format(s3_prefix, stack_name, timestamp_key,
                                                stacks[stack_name]['Template'])
        try:
            s3_session.Bucket(s3_bucket).upload_file(
                stacks[stack_name]['Template'],
                template_key
            )
        except Exception as exc:
            print(exc)
            alert(stack_name,
                  "Unable to push template to S3 bucket {} and S3 prefix {}. Exception = {}".format(
                      s3_bucket, s3_prefix, str(exc)
                  ),
                  stack_region, stack_account, action,
                  profile_name, slack_webhook_url)
            exit(1)

        output_object = {
            "type": "TemplateURL",
            "value": "https://{}.s3.amazonaws.com/{}".format(s3_bucket, template_key)
        }

    return output_object


def result(stack_file, stack_name, secret, s3_bucket, s3_prefix,
           stack_region=None, stack_account=None, action=None,
           profile_name=None, slack_webhook_url=None, s3_session=None):

    params = get_parameters(stack_file, stack_name, secret, stack_region,
                            stack_account, action, profile_name, slack_webhook_url)

    tags = get_tags(stack_file, stack_name, stack_region,
                    stack_account, action, profile_name, slack_webhook_url)

    template_url = upload(stack_file, stack_name, s3_bucket, s3_prefix, stack_region,
                    stack_account, action, profile_name, slack_webhook_url, s3_session)

    return params, tags, template_url


def alert(stack_name, error=None, stack_region=None, stack_account=None, action=None,
          profile_name=None, slack_webhook_url=None, iam_user="IAM User"):

    if slack_webhook_url is not None:
        action = str(action).upper()

        if stack_region is not None and stack_account is not None:
            tpl = None
            payload_text = '*{}* - *{}*'.format(stack_name, action)
            if error is not None:
                tpl = 'Stack *{}* process failed with error *{}* for stackId ' \
                      '<https://console.aws.amazon.com/cloudformation/home?region={}#/stacks/stackinfo?stackId={}>' \
                      ' in region `{}` for account Id `{}`.'.format(
                        action, error, stack_region,
                        stack_name, stack_region, stack_account)

                payload_text = '*{}* - *{}* - *FAILED*'.format(stack_name, str(action).upper())
            else:
                tpl = 'IAM user `{}` is doing operation *{}* for stack ' \
                      '<https://console.aws.amazon.com/cloudformation/home?region={}#/stacks/stackinfo?stackId={}>' \
                      ' in region `{}` for account Id `{}`.'.format(
                        iam_user, action, stack_region,
                        stack_name, stack_region, stack_account)

            payload = {
                'text': payload_text,
                'attachments': [
                    {
                        'fallback': tpl,
                        'fields': [
                            {
                                "title": "Stack URL",
                                "value": 'https://console.aws.amazon.com/cloudformation/home?region={}#'
                                         '/stacks/stackinfo?stackId={}'.format(stack_region, stack_name),
                                "short": False
                            },
                            {
                                "title": "AWS IAM Author",
                                "value": iam_user,
                                "short": False
                            },
                            {
                                "title": "AWS Region",
                                "value": stack_region,
                                "short": False
                            },
                            {
                                "title": "AWS Account Id",
                                "value": stack_account,
                                "short": False
                            },
                            {
                                "title": "Operation",
                                "value": str(action).upper(),
                                "short": False
                            }
                        ]
                    }

                ]
            }
            if error is not None:
                payload['attachments'][0]['fields'].append({
                    "title": "Error",
                    "value": error,
                    "short": False
                })
            try:
                requests.post(slack_webhook_url, json=payload)
            except Exception as e:
                print(e)
                return False
        else:
            tpl = None
            payload_text = '*{}* - *{}*'.format(stack_name, action)
            if error is not None:
                tpl = 'Stack operation *{}* process failed with error *{}* for stackId `{}`.'.format(
                    action, error, stack_name)
                payload_text = '*{}* - *{}* - *FAILED*'.format(stack_name, action)
            else:
                tpl = 'IAM user `{}` is doing operation *{}* for stackId `{}`.'.format(
                    iam_user, action, stack_name)

            payload = {
                'text': payload_text,
                'attachments': [
                    {
                        'fallback': tpl,
                        'fields': [
                            {
                                "title": "AWS IAM Author",
                                "value": iam_user,
                                "short": False
                            },
                            {
                                "title": "Operation",
                                "value": str(action).upper(),
                                "short": False
                            }
                        ]
                    }

                ]
            }
            if error is not None:
                payload['attachments'][0]['fields'].append({
                    "title": "Error",
                    "value": error,
                    "short": False
                })
            try:
                requests.post(slack_webhook_url, json=payload)
            except Exception as e:
                print(e)
                return False
    return True
