import argparse
from argparse import RawTextHelpFormatter
import sys
import os
import yaml


PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from stackuchin.create import create
from stackuchin.delete import delete
from stackuchin.update import update
from stackuchin.start_pipeline import start_pipeline


class StackuchinCLI(object):

    def __init__(self):
        parser = argparse.ArgumentParser(
            description='CLI tool to automatically create, update and delete AWS CloudFormation '
                        'stacks in multiple AWS accounts and regions at the same time',
            usage='''stackuchin <command> [<args>]

To see help text, you can run:
    stackuchin help
    stackuchin version
    stackuchin create --help
    stackuchin delete --help
    stackuchin update --help
    stackuchin pipeline --help
''')
        parser.add_argument('command', help='Command to run')
        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail
        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            parser.print_help()
            exit(1)
        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()

    # noinspection PyMethodMayBeStatic
    def version(self):
        print("1.6.0")

    # noinspection PyMethodMayBeStatic
    def create(self):
        parser = argparse.ArgumentParser(
            description='Create command system',
            formatter_class=RawTextHelpFormatter
        )
        parser.add_argument('--stack_file', dest="stack_file"
                            , default='./cloudformation-stacks.yaml'
                            , help="The YAML file which contains your stack definitions.\n"
                                   "Defaults to \"./cloudformation-stacks.yaml\" if not specified.")
        parser.add_argument('--stack_name', dest="stack_name", required=True
                            , help="The stack that you wish to create")
        parser.add_argument('--secret', dest="secret", required=False, default=None
                            , action='append', metavar='Parameter=Value'
                            , help='Argument used to specify values for NoEcho parameters in your stack')
        parser.add_argument('--slack_webhook', dest="slack_webhook", required=False, default=None
                            , help='Argument used to overwrite environment variable STACKUCHIN_SLACK.\n'
                                   'If argument is specified, any notifications will be sent to this URL.\n'
                                   'If not specified, the script will check for env var STACKUCHIN_SLACK.\n'
                                   'If neither argument nor environment variable is specified, then no notifications '
                                   'will be sent.')
        parser.add_argument('--s3_bucket', dest="s3_bucket", required=False, default=None
                            , help='Argument used to overwrite environment variable STACKUCHIN_BUCKET_NAME.\n'
                                   'If argument is specified, then the template is first uploaded here before '
                                   'used in the stack.\n'
                                   'If not specified, the script will check for env var STACKUCHIN_BUCKET_NAME.\n'
                                   'If neither argument nor environment variable is specified, then the script will '
                                   'attempt to feed the template directly to the AWS API call, however, due to '
                                   'AWS CloudFormation API call limitations, you might end up with a bigger template '
                                   'in byte size than the max value allowed by AWS.\n'
                                   'Details here -> https://docs.aws.amazon.com/AWSCloudFormation/latest/'
                                   'UserGuide/cloudformation-limits.html')
        parser.add_argument('--s3_prefix', dest="s3_prefix", required=False, default=None
                            , help='Argument used to overwrite environment variable STACKUCHIN_BUCKET_PREFIX.\n'
                                   'The bucket prefix path to be used when the S3 bucket is defined.')
        parser.add_argument('--only_errors', dest="only_errors", required=False, default=False, action="store_true"
                            , help='By default, all notifications are sent to Slack if slack_webhook is defined.\n'
                                   'By running this command you ensure that only errors are getting pushed.\n'
                                   'This is useful in case you don\'t want to see COMPLETE and START notifications.')
        parser.add_argument('-p', '--profile', dest='profile', default=None
                            , help='The AWS profile you\'ll be using.\n'
                                   'If not specified, the "default" profile will be used. \n'
                                   'If no profiles are defined, then the default AWS credential mechanism starts.\n')
        args = parser.parse_args(sys.argv[2:])

        slack_webhook_url = None
        if args.slack_webhook is not None:
            slack_webhook_url = args.slack_webhook
        else:
            if "STACKUCHIN_SLACK" in os.environ:
                slack_webhook_url = os.environ.get('STACKUCHIN_SLACK')

        s3_bucket = None
        if args.s3_bucket is not None:
            s3_bucket = args.s3_bucket
        else:
            if "STACKUCHIN_BUCKET_NAME" in os.environ:
                s3_bucket = os.environ.get('STACKUCHIN_BUCKET_NAME')

        s3_prefix = None
        if args.s3_prefix is not None:
            s3_prefix = args.s3_prefix
        else:
            if "STACKUCHIN_BUCKET_PREFIX" in os.environ:
                s3_prefix = os.environ.get('STACKUCHIN_BUCKET_PREFIX')

        create(args.profile, args.stack_file, args.stack_name,
               args.secret, slack_webhook_url, s3_bucket, s3_prefix, args.only_errors)

    # noinspection PyMethodMayBeStatic
    def delete(self):
        parser = argparse.ArgumentParser(
            description='Delete command system',
            formatter_class=RawTextHelpFormatter
        )
        parser.add_argument('--stack_file', dest="stack_file"
                            , default='./cloudformation-stacks.yaml'
                            , help="The YAML file which contains your stack definitions.\n"
                                   "Defaults to \"./cloudformation-stacks.yaml\" if not specified.")
        parser.add_argument('--stack_name', dest="stack_name", required=True
                            , help="The stack that you wish to create")
        parser.add_argument('--slack_webhook', dest="slack_webhook", required=False, default=None
                            , help='Argument used to overwrite environment variable STACKUCHIN_SLACK.\n'
                                   'If argument is specified, any notifications will be sent to this URL.\n'
                                   'If not specified, the script will check for env var STACKUCHIN_SLACK.\n'
                                   'If neither argument nor environment variable is specified, then no notifications '
                                   'will be sent.')
        parser.add_argument('--only_errors', dest="only_errors", required=False, default=False, action="store_true"
                            , help='By default, all notifications are sent to Slack if slack_webhook is defined.\n'
                                   'By running this command you ensure that only errors are getting pushed.\n'
                                   'This is useful in case you don\'t want to see COMPLETE and START notifications.')
        parser.add_argument('-p', '--profile', dest='profile', default=None
                            , help='The AWS profile you\'ll be using.\n'
                                   'If not specified, the "default" profile will be used. \n'
                                   'If no profiles are defined, then the default AWS credential mechanism starts.\n')
        args = parser.parse_args(sys.argv[2:])

        slack_webhook_url = None
        if args.slack_webhook is not None:
            slack_webhook_url = args.slack_webhook
        else:
            if "STACKUCHIN_SLACK" in os.environ:
                slack_webhook_url = os.environ.get('STACKUCHIN_SLACK')

        delete(args.profile, args.stack_file, args.stack_name, slack_webhook_url, args.only_errors)

    # noinspection PyMethodMayBeStatic
    def update(self):
        parser = argparse.ArgumentParser(
            description='Update command system',
            formatter_class=RawTextHelpFormatter
        )
        parser.add_argument('--stack_file', dest="stack_file"
                            , default='./cloudformation-stacks.yaml'
                            , help="The YAML file which contains your stack definitions.\n"
                                   "Defaults to \"./cloudformation-stacks.yaml\" if not specified.")
        parser.add_argument('--stack_name', dest="stack_name", required=True
                            , help="The stack that you wish to update")
        parser.add_argument('--secret', dest="secret", required=False, default=None
                            , action='append', metavar='Parameter=Value'
                            , help='Argument used to specify values for NoEcho parameters in your stack')
        parser.add_argument('--slack_webhook', dest="slack_webhook", required=False, default=None
                            , help='Argument used to overwrite environment variable STACKUCHIN_SLACK.\n'
                                   'If argument is specified, any notifications will be sent to this URL.\n'
                                   'If not specified, the script will check for env var STACKUCHIN_SLACK.\n'
                                   'If neither argument nor environment variable is specified, then no notifications '
                                   'will be sent.')
        parser.add_argument('--s3_bucket', dest="s3_bucket", required=False, default=None
                            , help='Argument used to overwrite environment variable STACKUCHIN_BUCKET_NAME.\n'
                                   'If argument is specified, then the template is first uploaded here before '
                                   'used in the stack.\n'
                                   'If not specified, the script will check for env var STACKUCHIN_BUCKET_NAME.\n'
                                   'If neither argument nor environment variable is specified, then the script will '
                                   'attempt to feed the template directly to the AWS API call, however, due to '
                                   'AWS CloudFormation API call limitations, you might end up with a bigger template '
                                   'in byte size than the max value allowed by AWS.\n'
                                   'Details here -> https://docs.aws.amazon.com/AWSCloudFormation/latest/'
                                   'UserGuide/cloudformation-limits.html')
        parser.add_argument('--s3_prefix', dest="s3_prefix", required=False, default=None
                            , help='Argument used to overwrite environment variable STACKUCHIN_BUCKET_PREFIX.\n'
                                   'The bucket prefix path to be used when the S3 bucket is defined.')
        parser.add_argument('--only_errors', dest="only_errors", required=False, default=False, action="store_true"
                            , help='By default, all notifications are sent to Slack if slack_webhook is defined.\n'
                                   'By running this command you ensure that only errors are getting pushed.\n'
                                   'This is useful in case you don\'t want to see COMPLETE and START notifications.')
        parser.add_argument('-p', '--profile', dest='profile', default=None
                            , help='The AWS profile you\'ll be using.\n'
                                   'If not specified, the "default" profile will be used. \n'
                                   'If no profiles are defined, then the default AWS credential mechanism starts.\n')
        args = parser.parse_args(sys.argv[2:])


        slack_webhook_url = None
        if args.slack_webhook is not None:
            slack_webhook_url = args.slack_webhook
        else:
            if "STACKUCHIN_SLACK" in os.environ:
                slack_webhook_url = os.environ.get('STACKUCHIN_SLACK')

        s3_bucket = None
        if args.s3_bucket is not None:
            s3_bucket = args.s3_bucket
        else:
            if "STACKUCHIN_BUCKET_NAME" in os.environ:
                s3_bucket = os.environ.get('STACKUCHIN_BUCKET_NAME')

        s3_prefix = None
        if args.s3_prefix is not None:
            s3_prefix = args.s3_prefix
        else:
            if "STACKUCHIN_BUCKET_PREFIX" in os.environ:
                s3_prefix = os.environ.get('STACKUCHIN_BUCKET_PREFIX')

        update(args.profile, args.stack_file, args.stack_name, args.secret,
               slack_webhook_url, s3_bucket, s3_prefix, args.only_errors)

    # noinspection PyMethodMayBeStatic
    def pipeline(self):
        parser = argparse.ArgumentParser(
            description='Create command system',
            formatter_class=RawTextHelpFormatter
        )
        parser.add_argument('--stack_file', dest="stack_file"
                            , default='./cloudformation-stacks.yaml'
                            , help="The YAML file which contains your stack definitions.\n"
                                   "Defaults to \"./cloudformation-stacks.yaml\" if not specified.")
        parser.add_argument('--pipeline_file', dest="pipeline_file", required=True
                            , help="The pipeline definition file to run your deployments.")
        parser.add_argument('--slack_webhook', dest="slack_webhook", required=False, default=None
                            , help='Argument used to overwrite environment variable STACKUCHIN_SLACK.\n'
                                   'If argument is specified, any notifications will be sent to this URL.\n'
                                   'If not specified, the script will check for env var STACKUCHIN_SLACK.\n'
                                   'If neither argument nor environment variable is specified, then no notifications '
                                   'will be sent.')
        parser.add_argument('--s3_bucket', dest="s3_bucket", required=False, default=None
                            , help='Argument used to overwrite environment variable STACKUCHIN_BUCKET_NAME.\n'
                                   'If argument is specified, then the template is first uploaded here before '
                                   'used in the stack.\n'
                                   'If not specified, the script will check for env var STACKUCHIN_BUCKET_NAME.\n'
                                   'If neither argument nor environment variable is specified, then the script will '
                                   'attempt to feed the template directly to the AWS API call, however, due to '
                                   'AWS CloudFormation API call limitations, you might end up with a bigger template '
                                   'in byte size than the max value allowed by AWS.\n'
                                   'Details here -> https://docs.aws.amazon.com/AWSCloudFormation/latest/'
                                   'UserGuide/cloudformation-limits.html')
        parser.add_argument('--s3_prefix', dest="s3_prefix", required=False, default=None
                            , help='Argument used to overwrite environment variable STACKUCHIN_BUCKET_PREFIX.\n'
                                   'The bucket prefix path to be used when the S3 bucket is defined.')
        parser.add_argument('--only_errors', dest="only_errors", required=False, default=False, action="store_true"
                            , help='By default, all notifications are sent to Slack if slack_webhook is defined.\n'
                                   'By running this command you ensure that only errors are getting pushed.\n'
                                   'This is useful in case you don\'t want to see COMPLETE and START notifications.')
        parser.add_argument('-p', '--profile', dest='profile', default=None
                            , help='The AWS profile you\'ll be using.\n'
                                   'If not specified, the "default" profile will be used. \n'
                                   'If no profiles are defined, then the default AWS credential mechanism starts.\n')
        args = parser.parse_args(sys.argv[2:])

        stacks = None
        try:
            with open(args.stack_file, 'r') as stack_stream:
                stacks = yaml.safe_load(stack_stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(1)

        pipeline = None
        try:
            with open(args.pipeline_file, 'r') as pipeline_stream:
                pipeline = yaml.safe_load(pipeline_stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(1)

        if 'pipeline' not in pipeline:
            print("The pipeline_file {} must contain a top-level object called \"pipeline\".".format(
                args.pipeline_file))
            exit(1)

        if 'pipeline_type' in pipeline['pipeline']:
            if str(pipeline['pipeline']['pipeline_type']).lower() not in ['parallel', 'sequential']:
                print("The value for \"pipeline_type\" can be either \"parallel\" or \"sequential\".")
                print("If not specified, the default value is \"sequential\".")
                exit(1)

        if 'update' not in pipeline['pipeline'] and \
                'delete' not in pipeline['pipeline'] and \
                'create' not in pipeline['pipeline']:
            print("An action type of either \"update\", \"create\", or \"delete\" must be defined "
                  "in the \"pipeline\" object definition.")
            exit(1)

        for action in ["update", "create", "delete"]:
            if action in pipeline["pipeline"]:
                if type(pipeline["pipeline"][action]) is not list:
                    print("Expected a list of inputs for the command {}.".format(action))
                    exit(1)
                for item in pipeline["pipeline"][action]:
                    if "stack_name" not in item:
                        print("A property with key \"stack_name\" must be present in each item "
                              "for the {} command.".format(action))
                        exit(1)
                    if "no_echo" in item:
                        if type(item["no_echo"]) is not list:
                            print("If you want to specify \"secrets\", make sure they "
                                  "are a list of Name/Value objects.")
                            exit(1)
                            for secret in item["no_echo"]:
                                if "Name" not in secret or "Value" not in secret:
                                    print("You must specify a combination of Name/Value objects "
                                          "for each item in your secrets")
                                    exit(1)

        slack_webhook_url = None
        if args.slack_webhook is not None:
            slack_webhook_url = args.slack_webhook
        else:
            if "STACKUCHIN_SLACK" in os.environ:
                slack_webhook_url = os.environ.get('STACKUCHIN_SLACK')

        s3_bucket = None
        if args.s3_bucket is not None:
            s3_bucket = args.s3_bucket
        else:
            if "STACKUCHIN_BUCKET_NAME" in os.environ:
                s3_bucket = os.environ.get('STACKUCHIN_BUCKET_NAME')

        s3_prefix = None
        if args.s3_prefix is not None:
            s3_prefix = args.s3_prefix
        else:
            if "STACKUCHIN_BUCKET_PREFIX" in os.environ:
                s3_prefix = os.environ.get('STACKUCHIN_BUCKET_PREFIX')

        start_pipeline(args.profile, args.stack_file, args.pipeline_file,
                       slack_webhook_url, s3_bucket, s3_prefix, args.only_errors)

def main():
    StackuchinCLI()


if __name__ == '__main__':
    StackuchinCLI()
