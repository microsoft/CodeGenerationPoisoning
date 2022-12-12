from acicontroller import get_token
from acicontroller import execute_rest_call
from create_tenant import create_tenant
from create_vrf import create_vrf
from create_bd import create_bd
from create_ap import create_ap
from create_epg import create_epg
from create_filter import create_filter
from create_contract import create_contract
from assign_contract import assign_contract
import yaml

yml_file = open("./vars/aci_variables.yml").read()
yml_dict = yaml.load(yml_file, yaml.SafeLoader)

tenant    = yml_dict['tenant']
vrf       = yml_dict['vrf']
bd        = yml_dict['bridge_domains'][0]['bd']
bd_subnet = yml_dict['bridge_domains'][0]['gateway'] + "/" + yml_dict['bridge_domains'][0]['mask']
ap        = yml_dict['ap']

def create_aci_constructs(): 
   print("---" * 50)
   print(f"Creating tenant with name {tenant}")
   response = create_tenant(tenant)

   if not response.status_code == 200:
      print(f"  => Something went wrong creating the tenant")
   else: 
      print(f"  => Successfully created Tenant with name {tenant}")

   print("---" * 50)
   print(f"Creating VRF with name {vrf}")
   response = create_vrf(tenant, vrf)

   if not response.status_code == 200:
      print(f"  => Something went wrong creating the VRF")
   else: 
      print(f"  => Successfully created VRF with name {vrf}")

   print("---" * 50)
   print(f"Creating BD with name {bd}")
   response = create_bd(tenant, vrf, bd, bd_subnet)

   if not response.status_code == 200:
      print(f"  => Something went wrong creating the BD")
   else: 
      print(f"  => Successfully created BD with name {vrf}")

   print("---" * 50)
   print(f"Creating AP {ap}")
   create_ap(tenant, bd, ap)

   if not response.status_code == 200:
      print(f"  => Something went wrong creating the AP")
   else: 
      print(f"  => Successfully created AP with name {ap}")


   amount_epgs = len(yml_dict['epgs'])

   for i in range(0, amount_epgs): 
      print("---" * 50)
      epg = yml_dict['epgs'][i]['epg']
      print(f"Creating EPG with name {epg} ")
      create_epg(tenant, ap, epg)

      if not response.status_code == 200:
         print(f"  => Something went wrong creating the EPG")
      else: 
         print(f"  => Successfully created EPG with name {epg}")


   amount_filters = len(yml_dict['filters'])

   for i in range(0, amount_filters): 
      print("---" * 50)
      filter = yml_dict['filters'][i]['filter']
      print(f"Creating filter with name {filter} ")
      create_filter(tenant, filter)

      if not response.status_code == 200:
         print(f"  => Something went wrong creating the filter")
      else: 
         print(f"  => Successfully created filter with name {filter}")
   
   amount_contracts = len(yml_dict['contracts'])

   for i in range(0, amount_contracts): 
      print("---" * 50)
      contract = yml_dict['contracts'][i]['contract']
      print(f"Creating contract with name {contract} ")
      create_contract(tenant, contract)

      if not response.status_code == 200:
         print(f"  => Something went wrong creating the contract")
      else: 
         print(f"  => Successfully created filter with name {contract}")



   amount_epg_contracts = len(yml_dict['epg_contracts'])

   for i in range(0, amount_epg_contracts): 
      print("---" * 50)
      epg           = yml_dict['epg_contracts'][i]['epg']
      contract      = yml_dict['epg_contracts'][i]['contract']
      contract_type = yml_dict['epg_contracts'][i]['contract_type']
      print(f"Assigning contract to EPG with name {contract} ")
      assign_contract(tenant, ap, epg, contract, contract_type)

      if not response.status_code == 200:
         print(f"  => Something went wrong assigning contract to EPG")
      else: 
         print(f"  => Successfully assigned contract to EPG with name {epg}")



if __name__ == "__main__":
   create_aci_constructs()