import yaml
from jinja2 import Environment, FileSystemLoader

loopbacks = yaml.load(open('loopback.yml'), Loader=yaml.SafeLoader)

env = Environment(loader = FileSystemLoader('../../templates'), trim_blocks=True, lstrip_blocks=True)
template = env.get_template('loopback.j2')
loopback_config = template.render(loopbacks)

print(loopback_config)