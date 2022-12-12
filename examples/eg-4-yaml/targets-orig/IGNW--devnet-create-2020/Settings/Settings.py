# Settings file for the library
import yaml
import os

from yaml.scanner import ScannerError
from pathlib import Path


class SettingsError(Exception):
    pass


class Settings():
    def __init__(self, settings_file=None):
        if settings_file is None:
            self.settings_file = Path("./settings.yml")
        else:
            self.settings_file = Path(settings_file)

        # Log file enablement
        self.log_file_name = "/var/log/pge-aci-web.log"
        self.log_file_enable = True

        # Set environment variables for ACI
        self.apic_creds = {
            'url': '',
            'username': '',
            'password': ''}

        # Application variables
        self.application_title = ""
        self.app_addr = os.getenv('APP_SERVER_IPADDR', 'localhost')
        self.app_port = 5000

        self.url_base = 'http://{0}:{1}/api/v1'.format(self.app_addr, self.app_port)
        self.data_url = ""
        self.form_data = []
        self.records = []

        # Theme files and theme to use for the system - Also for buttons, etc.
        # Theme and jscript code:  https://jqueryui.com
        self.theme = "a"
        self.theme_cancel = "b"
        self.theme_file_1 = "themes/dlt_themes.min.css"
        self.theme_file_2 = "themes/jquery.mobile.icons.min.css"

        # Files needed for the login
        self.header_graphic_file = 'lko_header.png'
        self.style_wu_file = 'wu.css'
        self.fabric_names = {'https://10.50.0.100': 'Lab2-fake'}

        # Override the defaults above
        self.load_settings_file()

    # Load data from the settings.yml file
    def load_settings_file(self):
        try:
            with open(self.settings_file, "r") as settings_file:
                data = yaml.safe_load(settings_file)
                for k, v in data.items():
                    setattr(self, k, v)
        except FileNotFoundError:
            # If the settings.yml file is missing, means use defaults
            pass
        except ScannerError as e:
            raise SettingsError(f"You have a malformed 'settings.yml' file.  Please fix this.  The error can be found in the following message: {e}")
