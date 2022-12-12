import pandas as pd
import yaml
from os import path
import pytest
from src.clean import clean, remove_na, remove_cancel, remove_invalid_prod, remove_return, remove_wrong, clean_desc
from src.evaluate import accuracy_calculator
from src.product_dim import product_dim
from src.create_basket import create_basket
from src.train import train, get_support, get_popular, get_recommendations, frozenset2String, pivot_rules, fill_no_rec
from src.helper import read_csv
import numpy as np
import config.config as config

# Get project path
project_path = path.dirname(path.dirname(path.abspath(__file__)))
test_config_path = project_path + "/" + config.TEST_YAML
func_config_path = project_path +  "/" + config.CONFIG_YAML

# Load configurations from .yaml
with open(test_config_path, "r") as f:
    test_conf = yaml.load(f, Loader=yaml.FullLoader)
with open(func_config_path, "r") as f:
    func_conf = yaml.load(f, Loader=yaml.FullLoader)


# Unit test for clean
raw_data_path = project_path + "/" + test_conf['raw_data']
raw_df = read_csv(raw_data_path)


def test_clean_valid():
    """
    Test clean --happy path
    This function clean the raw data
    """
    true_data_path = project_path + "/" + test_conf['clean_data']
    true_df = pd.read_csv(true_data_path, dtype=str)

    test_df = clean(raw_df, **func_conf['clean'])
    test_df = test_df.astype(str)

    assert true_df.equals(test_df)


def test_clean_invalid():
    """
    Test clean --unhappy path
    """

    unhappy_df = raw_df.drop("StockCode", axis=1)

    with pytest.raises(KeyError):
        clean(unhappy_df, **func_conf['clean'])


def test_remove_na():
    """
    remove_na() removes rows from input DataFrame
    """
    test_df = remove_na(raw_df)
    assert test_df.isnull().sum().sum() == 0


def test_remove_cancel():
    """
    remove_cancel() removes rows whose Invoice contains 'C'
    """
    test_df = remove_cancel(raw_df)
    assert sum(test_df['Invoice'].str.contains("C")) == 0


def test_remove_invalid_prod():
    """
    remove_invalid_prod() removes rows with invalid StockCode
    """
    test_df = remove_invalid_prod(raw_df)
    assert len(test_df) == sum(test_df['StockCode'].str.match(r'\d{5}[A-Z]*'))


def test_remove_return():
    """
    remove_return() removes rows with negative quantity
    """
    test_df = remove_return(raw_df)
    assert sum(test_df['Quantity'] < 0) == 0


def test_remove_wrong():
    """
    remove_wrong() removes wrong transactions
    """
    test_df = remove_wrong(raw_df)
    assert sum(test_df['Price'] <= 0) == 0


def test_clean_desc():
    """
    clean_desc() makes all valid product has one and only one description
    """
    test_df = clean_desc(raw_df)
    assert max(test_df.groupby('StockCode')['Description_clean'].nunique()) == 1


# Unit test for create basket and product_dim

clean_data_path = project_path + "/" + test_conf['clean_data']
clean_df = read_csv(clean_data_path)


def test_create_basket_valid():
    """
    Test create_basket() --happy path
    """
    true_data_path = project_path + "/" + test_conf['basket_data']
    true_df = pd.read_csv(true_data_path, dtype=str)

    test_df = create_basket(clean_df, **func_conf['create_basket'])
    test_df = test_df.reset_index()
    test_df = test_df.astype(str)

    assert np.array_equal(true_df.values, test_df.values)


def test_create_basket_invalid():
    """
    Test create_basket() --unhappy path
    """

    unhappy_df = clean_df.drop("StockCode", axis=1)

    with pytest.raises(KeyError):
        create_basket(unhappy_df, **func_conf['create_basket'])


def test_product_dim_valid():
    """
    Test product_dim() --happy path
    """
    true_data_path = project_path + "/" + test_conf['product_dim']
    true_df = pd.read_csv(true_data_path, dtype=str)

    test_df = product_dim(clean_df, **func_conf['product_dim'])
    test_df = test_df.astype(str)

    assert true_df.equals(test_df)


def test_product_dim_invalid():
    """
    Test product_dim() --unhappy path
    """

    unhappy_df = clean_df.drop("StockCode", axis=1)

    with pytest.raises(KeyError):
        product_dim(unhappy_df, **func_conf['product_dim'])


# Unit test for train
training_path = project_path + "/" + test_conf['training_data']
training_data = read_csv(training_path)
sample_train = training_data[['Invoice', '20725', '20724', '84946', '84970S', '85099B', '85123A']].head(20)


def test_get_support_valid():
    """
    Test get_support() --happy path
    """
    df = sample_train.set_index('Invoice')
    frequent_itemsets = get_support(df, func_conf['train']['apriori_args'])
    assert list(frequent_itemsets.columns) == ['support', 'itemsets'] and len(frequent_itemsets) >= 2


def test_get_support_invalid_1():
    """
    Test get_support() --unhappy path
    Wrong input DataFrame format
    """
    with pytest.raises(ValueError):
        get_support(sample_train, func_conf['train']['apriori_args'])


def test_get_support_invalid_2():
    """
    Test get_support() --unhappy path
    Raise value error if less than 2 items set returned.
    """
    with pytest.raises(ValueError):
        get_support(sample_train, test_conf['apriori_args'])


format_sample_train = sample_train.set_index('Invoice')
frequent_itemsets = get_support(format_sample_train, func_conf['train']['apriori_args'])


def test_get_popular_valid():
    """
    Test get_popular() --happy path
    """
    popular = get_popular(frequent_itemsets)
    assert type(popular) == list and len(popular) == 2


popular_list = get_popular(frequent_itemsets)


def test_get_recommendations_valid():
    """
    Test get_recommendations() --happy path
    """
    rules = get_recommendations(frequent_itemsets, **test_conf['get_recommendations_valid'])
    assert len(rules) >= 0 and {'antecedents', 'consequents', 'confidence'}.issubset(rules.columns)


def test_get_recommendations_invalid():
    """
    Test get_recommendations() --unhappy path
    raise Value error if not rules returned
    """
    with pytest.raises(ValueError):
        get_recommendations(frequent_itemsets, **test_conf['get_recommendations_invalid'])


rules = get_recommendations(frequent_itemsets, **test_conf['get_recommendations_valid'])


def test_frozenset2String_valid():
    """
    Test frozenset2String() --happy path
    """
    new_rules = frozenset2String(rules, test_conf['frozenset2String_valid'])
    assert sum([type(i) == str for i in new_rules['antecedents']])


def test_frozenset2String_invalid():
    """
    Test frozenset2String() --unhappy path
    invalid input
    """
    with pytest.raises(TypeError):
        frozenset2String(rules, test_conf['frozenset2String_invalid'])


rules = frozenset2String(rules, 'antecedents')
rules = frozenset2String(rules, 'consequents')


def test_pivot_rules_valid_1():
    """
    Test pivot_rules() --happy path1
    """
    new_rules = pivot_rules(rules, func_conf['train']['to_columns'])
    assert new_rules.shape[1] == 5 and list(new_rules.columns) == ['antecedents', 'rec1', 'rec2', 'conf1', 'conf2']


def test_pivot_rules_valid_2():
    """
    Test pivot_rules() --happy path2
    Test if no antecedents got a second recommendation, the return should still have five columns
    """
    new_rules = rules[rules['rank'] == 1]
    new_rules = pivot_rules(new_rules, func_conf['train']['to_columns'])
    assert new_rules.shape[1] == 5 and list(new_rules.columns) == ['antecedents', 'rec1', 'conf1', 'rec2', 'conf2']


def test_pivot_rules_invalid():
    """
    Test pivot_rules() --unhappy path
    invalid input
    """
    unhappy_rule = rules.drop("antecedents", axis=1)

    with pytest.raises(KeyError):
        pivot_rules(unhappy_rule, func_conf['train']['to_columns'])


rec = pivot_rules(rules, func_conf['train']['to_columns'])


def test_fill_no_rec_valid():
    """
    Test fill_no_rec() --happy path
    """
    full_rec = fill_no_rec(rec, popular_list)
    assert full_rec.isnull().sum().sum() == 0 and pd.Series(full_rec['rec1'] != full_rec['rec2']).all


def test_train_valid():
    """
    Test train() --happy path
    number of columns equals to product_num, one for each product. All products has two different recommendations
    """
    result = train(training_data, **func_conf['train'])

    assert len(result) == func_conf['create_basket']['product_num'] \
           and len(result['StockCode'].unique()) \
           and result.isnull().sum().sum() == 0

# Unit test fot evaluation


def test_accuracy_calculator_valid():
    """
    Test accuracy_calculator() --happy path
    """
    rec_path = project_path + "/" + test_conf['rec']
    test_data_path = project_path + "/" + test_conf['test_data']

    rec = read_csv(rec_path)
    test = read_csv(test_data_path)

    acc = accuracy_calculator(rec, test)

    assert acc.shape == (2, 3)
