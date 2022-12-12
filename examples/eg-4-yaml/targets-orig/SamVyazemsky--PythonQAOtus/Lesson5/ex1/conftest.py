# -*- coding: utf-8 -*-
import os
import yaml
import pytest


def pytest_generate_tests(metafunc):

    # Пропускаем все функции, у которых нет аргумента test_input
    if 'test_input' not in metafunc.fixturenames:
        return


    # Определяем директорию текущего файла
    dir_path = os.path.dirname(os.path.abspath(metafunc.module.__file__))

    # Определяем путь к файлу с данными
    file_path = os.path.join(dir_path, metafunc.function.__name__ + '.yaml')
    # Открываем выбранный файл
    with open(file_path) as f:
        test_cases = yaml.load(f)

    # Предусматриваем неправильную загрузку и пустой файл
    if not test_cases:
        raise ValueError("Test cases not loaded")

    return metafunc.parametrize("test_input, expected_result", test_cases)