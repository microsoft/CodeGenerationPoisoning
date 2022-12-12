from pathlib import Path
import re
import yaml

repo_dir = Path(__file__).parent.parent.parent.parent
resources_dir = repo_dir / 'resources'
# excel_path = resources_dir / 'Semio2Brain Database.xlsx'
semiology_dict_path = resources_dir / 'semiology_dictionary.yaml'

with open(semiology_dict_path) as f:
    SemioDict = yaml.load(f, Loader=yaml.FullLoader)


def custom_semiology_lookup(custom_semiology, nested_dict=SemioDict,
                            found=None) -> list:
    """
    User enters custom semiology. This checks if we already have a catch-all in taxonomy replacement SemioDict.
    Top level function will use this to find a match within SemioDict:
        semiology_exists_already = custom_semiology_lookup(custom_semiology, found=[])
        if not semiology_exists_already:
            pass
        elif len(semiology_exists_already) == 1:
            pop-up window("Note this custom semiology may already exist within the category {}".format(semiology_exists_already[0]))
        elif len(semiology_exists_already) > 1:
            pop-up window("Note this custom semiology term occurs in various ways within the following categories: {}".format(str(semiology_exists_already)))

    Alim-Marvasti 2020
    """
    found = [] if found is None else found
    for k, v in nested_dict.items():
        # look for matching keys only in top level
        if re.search(r'(?i)' + custom_semiology, k):
            found.append(k)
        elif re.search(r'(?i)' + k, custom_semiology):
            found.append(k)
        elif isinstance(v, list):
            for regex_item in v:
                if re.search(r'(?i)' + regex_item, custom_semiology):
                    found.append(k)
                if re.search(r'(?i)' + custom_semiology, regex_item):
                    found.append(k)
        elif isinstance(v, dict):
            # run it again to open nested dict values:
            custom_semiology_lookup(
                custom_semiology, nested_dict=v, found=found)
        else:  # single regex term in the value of the key
            if re.search(r'(?i)' + v, custom_semiology):
                found.append(k)
            if re.search(r'(?i)' + custom_semiology, v):
                found.append(k)

    return list(set(found))
