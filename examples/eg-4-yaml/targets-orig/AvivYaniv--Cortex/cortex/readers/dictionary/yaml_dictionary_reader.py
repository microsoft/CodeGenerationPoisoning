import yaml

def yaml_file_to_dictionary_reader(f):
        dictionary = yaml.safe_load(f.read())
        return dictionary
    