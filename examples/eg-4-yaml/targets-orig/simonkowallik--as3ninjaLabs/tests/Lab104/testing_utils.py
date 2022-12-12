import yaml
from pathlib import Path


def Tenants(path: str) -> dict:
    # utility function
    def readYamlFile(filename: str) -> dict:
        """reads a file and"""
        with open(filename) as f:
            return yaml.safe_load(f.read())

    # read Tenants configuration in 'tenants' dict
    tenants: dict = {}
    for tenant in Path(path).glob("*.yaml"):
        tenants.update(readYamlFile(tenant))

    return tenants
