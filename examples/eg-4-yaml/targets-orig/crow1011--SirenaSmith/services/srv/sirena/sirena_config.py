import yaml

def get_conf():
    with open('sirena.yaml') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
        return data