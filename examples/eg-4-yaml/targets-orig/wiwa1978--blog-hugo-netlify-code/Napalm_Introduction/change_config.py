from jinja2 import Environment, FileSystemLoader
from napalm import get_network_driver
import yaml


#This loads data from YAML into Python dictionary
config_data = yaml.load(open('change_config.yml'), Loader=yaml.SafeLoader)

#This line uses the current directory and loads the jinja2 template
env = Environment(loader = FileSystemLoader('.'), trim_blocks=True, lstrip_blocks=True)
template = env.get_template('change_config.j2')


#Return the template with data
response = template.render(config_data)

driver_xr = get_network_driver("iosxr")

device = {
    "device_type": "cisco_xr",
    "ip": "sbx-iosxr-mgmt.cisco.com",
    "username": "admin",
    "password": "C1sco12345",
    "port": "8181",
}

device_xr = driver_xr(hostname=device['ip'], username=device['username'], password=device['password'], optional_args={'port':device['port']})
device_xr.open()

facts = device_xr.load_merge_candidate(config=response)

print('\nDiff:')
diff = device_xr.compare_config()
print(diff)

if len(diff) < 1:
   print('\nNo Changes Required Closing...')
   device_xr.discard_config()
   device_xr.disconnect()
   exit()

try:
   choice = input("\nWould you like to commit these changes? [yN]: ")
except NameError:
   choice = input("\nWould you like to commit these changes? [yN]: ")
if choice == 'y':
   print('Committing ...')
   device_xr.commit_config()

else:
   print('Discarding ...')
   device_xr.discard_config()
   device_xr.disconnect()