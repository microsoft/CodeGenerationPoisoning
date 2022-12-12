# coding=utf-8

import urllib.request
import json
import os
import yaml

base_dir = os.path.dirname(os.path.dirname(__file__))

def get_text(env):
    web_config_path = os.path.join(base_dir, 'config/interface_config.yaml')
    with open(web_config_path, 'r', encoding='utf-8') as file:
        data = yaml.load(file.read(), Loader=yaml.FullLoader)

    urlList=data['common']
    listdata = []
    for i in urlList:
        resp = urllib.request.urlopen(urlList[i])
        ele_json = json.loads(resp.read())
        listdata.append(ele_json)

    return listdata

if __name__ == "__main__":
    textdata = get_text('url')

