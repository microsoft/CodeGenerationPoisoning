import yaml
import json
import torch
from tqdm import tqdm
import torch.utils.data.dataset as Dataset


def parse_config(conf_file):
    """
    解析yaml配置文件
    Args:
        conf_file:yaml配置文件路径
    Returns:
    解析后的配置对象
    """
    with open(conf_file, 'r',encoding='utf-8') as conf:
        conf = yaml.load(conf)
    return conf


def mkdata(tokenizer, tokens):
    # input_ids = [torch.tensor(tokenizer.encode(' '.join(i[0].strip().split(' |\n')[:512]))) for i in tokens]
    input_ids = []
    len_list = []
    for ii in tqdm(range(len(tokens))):
        i = tokens[ii]
        tos = ['[CLS]'] + tokenizer.tokenize(i[1]) + ['[SEP]'] + tokenizer.tokenize(i[0])
        tos = tos[:510]+['[SEP]']
        # print(tos)
        temp = tokenizer.convert_tokens_to_ids(tos)
        input_ids.append(torch.tensor(temp))
    te = 0
    ssss = []
    for i in tokens:
        ssss.append(float(i[2]))
        if i[2]==0:
            te+=1
    target = torch.tensor(ssss)
    print(te)
    return input_ids, target

def mktestdata(tokenizer, tokens):
    # input_ids = [torch.tensor(tokenizer.encode(' '.join(i[0].strip().split(' |\n')[:512]))) for i in tokens]
    input_ids = []
    len_list = []
    tops = tokens[1]
    tokens = tokens[0]
    for ii in range(len(tokens)):
        i = tokens[ii]
        tos = ['[CLS]'] + tokenizer.tokenize(i[1]) + ['[SEP]'] + tokenizer.tokenize(i[0])
        tos = tos[:510]+['[SEP]']
        # print(tos)
        temp = tokenizer.convert_tokens_to_ids(tos)
        input_ids.append(torch.tensor(temp))
    te = 0
    ssss = []
    for i in tokens:
        ssss.append(float(i[2]))
        if i[2]==0:
            te+=1
    target = torch.tensor(ssss)
    # print(te)
    return input_ids, target, tops

class subDataset(Dataset.Dataset):
    # 初始化，定义数据内容和标签
    def __init__(self, Data, Label):
        self.Data = Data
        self.Label = Label

    # 返回数据集大小
    def __len__(self):
        return len(self.Data)

    # 得到数据内容和标签
    def __getitem__(self, index):
        data = self.Data[index]
        label = self.Label[index]
        return data, label


def getData(conf_file):
    conf = parse_config(conf_file)
    data_conf, params_conf = conf['path'], conf['params']

    train_path = data_conf['train_data']
    intv = params_conf['intv']
    if (params_conf['gra'] == 'para'):
        train_path = data_conf['train_data_para']
    if (params_conf['gra'] == 'sent'):
        train_path = data_conf['train_data_sent']
    print(train_path)
    train_data = []

    file = []
    with open(train_path, 'r', encoding='utf-8') as f:
        file += f.readlines()
    for line in file[:10000]:
        js = json.loads(line)
        # print(js['text'])
        # print(js['question'])
        # print(js['label'])
        train_data.append([js['text'], js['question'], js['label']])
    #
    # file = []
    # with open(test_path, 'r', encoding='utf-8') as f:
    #     file += f.readlines()
    # sss= intv/10
    # for line in file[:2000]:
    #     js = json.loads(line)
    #     test_data.append([js['text'], js['question'], js['label']])

    return train_data#, test_data

# print([1,2,3,4,5][:2])

def getTestData(conf_file):
    conf = parse_config(conf_file)
    data_conf, params_conf = conf['path'], conf['params']
    test_path = data_conf['test_data_new']
    if (params_conf['gra'] == 'para'):
        test_path = data_conf['test_data_para_new']
    if (params_conf['gra'] == 'sent'):
        test_path = data_conf['test_data_sent_new']
    print(test_path)
    test_data = []

    file = []
    with open(test_path, 'r', encoding='utf-8') as f:
        file += f.readlines()
    for line in file[:]:
        js = json.loads(line)
        samples = []
        for item in js['sample']:
            samples.append([item['text'], item['question'], item['label']])
        test_data.append([samples,js['top']])
    return test_data

print(torch.mean(torch.tensor([1.0,2.0,3.0,4.0])))