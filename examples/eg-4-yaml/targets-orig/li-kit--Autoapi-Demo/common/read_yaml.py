import yaml
import os
import allure

print(__file__)
print(os.path.realpath(__file__))   # 返回的是真实路径


@allure.step("获取yaml文件数据")
def get_yaml_date(yml_path):
    '''获取yaml文件数据'''
    fp = open(yml_path, 'r', encoding='utf-8')
    f = fp.read()
    fp.close()
    # 把yaml文件数据转为dict
    d = yaml.load(f, Loader=yaml.FullLoader)
    print(d)
    return d


if __name__ == '__main__':
    from setting import base_dir
    yml_path = os.path.join(base_dir, 'test_data', 'update_info.yml')
    print(yml_path)
    get_yaml_date(yml_path)