#!/usr/bin/env python
"""
Read my_file.yml and then write the data back out as a CSV file.
The output CSV file should be similar to following format:

------
device_name,device_type,host,username,password
pynet-rtr1,cisco_ios,184.105.247.70,pyclass,my_pass
------

"""
from __future__ import print_function
from __future__ import unicode_literals
import csv
import yaml


def main():
    """Read my_file.yml and then write the data back out as a CSV file."""
    yaml_file = "my_file.yml"
    csv_file = "write_net_devices.csv"

    with open(yaml_file) as f:
        output = yaml.load(f)

    with open(csv_file, "wt") as f:
        writer = csv.writer(f)
        writer.writerow(("device_name", "device_type", "host", "username", "password"))
        for device in output:
            print(device)
            writer.writerow(
                (
                    device["device_name"],
                    device["device_type"],
                    device["host"],
                    device["username"],
                    device["password"],
                )
            )


if __name__ == "__main__":
    main()
