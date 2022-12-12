import csv

from Webservice.DBModels import Slot, Part
import yaml
import os


def get_demo_carriage_slot_list():
    file = '/demo_carriage.yml'
    path = os.path.dirname(os.path.realpath(__file__)) + file
    # print(path)
    f = open(path, 'r+')
    datamap = yaml.load(f)
    f.close()
    # print ( "dataMap is a ", type(datamap), datamap, "\n")
    return datamap


def get_demo_parts_big():
    file = '/demo_parts_big.yml'
    path = os.path.dirname(os.path.realpath(__file__)) + file
    # print(path)
    f = open(path, 'r+')
    datamap = yaml.load(f)
    f.close()
    # print ( "dataMap is a ", type(datamap), datamap, "\n")
    return datamap


def get_demo_parts_fail():
    file = '/demo_parts_fail.yml'
    path = os.path.dirname(os.path.realpath(__file__)) + file
    # print(path)
    f = open(path, 'r+')
    datamap = yaml.load(f)
    f.close()
    # print ( "dataMap is a ", type(datamap), datamap, "\n")
    return datamap


def get_demo_parts_medium():
    file = '/demo_parts_medium.yml'
    path = os.path.dirname(os.path.realpath(__file__)) + file
    # print(path)
    f = open(path, 'r+')
    datamap = yaml.load(f)
    f.close()
    # print ( "dataMap is a ", type(datamap), datamap, "\n")
    return datamap


def get_demo_parts_mixed():
    file = '/demo_parts_mixed.yml'
    path = os.path.dirname(os.path.realpath(__file__)) + file
    # print(path)
    f = open(path, 'r+')
    datamap = yaml.load(f)
    f.close()
    # print ( "dataMap is a ", type(datamap), datamap, "\n")
    return datamap


def get_demo_parts_small():
    file = '/demo_parts_small.yml'
    path = os.path.dirname(os.path.realpath(__file__)) + file
    # print(path)
    f = open(path, 'r+')
    datamap = yaml.load(f)
    f.close()
    # print ( "dataMap is a ", type(datamap), datamap, "\n")
    return datamap


def get_demo_parts_one_part():
    file = '/demo_parts_one_part.yml'
    path = os.path.dirname(os.path.realpath(__file__)) + file
    # print(path)
    f = open(path, 'r+')
    datamap = yaml.load(f)
    f.close()
    # print ( "dataMap is a ", type(datamap), datamap, "\n")
    return datamap


def get_demo_parts_partmapping():
    file = '/demo_parts_partmapping.yml'
    path = os.path.dirname(os.path.realpath(__file__)) + file
    # print(path)
    f = open(path, 'r+')
    datamap = yaml.load(f)
    f.close()
    # print ( "dataMap is a ", type(datamap), datamap, "\n")
    return datamap


class DBModelsDemoDataCarriage:

    @staticmethod
    def get_slot_list():
        ret_list = []
        datamap = get_demo_carriage_slot_list()
        for slot in datamap.values():
            ret_list.append(Slot(slot_name=slot['slot_name'],
                                 part_number=None,
                                 max_length=slot['max_length'],
                                 max_width=slot['max_width'],
                                 module_number=slot['module_number']))

        return ret_list

    # this method only for BestDistributeDemoCarriage
    @staticmethod
    def get_parts():
        ret_list = []
        datamap = get_demo_parts_big()
        # datamap = get_demo_parts_fail()
        # datamap = get_demo_parts_medium()
        # datamap = get_demo_parts_mixed()
        # datamap = get_demo_parts_small()
        # datamap = get_demo_parts_one_part()

        for part in datamap.values():
            ret_list.append(Part(part_number=part['part_number'],
                                 finished_length=part['finished_length'],
                                 finished_width=part['finished_width'],
                                 status='not_onboard'))

        return ret_list

    @staticmethod
    def get_parts_with_partmapping():
        ret_list = []
        datamap = get_demo_parts_partmapping()

        for part in datamap.values():
            ret_list.append(Part(part_number=part['part_number'],
                                 finished_length=part['finished_length'],
                                 finished_width=part['finished_width'],
                                 finished_thickness=part['finished_thickness'],
                                 status='not_onboard',
                                 part_mapping=part['part_mapping']))

        return ret_list

    @staticmethod
    def get_demo_parts_from_reference_sheet():
        file = '/P22_Referenzteile.CSV'
        # file ='/Referenzteile_part5.CSV'
        path = os.path.dirname(os.path.realpath(__file__)) + file
        ret_list = []
        with open(path, newline='\n', encoding='utf-8') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=';')
            for row in csv_reader:
                part = Part(part_number=int(row[0]),
                            finished_length=float(row[16].split(' x ')[0]),
                            finished_width=float(row[16].split(' x ')[1]),
                            finished_thickness=float(row[16].split(' x ')[2]),
                            description=row[9],
                            part_mapping=int(row[25]),
                            status='not_onboard')
                ret_list.append(part)

        return ret_list

    @staticmethod
    def get_part_scans():
        file = '/part_scans.yml'
        path = os.path.dirname(os.path.realpath(__file__)) + file
        f = open(path, 'r+')
        datamap = yaml.load(f)
        ret_dict = {}
        i = 0
        for part in datamap.values():
            local_dict = {
                "part_number": int(part['part_number']),
                "x": float(part['x']),
                "y": float(part['y']),
                "z": float(part['z']),
                "phi": float(part['phi'])
            }
            ret_dict[i] = local_dict
            i += 1
        return ret_dict
