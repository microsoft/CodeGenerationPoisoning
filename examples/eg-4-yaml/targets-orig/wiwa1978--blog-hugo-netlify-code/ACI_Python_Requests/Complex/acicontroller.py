import requests
import json
from jinja2 import Environment
from jinja2 import FileSystemLoader
import yaml

JSON_TEMPLATES = Environment(loader=FileSystemLoader('templates'), trim_blocks=True)

yml_file = open("./vars/aci_variables.yml").read()
yml_dict = yaml.load(yml_file, yaml.SafeLoader)

url = yml_dict['url']

username = yml_dict['username']
password = yml_dict['password']

def get_token():
   login_endpoint = "api/aaaLogin.json"
   template = JSON_TEMPLATES.get_template("login.j2.json")
   payload = template.render(username=username, password=password)
   login_url=url+login_endpoint
   requests.packages.urllib3.disable_warnings()
   response = requests.post(login_url, data=payload, verify=False).json()
   token = response['imdata'][0]['aaaLogin']['attributes']['token']
   return token

def execute_rest_call(endpoint, method, data):
   token = get_token()
   requests.packages.urllib3.disable_warnings()
   cookies = {'APIC-Cookie': token}
   if method == "POST":
      response = requests.post(url + endpoint, data=data, cookies=cookies, verify=False)
   else:
      print("executing get")
      response = requests.get(url,cookies=cookies, verify=False)

   if 199 < response.status_code < 300:
      return response
   else:
      error_message = json.loads(response.text)['imdata'][0]['error']['attributes']['text']
      if error_message.endswith("already exists."):
         return None
      else:
         raise Exception(error_message)

  

      