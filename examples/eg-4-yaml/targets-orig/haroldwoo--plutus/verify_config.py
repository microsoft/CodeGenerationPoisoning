import sys
import yaml

from plutus.budget_manager.verify import (
    verify_project_yaml,
    verify_parent_yaml,
    verify_labels_yaml,
    # verify_default_yaml
)

# test config file for errors as a requirement for merging
with open(sys.argv[1], "r") as f:
    budget_dict = yaml.load(f, Loader=yaml.SafeLoader)

    for project_dict in budget_dict["projects"]:
        if verify_project_yaml(project_dict):
            pass
        else:
            print(f"Error validating {project_dict}.")
            sys.exit(1)

    for parent_dict in budget_dict["parent_folders"]:
        if verify_parent_yaml(parent_dict):
            pass
        else:
            print(f"Error validating {parent_dict}.")
            sys.exit(1)

    for label_dict in budget_dict["labels"]:
        if verify_labels_yaml(label_dict):
            pass
        else:
            print(f"Error validating {label_dict}.")
            sys.exit(1)

print("Config verification succeeded.")
