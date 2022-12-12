


"""
#1、创建yaml格式文件
#2、读取这个文件
#3、输出这个文件
"""

#2、读取单个文档
#1）、导入yaml包
import yaml
#2）、打开文件 encoding="utf-8"
#with open("./data.yml","r",encoding="utf-8") as f:
#3）、使用yaml读取文件
#    r = yaml.safe_load(f)
#3、输出这个文件内容
#    print(r)

#读取多个文档
#1、编辑或修改data.yml
#2、yaml读取方法，all
#with open("./data.yml","r",encoding="utf-8") as f:
#    r = yaml.safe_load_all(f)
#3、循环打印
#    for i in r:
#        print(i)
from utils.YamlUtil import YamlReader

#res = YamlReader("./data.yml").data()
res = YamlReader("./data.yml").data_all()
print(res)
