import random
import string
import pytest
import yaml
import airplay
import os
import json
import subprocess


# TODO: be generic about table name and content !!!!!!!!!!!!!!!!!!!!!!!!!!!!!


# generate random items- code
def random_str(typo, nr_char):
    letters = string.ascii_letters
    numbers = string.digits
    if typo == "l":
        char = letters
    else:
        char = numbers
    output = [y for nr in range(nr_char) for y in random.choice(list(char))]
    try:
        return int(''.join(output))
    except ValueError:
        return ''.join(output)


# generate string to insert
def rand_item(count=1):
    res = []
    for _ in range(count):
        res.append({'Name': random_str("l", 10), 'Code': random_str("n", 10)})
    return res


def _wrap_insert(x):
    tbl, item = x
    return tbl.insert(**item)


# def test_concurrency():
#     p = multiprocessing.Pool(20)
#     items = rand_item(30)
#     res = p.map(_wrap_insert, [(tbl, item) for item in items])
#     p.close()
#     p.join()
#     if res[0] != 200:
#         return res


def test_wrong_api_key():
    with open(r'config.yaml') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    tbl0 = airplay.Table(config['base_key'], config['table_name'], 'asf')
    with pytest.raises(airplay.HTTPStatusCodeException):
        tbl0.items()


def test_cli_actions():
    PL = "{\"Name\": \"test1000\", \"Code\": 1000}"
    TB = "Table 9"

    # test get
    param = ['python', 'cli_airplay.py', TB, 'get']
    cli_test = subprocess.check_output(param, encoding="utf-8")
    assert 'records' in cli_test
    # test ins
    param = ['python', 'cli_airplay.py', TB, 'ins', '-payload', PL]
    cli_test = subprocess.check_output(param, encoding="utf-8")
    id_ = json.loads(cli_test)['id']
    assert 'test1000' in cli_test
    # test mod
    param = ['python', 'cli_airplay.py', TB, 'mod', '-payload', PL, '-t', id_]
    cli_test = subprocess.check_output(param, encoding="utf-8")
    assert 'test1000' in cli_test
    # test del
    param = ['python', 'cli_airplay.py', TB, 'del', '-t', id_]
    cli_test = subprocess.check_output(param, encoding="utf-8")
    assert 'deleted' in cli_test


def test_config_yaml():
    import tempfile
    import shutil
    import subprocess
    temp_dir = tempfile.TemporaryDirectory(prefix='Tom')
    src = os.getcwd()
    print(src)
    dst = temp_dir.name
    fn = 'test_config.yaml'
    shutil.copyfile(os.path.join(src, fn), os.path.join(dst, "config1.yaml"))
    os.chdir(dst)
    # test with valid alternative conf
    param = ['python', '{}'.format(os.path.join(src, 'cli_airplay.py')), 'Table 9', 'get', '-c', 'config1.yaml']
    cli_test = subprocess.check_output(param, encoding="utf-8")
    assert 'records' in cli_test
    # test -h

    param = ['python', '{}'.format(os.path.join(src, 'cli_airplay.py')), '-h']
    cli_test = subprocess.check_output([*param], encoding="utf-8")
    assert 'help' in cli_test

    # test without valid alternative conf
    param = ['python', '{}'.format(os.path.join(src, 'cli_airplay.py')), 'Table 9', 'get', '-c {}'.format('C:\\users')]
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.check_output([*param], encoding="utf-8")

    os.chdir(src)


def test_class():
    print(os.path.abspath('config.yaml'))

    with open(r'config.yaml') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)

    tbl = airplay.Table(config['base_key'], config['table_name'], config['api_key'])

    rsp0 = tbl.items()
    assert 'error' not in rsp0
    rsp1 = tbl.insert(Name='Items00', Code=100)
    assert 'error' not in rsp1
    rsp3 = tbl.items()
    my_id = rsp3['records'][0]['id']
    rsp4 = tbl.modify(my_id, Name='RenameItem00', Code=200)
    assert 'error' not in rsp4
    tbl.delete(my_id)

# def test_all():
#     resp_ins = old_airplay.table_insert(Name='item01', Code=200)
#     assert resp_ins[0] == 200
#     assert resp_ins[1] is not None
#
#     resp_get = old_airplay.table_get()
#     assert resp_get is not None
#     assert len(resp_get) == 2
#
#     resp_mod = old_airplay.table_modify(resp_ins[1], Name='rename_item01', Code=200)
#     assert resp_mod[0] == 200
#     assert resp_mod[1] == resp_ins[1]
#
#     resp_get = old_airplay.table_get()
#     assert resp_get is not None
#     assert len(resp_get) == 2
#
#     resp_del = old_airplay.table_del(resp_ins[1])
#     assert resp_del is not None
#     assert resp_del[0] == 200
#     assert resp_del[1] == resp_ins[1]
