import requests
import json
from jinja2 import Environment
from jinja2 import FileSystemLoader
from acicontroller import get_token
from acicontroller import execute_rest_call
import yaml

JSON_TEMPLATES = Environment(loader=FileSystemLoader('templates'), trim_blocks=True)

yml_file = open("./vars/aci_variables.yml").read()
yml_dict = yaml.load(yml_file, yaml.SafeLoader)
tenant = yml_dict['tenant']

def delete_tenant():
    tenant_endpoint = "api/mo/uni.json"
    template = JSON_TEMPLATES.get_template("delete_tenant.j2.json")
    payload = template.render(name=tenant)
   
    response = execute_rest_call(endpoint=tenant_endpoint, method="POST", data=payload)
    return response

if __name__ == "__main__":
    response = delete_tenant()

    if not response.status_code == 200:
      print(f"Something went wrong deleting the tenant {tenant}")
    else:
      print(f"Successfully deleted tenant with name {tenant}")

    
    
    