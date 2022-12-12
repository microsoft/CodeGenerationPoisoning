from PyInquirer import prompt
from socialist_ir.cdk_menu import CdkMenu
from socialist_ir.config import Config
from aws_cdk import (
    core,
    aws_lambda as _lambda,
)
import boto3
import os
import json
import yaml
import zipfile
import time
import datetime

class LambdaCreate(CdkMenu):
    def __init__(
        self,
        name: str = "lambda_create",
        required_variables: list = [],
    ):
        super().__init__(name=name, required_variables=required_variables)


    def execute(self) -> bool:
        try:
            rolename = f"in_lam_01_helloworld_lambdarole_{int(datetime.datetime.now().timestamp())}"
            fname = "hw"
            pyloc = os.path.join(os.getcwd(), "tests", f"{fname}.py")
            ziploc = os.path.join(os.getcwd(), "tests", f"{fname}.zip")

            basic_role = """
            Version: '2012-10-17'
            Statement:
                Effect: Allow
                Principal: 
                    Service: lambda.amazonaws.com
                Action: sts:AssumeRole
            """
            
            iam = boto3.client('iam')

            # lambda.awazonaws.com can assume this role. 
            iam.create_role(RoleName=rolename, 
                AssumeRolePolicyDocument=json.dumps(yaml.load(basic_role, Loader=yaml.FullLoader)))

            # This role has the AWSLambdaBasicExecutionRole managed policy.
            iam.attach_role_policy(RoleName=rolename, 
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole')
            
            print(f"Successfully created iam role for lambda function - '{rolename}'.")

            client = boto3.client('lambda')

            with zipfile.ZipFile(ziploc, 'w') as z:
                z.write(pyloc, os.path.basename(os.path.join(os.getcwd(), "tests")))

            # Loads the zip file as binary code. 
            with open(ziploc, 'rb') as f: 
                code = f.read()

            # Need delay otherwise complains about bad iam role
            time.sleep(10)
            role = iam.get_role(RoleName=rolename)

            lambda_name = f"in_lam_01_HelloWorld_{int(datetime.datetime.now().timestamp())}"

            client.create_function(
                FunctionName = lambda_name,
                Runtime="python3.8",
                Role = role["Role"]["Arn"],
                Handler = f"{fname}.lambda_handler",
                Code = {
                    'ZipFile' : code
                }
            )
            print(f"Successfully created lambda function '{lambda_name}'.")
            return True
        except Exception as e:
            print(e)
            return False

    def setup(self) -> None:
        # Prompt required variables
        pass