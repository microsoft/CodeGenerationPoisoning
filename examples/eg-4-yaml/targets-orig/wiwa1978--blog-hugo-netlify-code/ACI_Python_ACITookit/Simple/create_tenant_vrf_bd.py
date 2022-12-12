from acitoolkit.acitoolkit import *
import yaml
from pprint import pprint

url = "https://10.48.109.10/"

user = "admin"
pwd = "C1sco123"

session = Session(url, user, pwd)
session.login()

# Read YAML configuration
yml_file = open("variables.yml").read()
yml_dict = yaml.load(yml_file, yaml.SafeLoader)

tenant_name = yml_dict['tenant']
vrf_name = yml_dict['vrf']
bd_name = yml_dict['bridge_domains'][0]['bd']

# Create ACI objects
tenant = Tenant(tenant_name)
vrf = Context(vrf_name, tenant)
bd = BridgeDomain(bd_name, tenant)

response = session.push_to_apic(tenant.get_url(), data=tenant.get_json())

print(response)