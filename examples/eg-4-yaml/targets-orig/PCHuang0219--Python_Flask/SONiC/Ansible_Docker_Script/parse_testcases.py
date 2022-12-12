import yaml
import sys
import json
import csv

testcases_yaml_file =  '/var/jlo/sonic-mgmt/ansible/roles/test/vars/testcases.yml'
csv_file = 'testcases.csv'

stream = open (testcases_yaml_file,'r')
testcases_list = []
dlist = yaml.safe_load(stream)
test_info_list = dlist["testcases"]

def return_testcases_list():
    for testcase in test_info_list:
        testcase_info = test_info_list[testcase]
        testcase_topo = testcase_info["topologies"]
        for topo in testcase_topo:
            if topo == 't0':
                topo = 'vms-t0'
                testcases_list.append({"Test Name":testcase,"Topology":topo})
            elif topo == 't1':
                topo = 'vms-t1'
                testcases_list.append({"Test Name":testcase,"Topology":topo})
            elif topo == 't1-lag':
                topo = 'vms-t1-lag'
                testcases_list.append({"Test Name":testcase,"Topology":topo})
            elif topo == 'ptf32':
                topo = 'ptf1-32'
                testcases_list.append({"Test Name":testcase,"Topology":topo})
    return testcases_list

def write_testcases_to_csv():
    testcases_list = return_testcases_list()
    with open(csv_file,'w') as csvfile :
        write = csv.writer(csvfile)
        write.writerow(["Test Case","Test Name","Topology"])
        previous_testcase = ''
        testcase_number = 0
        for testcase in testcases_list :
            if ( previous_testcase != testcase["Test Name"] ):
                testcase_number += 1
            testcase_code = 'TC' + "%03d" % testcase_number
            write.writerow([testcase_code,testcase["Test Name"],testcase["Topology"]])
            previous_testcase = testcase["Test Name"]

if __name__ == "__main__":
    write_testcases_to_csv()
