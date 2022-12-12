import yaml
import sys,os

def getalldata():
    with open("./config.yaml") as f:
        k = f.read()
    a = yaml.load(k, Loader=yaml.FullLoader)
    print(a)

def getdata(config1,config2):
    with open("./data/config.yaml") as f:
        k = f.read()
    a = yaml.load(k, Loader=yaml.FullLoader)
    print(a[config1][config2])
    return a[config1][config2]

# getdata("setup_account", "username")

def getThirddata(first,second,third):
    with open("./data/config.yaml") as f:
        k = f.read()
    a = yaml.load(k, Loader=yaml.FullLoader)
    # print(a)
    # print("1111111111111111111111111")
    # print(a[first])
    # print("2222222222222222222222222")
    # print(a[first][1])
    # print(a[first][second][third])
    return a[first][second][third]

getThirddata("multi_account", 1, "username")