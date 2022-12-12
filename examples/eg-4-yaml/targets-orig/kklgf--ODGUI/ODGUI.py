import sys
import yaml

if __name__ == "__main__":
    sys.path.append("..")
    sys.path.append("./Tensorflow/models/research")
    from data.GUI.GUI import *

    with open(r'config.yml') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    config['loader']['image_size'] = (config['loader']['default_size']['x'], config['loader']['default_size']['y'])

    ########
    # GUI idzie tutaj i zbiera dane w config
    # nadpisuje standardowe wartości wczytane z config.yml
    ########
    gui = GUI(config)
