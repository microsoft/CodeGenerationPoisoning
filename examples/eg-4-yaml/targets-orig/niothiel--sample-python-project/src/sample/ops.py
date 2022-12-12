import yaml


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def is_valid_yaml(yaml_str: str):
    try:
        content = yaml.safe_load(yaml_str)
    except Exception:
        return False

    print("Content of captured yaml", content)
    return True
