import json
from odoo_nginx.env import get_template
from odoo_nginx.schemas import SiteConfigSchema

# import yaml
# with open("odoo_nginx/format.yml") as f:
#     data = yaml.safe_load(f)

data = {
    "config_filename1": {
        "server_name": "monserver.com",
        "web_upstream": "192.168.13.1:8076",
        "poll_upstream": "192.168.13.1:8072",
        "proxy_pass": "192.168.13.1:8076",
        "httpaccess": True,
        "httpsaccess": True,
        "proxy_http_11": True,
        "cache_statics": True,
        "disable_cache_zone": False,
        "header_upgrade": True,
        "header_connection": True,
        "header_host": True,
        "masquerade": "test.odoocloud.ch",
        "redirect": "https://www.test.com",
        "allow_tls_v1": None,
        "certificat_folder": "test_client",
        "ip_allow": [
            "80.254.189.97",
            "81.62.154.114",
            "45.66.220.128",
        ],
        "ip_deny": "all",
    }
}
print(json.dumps(data, indent=4))

template = get_template("site.j2")

filename, config = list(data.items())[0]

print(json.dumps(config, indent=4))
config = SiteConfigSchema.validate(config)
print(json.dumps(config, indent=4))

print(template.render(config=config))