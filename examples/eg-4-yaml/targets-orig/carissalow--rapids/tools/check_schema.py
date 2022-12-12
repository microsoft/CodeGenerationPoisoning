# Adapted from https://bitbucket.org/snakemake/snakemake/pull-requests/291/schema-based-validation/diff
from jsonschema import Draft7Validator
import yaml
import collections
class OrderedLoader(yaml.Loader):
    pass

def construct_mapping(loader, node):
    loader.flatten_mapping(node)
    return collections.OrderedDict(loader.construct_pairs(node))

OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
with open("tools/config.schema.yaml") as f:
    data = yaml.load(f, OrderedLoader)

Draft7Validator.check_schema(data)
print("Schema is OK")