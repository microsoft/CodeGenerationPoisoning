#!/usr/bin/env python3
import urllib.request
import yaml
import sys

#This program takes in as an argument a reference to a yaml file. It will then scan through the file looking for
# #particular tags, and then upon finding those tags, replacing them with text from other yaml files of a given address

#This function accepts a file path to a yaml file and returns the contents of the yaml file as a dictionary
def input_from_yaml(inputfile):
    try:
        with open(inputfile) as file:
            yaml_template = yaml.load(file, Loader=yaml.FullLoader)
            return yaml_template
    except Exception as e:
        sys.stderr.write(str(e))
        sys.exit()
#This function accepts a url for a yaml file, and returns the contents of the yaml file in a python dictionary
def get_yaml_from_url(yaml_url):
    try:
        with urllib.request.urlopen(yaml_url) as urlfile:
            yaml_resource_file = yaml.load(urlfile, Loader=yaml.FullLoader)
            return yaml_resource_file
    except Exception as e:
        sys.stderr.write(str(e))
        sys.exit()
#This function accepts a python dictionary and outputs a yaml file to stdout.
def output_to_yaml():
    try:
        yaml.safe_dump(outputyaml, sys.stdout, allow_unicode=True, default_flow_style=False, sort_keys=False)
    except Exception as e:
        sys.stderr.write(str(e))
        sys.exit()
#This function takes in a strongly nested dictionary, then recursively traverses it looking for certain tags. It then replaces the tags with text from other files and then returns a new file.
def create_new_yaml(nested_dict):
    emptydict = {}
    for key, value in nested_dict.items():
        keystring = str(key)
        if keystring.startswith('X-replace')==False:
            if type(value) != dict:
                emptydict[key] = value
            if type(value) == dict:
                recursivevalue = create_new_yaml(value)
                if recursivevalue != "schema replaced" and recursivevalue !="enum replaced":
                    emptydict[key] = recursivevalue
                if recursivevalue == "schema replaced":
                    emptydict[key]=storagedict
                if recursivevalue =="enum replaced":
                    emptydict['enum'] = secondstorage.get('enum')
        if keystring.startswith('X-replace'):
            if keystring == 'X-replace-enum-list':
                yaml_url=str(value.get('enum-file-ref'))
                if yaml_url.startswith('http') == False:
                    yaml_obj = input_from_yaml(yaml_url)
                if yaml_url.startswith('http'):
                    yaml_obj = get_yaml_from_url(yaml_url)
                replaced_section = []
                for enumkey, enumvalue in yaml_obj.items():
                    replaced_section.append(enumkey)
                secondstorage['enum'] = replaced_section
                return "enum replaced"
            if keystring == 'X-replace-schema':
                yaml_url_list=(value.get('schema-file-ref'))
                for schemakey, schemavalue in emptydict.items():
                    storagedict[schemakey] = schemavalue
                for thisurl in yaml_url_list:
                    yaml_url = str(thisurl)
                    if yaml_url.startswith('http') == False:
                        yaml_obj = input_from_yaml(yaml_url)
                    if yaml_url.startswith('http'):
                        yaml_obj = get_yaml_from_url(yaml_url)
                    internalcall = create_new_yaml(yaml_obj)
                    for tempkey, tempvalue in internalcall.items():
                        storagedict[tempkey] = tempvalue
                return "schema replaced"
    return emptydict


# Running this python file as a script
# python3 -m general_schema_template_transformer <input_file>
if __name__ == "__main__":
    #Makes sure that there is at least one argument being passed to this program. If there is, the argument is assigned to a variable. input_from_yaml is then called with this variable as a parameter.
    try:
        input_file = sys.argv[1]
    except IndexError as e:
        msg = "Must pass in exactly 1 argument: the name of an existing file"
        sys.exit(msg)

    yaml_template = input_from_yaml(input_file)

    storagedict = {} #Instantiates a global dictionary. This provides temporary storage of dictionary elements to be used with create_new_yaml function
    secondstorage = {} #Instantiates a second global dictionary. This is only used for collecting enum lists to use at earlier loops through the recursive function
    outputyaml = create_new_yaml(yaml_template)
    output_to_yaml()
