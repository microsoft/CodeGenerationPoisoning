import os
import yaml

from pytest import fixture
from plutus.budget_manager.verify import (
    verify_project_yaml,
    verify_parent_yaml,
    verify_labels_yaml,
    verify_default_yaml,
)


@fixture
def config_dict():
    """Loads test configuration yaml file into dict."""

    test_config_file = os.path.join(os.path.dirname(__file__), "./files/config.yaml")
    with open(test_config_file, "r") as f:
        dict = yaml.load(f, Loader=yaml.SafeLoader)
        return dict


def test_verify_project_yaml(config_dict):
    assert verify_project_yaml(config_dict["good"]) is True
    assert verify_project_yaml(config_dict["missing_project_id"]) is False
    assert verify_project_yaml(config_dict["project_id_wrong_type"]) is False
    assert verify_project_yaml(config_dict["missing_budget_type"]) is False
    assert verify_project_yaml(config_dict["missing_budget_amount"]) is False
    assert verify_project_yaml(config_dict["missing_threshold_rules"]) is False
    assert verify_project_yaml(config_dict["missing_include_credits"]) is False
    assert verify_project_yaml(config_dict["missing_pubsub"]) is False
    assert verify_project_yaml(config_dict["user_configured_display_name"]) is False
    assert verify_project_yaml(config_dict["budget_type_wrong_type"]) is False
    assert verify_project_yaml(config_dict["budget_amount_wrong_type"]) is False
    assert verify_project_yaml(config_dict["pubsub_wrong_type"]) is False
    assert verify_project_yaml(config_dict["include_credits_wrong_type"]) is False
    assert verify_project_yaml(config_dict["budget_type_wrong_val"]) is False
    assert verify_project_yaml(config_dict["products_wrong_type"]) is False
    assert verify_project_yaml(config_dict["alert_emails_wrong_type"]) is False
    assert verify_project_yaml(config_dict["threshold_rules_wrong_type"]) is False
    assert (
        verify_project_yaml(config_dict["threshold_rules_invalid_spend_basis"]) is False
    )
    assert verify_project_yaml(config_dict["threshold_percent_wrong_type"]) is False
    assert (
        verify_project_yaml(config_dict["threshold_rules_invalid_list_object"]) is False
    )
    assert verify_project_yaml(config_dict["pubsub_topic_wrong_type"]) is False


def test_verify_parent_yaml(config_dict):
    assert verify_parent_yaml(config_dict["good_parent"]) is True
    assert verify_parent_yaml(config_dict["missing_parent_folder_id"]) is False
    assert verify_parent_yaml(config_dict["parent_folder_id_with_morekeys"]) is False


def test_verify_labels_yaml(config_dict):
    assert verify_labels_yaml(config_dict["good_labels"]) is True
    assert verify_labels_yaml(config_dict["missing_label_list"]) is False
    assert verify_labels_yaml(config_dict["label_list_wrong_type"]) is False
    assert verify_labels_yaml(config_dict["label_list_len"]) is True
    assert verify_labels_yaml(config_dict["label_list_obj_wrong_type"]) is False
    assert verify_labels_yaml(config_dict["label_list_obj_wrong_type2"]) is False


def test_verify_default_yaml(config_dict):
    assert verify_default_yaml(config_dict["good_default"]) is True
    assert verify_default_yaml(config_dict["configured_project_id"]) is False
    assert verify_default_yaml(config_dict["configured_parent_folder_id"]) is False
    assert verify_default_yaml(config_dict["configured_label_list"]) is False
