from jinja2 import Environment
from jinja2 import FileSystemLoader
import yaml

my_template = Environment(loader=FileSystemLoader("templates"), trim_blocks=True, lstrip_blocks=True)

variables = yaml.load(open("variables.yml"), Loader=yaml.SafeLoader)
print(variables)

template = my_template.get_template("terraform.j2")
result = template.render(data=variables)
print(result)
