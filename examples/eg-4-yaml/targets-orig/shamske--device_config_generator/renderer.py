#!/bin/python
import yaml
from jinja2 import Template

def main():
    # open variables in YAML file, read the file, load the variables into variable called my_vars
    var_file = open("variables.yaml")
    var_data = var_file.read()
    my_vars = yaml.full_load(var_data)

    # open and read device template file that contains Jinja2 variables and store it in a variable called template
    template_file = open("template.j2")
    template_data = template_file.read()
    template = Template(template_data)

    # render the template for each device based on the YAML variables stored in my_vars. Write to file and save.
    for device in my_vars:
        outfile = open(device["HOSTNAME"] + ".conf", "w")
        outfile.write(template.render(device))
        outfile.close()

if __name__ == "__main__":
    main()