import yaml
from jinja2 import Environment, FileSystemLoader

interfaces = yaml.load(open('loopback_variant.yml'), Loader=yaml.SafeLoader)

env = Environment(loader = FileSystemLoader('../../templates'), trim_blocks=True, lstrip_blocks=True)
template = env.get_template('loopback_variant.j2')
loopback_config = template.render(data=interfaces)

print(loopback_config)