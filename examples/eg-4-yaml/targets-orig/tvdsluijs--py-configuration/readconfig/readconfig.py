# pip install pyyaml
import logging
import yaml


class ReadConfig:

    def __init__(self, config_file: str = None):
        try:
            self.config = None
            self.config_file = config_file

            if self.config_file is None:
                self.config_file = "./config/config.yml"

            self.read_config()

        except Exception as e:
            logging.warning(e)

    def read_config(self) -> dict:
        try:

            with open(self.config_file) as f:
                self.config = yaml.load(f, Loader=yaml.FullLoader)

        except Exception as e:
            logging.warning("We could not open or parse the config file! " + " | " + str(e))
            return False


if __name__ == '__main__':
    file = "tests/config.yml"
    rc = ReadConfig(file)
    print(rc)
