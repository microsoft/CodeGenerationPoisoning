from jinja2 import Environment
from jinja2 import FileSystemLoader
import yaml

my_template = Environment(loader=FileSystemLoader('../templates'))

vlans = yaml.load(open('vlans.yml'), Loader=yaml.SafeLoader)

print(type(vlans))
template = my_template.get_template("vlans.j2")
result = template.render(vlans=vlans)
print(result)

