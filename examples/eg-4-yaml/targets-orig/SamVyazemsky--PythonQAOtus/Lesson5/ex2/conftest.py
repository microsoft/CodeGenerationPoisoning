# -*- coding: utf-8 -*-
import os
import yaml
import pytest
import requests


def pytest_addoption(parser):
    parser.addoption("--user", action="store", default="1", help="user for auth")
    parser.addoption("--password", action="store", default="1", help="password for auth")


def pytest_generate_tests(metafunc):
    # Пропускаем все функции, у которых нет аргумента test_input
    if 'status_code' not in metafunc.fixturenames:
        return

    # Определяем директорию текущего файла
    dir_path = os.path.dirname(os.path.abspath(metafunc.module.__file__))

    # Определяем путь к файлу с данными
    file_path = "test_status_code_get.yaml"
    # Открываем выбранный файл
    with open(file_path) as f:
        test_cases = yaml.load(f)

    # Предусматриваем неправильную загрузку и пустой файл
    if not test_cases:
        raise ValueError("Test cases not loaded")

    return metafunc.parametrize("status_code, expected_result", test_cases)


@pytest.fixture()
def status_url():
    return 'http://httpbin.org/status/'


@pytest.fixture()
def basic_auth(request):
    user = request.config.getoption("--user")
    password = request.config.getoption("--password")
    url = "https://httpbin.org/basic-auth/{}/{}".format(user, password)
    resp = requests.get(url).json()
    try:
        resp["authenticated"] is True
    except ConnectionError('Auth failed'):
        if resp['status_code'] == 401:
            print('Incorrect password or user')
        else:
            print("shit happens")
