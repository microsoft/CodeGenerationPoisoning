from __future__ import division, print_function
import pyTFM
import shutil
from pyTFM.TFM_functions_for_clickpoints import *  # must be on top because of some matplotlib backend issues
from pyTFM.parameters_and_strings import tooltips, default_parameters, convert_config_input, default_search_keys
from pyTFM.database_functions import *


import importlib
import os
import sys
from functools import partial
from qtpy import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QSettings
import qtawesome as qta
import clickpoints
import traceback
import asyncio
import yaml

import warnings

warnings.simplefilter(action='ignore', category=RuntimeWarning)


class ConfigError(Exception):
    def __init__(self, message=None, path=None):
        self.final_message = ""
        if isinstance(message, str):
            self.message = message
            self.final_message = self.final_message + message
        if isinstance(path, str):
            self.path = path
            self.final_message = self.final_message + "\npath: " + path

    def __str__(self):
        if self.message:
            return self.final_message
        else:
            return "reading config file failed"


def load_config(file_path, parameters):
    try:
        with open(file_path, "r") as f:
            c = yaml.safe_load(f)
        if "analysis_parameters" in c.keys():  # behold the ugliest piece of code ever
            for k, v in c["analysis_parameters"].items():
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        if isinstance(v2, dict):
                            for k3, v3 in v2.items():
                                nv = convert_config_input(v3, k3)
                                parameters[k][k2][k3] = nv
                                print("setting", "analysis_parameters", k, k2, k3, "to", nv)
                        else:
                            nv = convert_config_input(v2, k2)
                            parameters[k][k2] = nv
                            print("setting", "analysis_parameters", k, k2, "to", nv)
                else:
                    nv = convert_config_input(v, k)
                    parameters[k] = nv
                    print("setting", "analysis_parameters", k, "to", nv)
        # adding to subdict "fig parameters in parameters
        if "fig_parameters" in c.keys():
            for k, v in c["fig_parameters"].items():  # first layer would be applied to all plots
                if isinstance(v, dict):
                    for k2, v2 in v.items():  # second layer would be applied for specific plot types
                        if isinstance(v2, dict):
                            for k3, v3 in v2.items():  # third layer currently not used
                                nv = convert_config_input(v3, k3)
                                parameters["fig_parameters"][k][k2][k3] = nv
                                print("setting", "fig_parameters", k, k2, k3, "to", nv)
                        else:
                            nv = convert_config_input(v2, k2)
                            parameters["fig_parameters"][k][k2] = nv
                            print("setting", "fig_parameters", k, k2, "to", nv)
                else:
                    nv = convert_config_input(v, k)
                    parameters["fig_parameters"][k] = defaultdict(
                        lambda value=nv: value)  # needs to be defaultdict to work for all plot types
                    print("setting", "fig_parameters", k, "to", nv)

    except Exception as e:
        traceback.print_exc()
        # raise ConfigError("reading config file failed",path=file_path)
        print("reading config file failed\n", "path: " + file_path)

    return parameters


def add_parameter_from_list(labels, dict_keys, default_parameters, layout, grid_line_start, con_func):

    params = {}
    param_labels = {}
    for i, (label, dict_key) in enumerate(zip(labels, dict_keys)):
        p = QtWidgets.QLineEdit()  # box to enter number
        p.setFixedWidth(120)
        p.setText(str(default_parameters[dict_key]))
        p.setToolTip(tooltips[dict_key])
        p.textChanged.connect(con_func)
        p_l = QtWidgets.QLabel()  # text
        p_l.setText(label)
        layout.addWidget(p, grid_line_start + i, 1)  # adding to layout
        layout.addWidget(p_l, grid_line_start + i, 0)
        params[dict_key] = p
        param_labels[dict_key] = p_l
    last_line = grid_line_start + i
    return params, param_labels, last_line


def read_all_paramters(parameter_widgets, parameter_dict):
    for p_name, p_widget in parameter_widgets.items():
        if isinstance(p_widget, QtWidgets.QLineEdit):
            if p_widget.text() != "":
                parameter_dict[p_name] = float(p_widget.text())
        if isinstance(p_widget, QtWidgets.QComboBox):
            parameter_dict[p_name] = p_widget.currentText()

    return parameter_dict


def print_parameters(parameters):  # printing only selected parts of the parameter dict
    print("paramters:\n")
    for key, value in parameters.items():
        if key not in ["mask_properties", "FEM_mode_id", "fig_parameters", "cv_pad"]:
            print(key, ": ", value)


def print_db_info(db_info):  # printing only selected parts of the db_info dict
    print("image information:\n")
    for key, value in db_info.items():
        if key not in ["id_frame_dict", "cbd_frames_ref_dict", "file_order"]:
            print(key, ": ", value)


class SegSlider(QtWidgets.QWidget):
    def __init__(self, main_window):
        super(SegSlider, self).__init__()
        self.im_filter_membrane = None
        self.im_filter_area = None

        self._new_window = None
        self.setMinimumWidth(600)
        self.setMinimumHeight(100)
        self.main_window = main_window
        self.setWindowTitle("segmentation")

        # button to cover the whole image with a mask
        self.cover_area = QtWidgets.QPushButton("mark entire image")
        self.cover_area.setToolTip(tooltips["mark entire image"])
        self.cover_area.clicked.connect(self.cover_entire_image)
        # drop down menu to select the mask type
        self.mask_type = QtWidgets.QComboBox()
        names = [m.name for m in self.main_window.db.getMaskTypes()]
        if names[0] == "membrane":
            names.insert(-1, names.pop(0))
        self.mask_type.addItems(names)
        self.mask_type.setToolTip(tooltips["select mask segmentation"])
        # drop down menu to switch between encircling the entire image or filling the entire image
        # the latter would delete every other mask
        self.fill_mode = QtWidgets.QComboBox()
        self.fill_mode.addItems(["encircle image", "fill out image"])
        self.fill_mode.setToolTip(tooltips["fill_mode"])

        self.fill_hbox = QtWidgets.QHBoxLayout()
        self.fill_hbox.addWidget(self.mask_type, QtCore.Qt.AlignLeft)
        self.fill_hbox.addWidget(self.fill_mode, QtCore.Qt.AlignLeft)
        self.fill_hbox.addStretch(2)

        # button for simple segmentation of cell area when in colony mode
        self.button_seg_area = QtWidgets.QPushButton("segment cell area")
        self.button_seg_area.setToolTip(tooltips["segmentation_area"])
        self.button_seg_area.clicked.connect(
            partial(self.segmentation, self.main_window.all_frames, seg_type="cell_area"))  # update parameters

        # button for simple segmentation of membrane
        self.button_seg_mem = QtWidgets.QPushButton("segment membrane")
        self.button_seg_mem.setToolTip(tooltips["segmentation_membrane"])
        self.button_seg_mem.clicked.connect(
            partial(self.segmentation, self.main_window.all_frames, seg_type="membrane"))  # update parameters
        # slider1
        self.slider_area = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_area.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.slider_area.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.slider_area.setToolTip(tooltips["segmentation_area"])
        self.im_filter_area = gaussian_filter(self.main_window.db.getImage(
            id=self.main_window.db_info["file_order"][main_window.frame + "membranes"]).data, sigma=10)
        max_area = np.max(self.im_filter_area)
        min_area = np.min(self.im_filter_area)
        step_size_area = (max_area - min_area) / 100
        self.slider_area.setMinimum(min_area)
        self.slider_area.setMaximum(max_area)
        self.slider_area.setSingleStep(step_size_area)
        self.slider_area.valueChanged.connect(
            partial(self.segmentation_single, frames=self.main_window.frame, seg_type="cell_area"))
        slider_area_vbox = QtWidgets.QVBoxLayout()
        slider_area_hbox = QtWidgets.QHBoxLayout()
        slider_area_hbox.setContentsMargins(0, 0, 0, 0)
        slider_area_vbox.setContentsMargins(0, 0, 0, 0)
        slider_area_vbox.setSpacing(0)
        label_minimum_area = QtWidgets.QLabel(str(int(min_area)), alignment=QtCore.Qt.AlignLeft)
        label_maximum_area = QtWidgets.QLabel(str(int(max_area)), alignment=QtCore.Qt.AlignRight)
        label_value_area = QtWidgets.QLabel(str(self.slider_area.value()), alignment=QtCore.Qt.AlignCenter)
        self.slider_area.valueChanged.connect(label_value_area.setNum)  # this actually works!!
        slider_area_vbox.addWidget(self.slider_area)
        slider_area_vbox.addLayout(slider_area_hbox)
        slider_area_hbox.addWidget(label_minimum_area, QtCore.Qt.AlignLeft)
        slider_area_hbox.addWidget(label_value_area, QtCore.Qt.AlignCenter)
        slider_area_hbox.addWidget(label_maximum_area, QtCore.Qt.AlignRight)

        # slider2
        self.slider_mem = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_mem.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.slider_mem.setTickPosition(QtWidgets.QSlider.TicksBelow)
        im = self.main_window.db.getImage(
            id=self.main_window.db_info["file_order"][main_window.frame + "membranes"]).data.astype(float)
        self.im_filter_membrane = gaussian_filter(im, sigma=2) - gaussian_filter(im, sigma=10)
        max_mem = np.max(self.im_filter_membrane)
        min_mem = np.min(self.im_filter_membrane)
        step_size_mem = (max_mem - min_mem) / 200
        self.slider_mem.setMinimum(min_mem)
        self.slider_mem.setMaximum(max_mem)
        self.slider_mem.setSingleStep(1)  # only takes int??
        self.slider_mem.setTickInterval(2)  # only takes int??
        self.slider_mem.valueChanged.connect(
            partial(self.segmentation_single, frames=self.main_window.frame, seg_type="membrane"))
        self.slider_mem.setToolTip(tooltips["segmentation_membrane"])
        slider_mem_vbox = QtWidgets.QVBoxLayout()
        slider_mem_hbox = QtWidgets.QHBoxLayout()
        slider_mem_hbox.setContentsMargins(0, 0, 0, 0)
        slider_mem_vbox.setContentsMargins(0, 0, 0, 0)
        slider_mem_vbox.setSpacing(0)
        label_minimum_mem = QtWidgets.QLabel(str(int(min_mem)), alignment=QtCore.Qt.AlignLeft)
        label_maximum_mem = QtWidgets.QLabel(str(int(max_mem)), alignment=QtCore.Qt.AlignRight)
        label_value_mem = QtWidgets.QLabel(str(self.slider_mem.value()), alignment=QtCore.Qt.AlignCenter)
        self.slider_mem.valueChanged.connect(label_value_mem.setNum)
        slider_mem_vbox.addWidget(self.slider_mem)
        slider_mem_vbox.addLayout(slider_mem_hbox)
        slider_mem_hbox.addWidget(label_minimum_mem, QtCore.Qt.AlignLeft)
        slider_mem_hbox.addWidget(label_value_mem, QtCore.Qt.AlignCenter)
        slider_mem_hbox.addWidget(label_maximum_mem, QtCore.Qt.AlignRight)

        grid = QtWidgets.QGridLayout(self)
        grid.setColumnStretch(0,1)
        grid.setColumnStretch(1,2)
        grid.addWidget(self.button_seg_area, 0, 0)
        grid.addLayout(slider_area_vbox, 0, 1)
        grid.addWidget(self.button_seg_mem, 1, 0)
        grid.addLayout(slider_mem_vbox, 1, 1)
        grid.addWidget(self.cover_area, 3, 0)
        grid.addLayout(self.fill_hbox, 3, 1)


    def segmentation(self, frames="", seg_type="cell_area"):
        if seg_type == "cell_area":
            seg_threshold = self.slider_area.value()
        if seg_type == "membrane":
            seg_threshold = self.slider_mem.value()
        self.main_window.db_info, self.main_window.masks, self.main_window.res_dict = apply_to_frames(
            self.main_window.db,
            self.main_window.parameter_dict, analysis_function=simple_segmentation, masks=self.main_window.masks,
            leave_basics=True,
            res_dict=self.main_window.res_dict, frames=frames, db_info=self.main_window.db_info,
            seg_threshold=seg_threshold, seg_type=seg_type)
        self.main_window.cp.reloadMask()

    def segmentation_single(self, frames="", seg_type="cell_area"):
        if seg_type == "cell_area":
            seg_threshold = self.slider_area.value()
            self.im_filter_area = simple_segmentation(frames, self.main_window.parameter_dict,
                                                      self.main_window.res_dict,
                                                      self.main_window.db, self.main_window.db_info,
                                                      seg_threshold=seg_threshold,
                                                      seg_type=seg_type, im_filter=self.im_filter_area)
        if seg_type == "membrane":
            seg_threshold = self.slider_mem.value()
            print(type(self.im_filter_membrane))
            self.im_filter_membrane = simple_segmentation(frames, self.main_window.parameter_dict,
                                                          self.main_window.res_dict, self.main_window.db,
                                                          self.main_window.db_info,
                                                          seg_threshold=seg_threshold, seg_type=seg_type,
                                                          im_filter=self.im_filter_membrane)

        self.main_window.cp.reloadMask()

    def cover_entire_image(self):
        mt = self.mask_type.currentText()
        mode = self.fill_mode.currentText()
        if mode == "fill out image":
            choice = QtWidgets.QMessageBox.question(self, 'continue',
                                                    "This override all existing masks.",
                                                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if choice == QtWidgets.QMessageBox.No:
                return
        apply_to_frames( self.main_window.db, self.main_window.parameter_dict, analysis_function=cover_entire_image_with_mask,
                         masks=self.main_window.masks, leave_basics=True,  res_dict=self.main_window.res_dict,
                         frames=self.main_window.all_frames, db_info=self.main_window.db_info, mask_type=mt, mode=mode)
        self.main_window.cp.reloadMask()


class FileSelectWindow(QtWidgets.QWidget):
    def __init__(self, main_window):
        super(FileSelectWindow, self).__init__()
        self._new_window = None


        self.setStyleSheet("""
                QPushButton#collect_images {background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 #f6f7fa, stop: 1 #dadbde)}
                QLabel#text_file_selection {font-size:10pt;font-weight: bold}
                QLabel#text_output_options {font-size:10pt;font-weight: bold}
                """)
        self.setWindowTitle("image selection")
        self.setMinimumWidth(600)
        self.setMinimumHeight(300)
        self.main_window = main_window
        self.main_window.outfile_path = os.path.join(os.getcwd(), "out.txt")

        # check if clickpoints file is temporary file
        if re.match("tmp\d*\.cdb", os.path.split(self.main_window.db._database_filename)[1]):
            self.db_name = "database.cdb"
        else:
            self.db_name = self.main_window.db._database_filename  # if not use current filename as default filename
        self.cwd = os.getcwd()
        self.default_folder = self.cwd
        self.folders = {"folder_after": self.cwd,
                        "folder_before": self.cwd,
                        "folder_cells": self.cwd,
                        "folder_out": self.cwd}
        self.search_keys = default_search_keys
        # updating according to qt settings
        for key in self.search_keys.keys():
            if not self.main_window.settings.value(key) is None:
                self.search_keys[key] = main_window.settings.value(key)


        self.layout = QtWidgets.QGridLayout()
        self.layout.setColumnStretch(0, 8)
        self.layout.setColumnStretch(1, 1)
        self.layout.setColumnStretch(2, 6)
        self.layout.setRowMinimumHeight(4, 40)

        self.sub_v_layout = defaultdict(QtWidgets.QVBoxLayout)
        self.sub_h_layout = defaultdict(QtWidgets.QHBoxLayout)
        self.objects = {
            "folder_after": {"object": None,
                             "properties": [1, 0, None, 20, None, "textChanged", self.update_dirs, QtWidgets.QLineEdit,
                                            self.cwd]},
            "folder_before": {"object": None,
                              "properties": [2, 0, None, 20, None, "textChanged", self.update_dirs, QtWidgets.QLineEdit,
                                             self.cwd]},
            "folder_cells": {"object": None,
                             "properties": [3, 0, None, 20, None, "textChanged", self.update_dirs, QtWidgets.QLineEdit,
                                            self.cwd]},

            "folder_after_button": {"object": None,
                                    "properties": [1, 1, 30, 80, QtCore.Qt.AlignLeft, "clicked", self.file_dialog,
                                                   QtWidgets.QPushButton, "..."]},
            "folder_before_button": {"object": None,
                                     "properties": [2, 1, 30, 80, QtCore.Qt.AlignLeft, "clicked", self.file_dialog,
                                                    QtWidgets.QPushButton, "..."]},
            "folder_cells_button": {"object": None,
                                    "properties": [3, 1, 30, 80, QtCore.Qt.AlignLeft, "clicked", self.file_dialog,
                                                   QtWidgets.QPushButton, "..."]},

            "folder_out": {"object": None,
                           "properties": [6, 0, None, 20, None, "textChanged", self.update_dirs, QtWidgets.QLineEdit,
                                          self.cwd]},
            "db_name_text": {"object": None,
                             "properties": [6, 2, None, 20, None, "textChanged", self.update_dirs, QtWidgets.QLineEdit,
                                            self.db_name]},
            "folder_out_button": {"object": None,
                                  "properties": [6, 1, 30, 20, QtCore.Qt.AlignLeft, "clicked", self.file_dialog,
                                                 QtWidgets.QPushButton, "..."]},
            "after": {"object": None,
                      "properties": [1, 2, 200, 30, None, "textChanged", self.update_dirs, QtWidgets.QLineEdit,
                                     "default"]},
            "before": {"object": None,
                       "properties": [2, 2, 200, 30, None, "textChanged", self.update_dirs, QtWidgets.QLineEdit,
                                      "default"]},
            "cells": {"object": None,
                      "properties": [3, 2, 200, 30, None, "textChanged", self.update_dirs, QtWidgets.QLineEdit,
                                     "default"]},
            "frames": {"object": None,
                       "properties": [4, 2, 200, 30, None, "textChanged", self.update_dirs, QtWidgets.QLineEdit,
                                      "default"]},

            "text_file_selection": {"object": None,
                                    "properties": [0, 0, None, 0, QtCore.Qt.AlignLeft, None, self.update_dirs,
                                                   QtWidgets.QLabel, "select image files"]},
            "text_output_options": {"object": None,
                                    "properties": [5, 0, None, 0, QtCore.Qt.AlignLeft, None, self.update_dirs,
                                                   QtWidgets.QLabel, "select output folder and database name"]}
        }

        self.texts = {
            "folder_out": {"object": None, "properties": [0, 0, "output folder"]},
            "folder_after": {"object": None, "properties": [0, 0, "images after cell removal"]},
            "folder_before": {"object": None, "properties": [0, 0, "images before cell removal"]},
            "folder_cells": {"object": None, "properties": [0, 0, "images cells"]},
            "db_name_text": {"object": None, "properties": [0, 0, "database name"]},
            "folder_out_button": {"object": None, "properties": [0, 0, ""]},
            "folder_after_button": {"object": None, "properties": [0, 0, ""]},
            "folder_before_button": {"object": None, "properties": [0, 0, ""]},
            "folder_cells_button": {"object": None, "properties": [0, 0, ""]},
            "after": {"object": None, "properties": [0, 0, "'after' image identifier"]},
            "before": {"object": None, "properties": [0, 0, "'before' image identifier"]},
            "cells": {"object": None, "properties": [0, 0, "cell image identifier"]},
            "frames": {"object": None, "properties": [0, 0, "frame identifier"]}}

        for name in self.texts.keys():
            self.add_text(name, *self.texts[name]["properties"])
        for name in self.objects.keys():
            self.add_object(name, *self.objects[name]["properties"])

        # adding the start button
        self.super_layout = QtWidgets.QGridLayout(self)
        self.super_layout.addLayout(self.layout, 0, 0)
        self.Spacer1 = QtWidgets.QSpacerItem(50, 50)
        self.super_layout.addItem(self.Spacer1, 1, 0)
        self.collect_button = QtWidgets.QPushButton("collect images")
        self.collect_button.clicked.connect(self.collect_files)
        self.collect_button.setObjectName("collect_images")
        self.collect_button.setToolTip(tooltips["collect_button"])
        self.super_layout.addWidget(self.collect_button, 2, 0, alignment=QtCore.Qt.AlignLeft)
        self.super_layout.setRowStretch(12, 1)

    def add_text(self, name, vpos, hpos, string):
        self.texts[name]["object"] = QtWidgets.QLabel(string)
        self.sub_v_layout[name].addStretch()
        self.sub_v_layout[name].addWidget(self.texts[name]["object"])  # adds to sub gid layout

    def add_object(self, name, vpos, hpos, m_width, s_width, alignment, connect_type, connect_function, type, text):
        text = self.search_keys[name] if text == "default" else text
        self.objects[name]["object"] = type(text)  # creates widget with text as label
        self.objects[name]["object"].setObjectName(name)
        if connect_function and connect_type:
            getattr(self.objects[name]["object"], connect_type).connect(
                partial(connect_function, name))  # connects to function
        self.objects[name]["object"].setToolTip(tooltips[name])  # sets tooltip
        if m_width:
            self.objects[name]["object"].setMaximumWidth(m_width)
        if alignment:
            self.sub_v_layout[name].addWidget(self.objects[name]["object"],
                                              alignment=alignment)  # generates new grid layout
        else:
            self.sub_v_layout[name].addWidget(self.objects[name]["object"])
        self.sub_h_layout[name].addLayout(self.sub_v_layout[name])  # generates new horizontal layout
        self.sub_h_layout[name].addSpacing(s_width)  # adds spacing on the right
        self.layout.addLayout(self.sub_h_layout[name], vpos, hpos)  # adds to main grid layout

    # additional file selectors
    def file_dialog(self, button_name):
        dialog = QtWidgets.QFileDialog()
        dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
        dialog.setDirectory(self.default_folder)
        if dialog.exec_():
            dirname = dialog.selectedFiles()
            text_field = self.objects[button_name[:-7]]["object"]
            text_field.setText(dirname[0])
            self.default_folder = os.path.split(dirname[0])[0]
        self.update_dirs()

    def update_dirs(self, *args):
        # updating the selected folders and search keys
        self.folders = {key: self.objects[key]["object"].text() for key in self.folders.keys()}
        # replace "none" if necessary
        self.folders = {key: convert_none_str(value) for key, value in self.folders.items()}

        self.search_keys = {key: self.objects[key]["object"].text() for key in self.search_keys.keys()}
        # replace "none" if necessary
        self.search_keys = {key: convert_none_str(value) for key, value in self.search_keys.items()}
        self.db_name = self.objects["db_name_text"]["object"].text()

    def collect_files(self):

        for key, value in self.search_keys.items():
            self.main_window.settings.setValue(key,value)
        self.main_window.settings.sync()

        filename = os.path.join(self.folders["folder_out"], self.db_name)
        old_filename = self.main_window.db._database_filename
        if os.path.exists(filename):
            choice = QtWidgets.QMessageBox.question(self, 'continue',
                                                    "Database file already exists. Do you want to override it?",
                                                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if choice == QtWidgets.QMessageBox.No:
                return

        # saving database to new location. If existing database is overwritten this does nothing.
        self.save_data_base(filename, old_filename)

        # clearing database
        self.main_window.db.deleteImages()  # delete existing images
        self.main_window.db.deleteLayers()  # delete existing layers
        self.main_window.db.deletePaths()  # removes existing paths

        # searching,sorting and adding new images// also updating the options
        setup_database_internal(self.main_window.db, self.search_keys, self.folders)  # sort in images

        # update output folder
        self.main_window.outfile_path = os.path.join(self.folders["folder_out"], "out.txt")
        self.main_window.db._AddOption(key="folder", value=self.folders["folder_out"])
        self.folder = self.main_window.db.setOption("folder", self.folders["folder_out"])

        # update db info
        self.main_window.db_info, self.main_window.all_frames = get_db_info_for_analysis(self.main_window.db)
        # resetting res dict and masks just to be sure
        self.main_window.res_dict = defaultdict(lambda: defaultdict(list))
        self.main_window.masks = None
        # reinitialise masks (deletes the old masks)
        setup_mask_wrapper(self, self.main_window.db, self.main_window.db_info, self.main_window.parameter_dict,
                           delete_all=True, warn_popup=False)


        # reading config
        config_path = os.path.join(self.folders["folder_out"], "config.yaml")
        # trying to read config:
        if os.path.exists(config_path):
            print("found exsisting config at ", config_path)
            self.main_window.config_path = config_path
            self.main_window.parameter_dict = load_config(config_path, self.main_window.parameter_dict)

        # reloading all displayed images
        self.main_window.reload_all()

        print( self.main_window.db_info["frames_ref_dict"])  ## reduce the output here...
        self.main_window.cp.updateImageCount()  # reload the image bar
        # reloading the Masktypes
        self.main_window.cp.reloadMaskTypes()

    def save_data_base(self, new_filename, old_filename):
        '''
        saving the clickpoints database to another locations.
        This is somewhat complicated by issues when there are paths defined in the database.
        :param new_filename:
        :param old_filename:
        :return:
        '''
        # save database to target
        if not new_filename == old_filename:
            # copying original database to temporary file:
            # shutil.copy(old_filename, old_filename + "_tmp")
           # self.main_window.db.deletePaths()  # removes existing paths
            print("saved database to " + new_filename)
            self.main_window.cp.window.SaveDatabase(srcpath=new_filename)

            # restore paths in older database file
           # if os.path.exists(old_filename + "-shm"):
           #     os.remove(old_filename + "-shm")
           # if os.path.exists(old_filename + "-wal"):
           #     os.remove(old_filename + "-wal")
            # os.remove(old_filename)
           # shutil.move(old_filename + "_tmp", old_filename)


class Addon(clickpoints.Addon):

    def __init__(self, *args, **kwargs):

        clickpoints.Addon.__init__(self, *args, **kwargs)

        self.frame_number = except_error(self.db.getImageCount, TypeError, print_error=False, return_v=None)
        # information about the path, image dimensions
        self.db_info, self.all_frames = get_db_info_for_analysis(self.db)
        print_db_info(self.db_info)

        self.res_dict = defaultdict(list)  # dictionary that catches all results
        self.masks = None
        self.parameter_dict = copy.deepcopy(default_parameters)  # loading default parameters
        self.read_or_set_options()  # reading the database folder and the previous FEM_mode, or fill in default values
        self.outfile_path = os.path.join(self.folder, "out.txt")  # path for output text file
        self.config_path = os.path.join(self.folder, "config.yaml")

        # loading some default settings
        if os.path.exists(self.config_path):
            print("found config at", self.config_path)
            self.parameter_dict = load_config(self.config_path, self.parameter_dict)
        # QT settings overwrite "default_parameters"
        # reading Qt settings file
        # on linux this file is saved at /home/user/.config/pyTFM
        self.settings = QSettings("pyTFM", "pyTFM")
        for key in self.parameter_dict.keys():
            if not self.settings.value(key) is None:
                self.parameter_dict[key] = self.settings.value(key)

        # TODO: consider to save settings in each database separately

        """ GUI Widgets"""
        # set the title and layout
        self.setWindowTitle("pyTFM" + "-" + pyTFM.__version__)
        self.setWindowIcon(qta.icon("fa.compress"))
        self.setMinimumWidth(400)
        self.setMinimumHeight(200)
        self.layout = QtWidgets.QGridLayout(self)
        self.layout.setColumnMinimumWidth(0, 150)

        # button to start calculation
        self.button_start = QtWidgets.QPushButton("start")
        self.button_start.clicked.connect(partial(self.start_thread, run_function=self.start))
        self.button_start.setToolTip(tooltips["button_start"])
        self.layout.addWidget(self.button_start, 0, 0)

        # button to select images:
        self.button_select_images = QtWidgets.QPushButton("image selection")
        self.button_select_images.clicked.connect(self.select_images)
        self.button_select_images.setToolTip(tooltips["image selection"])
        self.sub_layout1 = QtWidgets.QHBoxLayout()
        self.sub_layout1.addWidget(self.button_select_images)
        self.sub_layout1.addStretch()
        self.layout.addLayout(self.sub_layout1, 1, 0)

        # button to apply drift correction:
        self.correct_drift = QtWidgets.QPushButton("correct drift")
        self.correct_drift.clicked.connect(partial(self.start_thread, run_function=self.drift_correction))
        self.correct_drift.setToolTip(tooltips["correct drift"])
        self.sub_layout2 = QtWidgets.QHBoxLayout()
        self.sub_layout2.addWidget(self.correct_drift)
        self.sub_layout2.addStretch()
        self.layout.addLayout(self.sub_layout2, 2, 0)

        # check_boxes
        self.check_box_def = QtWidgets.QCheckBox("deformation")
        self.check_box_tra = QtWidgets.QCheckBox("traction forces")
        self.check_box_FEM = QtWidgets.QCheckBox("stress analysis")
        self.check_box_contract = QtWidgets.QCheckBox("force generation")

        self.check_box_def.setToolTip(tooltips["check_box_def"])
        self.check_box_tra.setToolTip(tooltips["check_box_tra"])
        self.check_box_FEM.setToolTip(tooltips["check_box_FEM"])
        self.check_box_contract.setToolTip(tooltips["check_box_contract"])

        self.layout.addWidget(self.check_box_def, 0, 1)
        self.layout.addWidget(self.check_box_tra, 1, 1)
        self.layout.addWidget(self.check_box_FEM, 2, 1)
        self.layout.addWidget(self.check_box_contract, 3, 1)

        # a gap
        self.layout.setRowMinimumHeight(4, 20)

        # # choosing single or all frames
        self.analysis_mode = QtWidgets.QComboBox()
        self.analysis_mode.addItems(["current frame", "all frames"])
        self.analysis_mode.setToolTip(tooltips["apply to"])
        self.layout.addWidget(self.analysis_mode, 5, 1)
        self.analysis_mode_descript = QtWidgets.QLabel()
        self.analysis_mode_descript.setText("apply to")
        self.layout.addWidget(self.analysis_mode_descript, 5, 0)

        # parameters
        self.parameter_labels = ["Youngs modulus [Pa]", "Poisson's ratio", "pixel size [µm]", "PIV overlap [µm]",
                                 "PIV window size [µm]", "gel height [µm]"]
        self.param_dict_keys = ["young", "sigma", "pixelsize", "overlap", "window_size", "h"]
        self.parameter_widgets, self.parameter_lables, last_line = add_parameter_from_list(self.parameter_labels,
                                                                                           self.param_dict_keys,
                                                                                           self.parameter_dict,
                                                                                           self.layout,
                                                                                           6, self.parameters_changed)

        # adding to layout
        self.setLayout(self.layout)
        self.parameters_changed()  # initialize parameters dict

        # choosing type of cell system
        self.colony_type = QtWidgets.QComboBox()
        self.colony_type.addItems(["colony", "cell layer"])
        self.colony_type.setToolTip(tooltips["switch mode"])
        self.colony_type.setCurrentIndex(self.parameter_dict["FEM_mode_id"])
        # update parameters
        self.colony_type.currentTextChanged.connect(self.parameters_changed)
        # switch between cell layer and colony mode
        self.colony_type.currentTextChanged.connect(self.switch_colony_type_mode)
        self.parameter_widgets["FEM_mode"] = self.colony_type  # adding to parameters dict
        self.parameter_lables["FEM_mode"] = ""  # label
        self.sub_layout3 = QtWidgets.QHBoxLayout()
        self.sub_layout3.addWidget(self.colony_type)

        # button for simple segmentation of membranes and cell area
        self.button_seg = QtWidgets.QPushButton("segmentation")
        self.button_seg.setToolTip(tooltips["segmentation"])
        self.button_seg.clicked.connect(self.segmentation)  # update parameters
        self.sub_layout3.addWidget(self.button_seg)
        self.sub_layout3.addStretch()
        self.layout.addLayout(self.sub_layout3, 3, 0)

    def read_or_set_options(self):
        self.folder = get_option_wrapper(self.db, "folder", unpack_funct=None, empty_return=lambda: "")
        if self.folder == "":
            self.folder = os.getcwd()
            self.db._AddOption(key="folder", value=self.folder)
            self.db.setOption(key="folder", value=self.folder)
        self.parameter_dict["FEM_mode"] = get_option_wrapper(self.db, "FEM_mode", empty_return=lambda: "")
        if self.parameter_dict["FEM_mode"] == "":
            self.parameter_dict["FEM_mode"] = default_parameters["FEM_mode"]
            self.db._AddOption(key="FEM_mode", value=self.parameter_dict["FEM_mode"])
            self.db.setOption(key="FEM_mode", value=self.parameter_dict["FEM_mode"])
        self.parameter_dict["FEM_mode_id"] = 0 if self.parameter_dict["FEM_mode"] == "colony" else 1

    def select_images(self):  # for what do i need this??
        self._new_window = FileSelectWindow(self)
        self._new_window.show()

    def reload_all(self):  # reloading entire display ## could be optimized
        sys.stdout = open(os.devnull, 'w')
        for frame in self.db_info["cbd_frames_ref_dict"].keys():
            for layer in self.db_info["layers"]:
                self.cp.reloadImage(frame_index=frame, layer_id=self.db.getLayer(layer).id)
        sys.stdout = sys.__stdout__

    # reading paramteres and updating the dictionary
    def parameters_changed(self):
        self.parameter_dict = read_all_paramters(self.parameter_widgets, self.parameter_dict)

    # decorator functions to handle diffrent outputs and writing to text file
    def calculate_general_properties(self, frames):  # calculation of colony area, number of cells in colony
        self.db_info, self.masks, self.res_dict = apply_to_frames(self.db, self.parameter_dict,
                                                                  analysis_function=general_properties,
                                                                  res_dict=self.res_dict,
                                                                  masks=self.masks, frames=frames, db_info=self.db_info)

    def calculate_deformation(self, frames):  # calculation of deformations

        self.db_info, self.masks, self.res_dict = apply_to_frames(self.db, self.parameter_dict,
                                                                  analysis_function=deformation, res_dict=self.res_dict,
                                                                  masks=self.masks, frames=frames, db_info=self.db_info)

    def calculate_traction(self, frames):  # calculation of traction forces
        self.db_info, self.masks, self.res_dict = apply_to_frames(self.db, self.parameter_dict,
                                                                  analysis_function=traction_force,
                                                                  res_dict=self.res_dict,
                                                                  masks=self.masks, frames=frames, db_info=self.db_info)

    def calculate_FEM_analysis(self, frames):  # calculation of various stress measures
        self.db_info, self.masks, self.res_dict = apply_to_frames(self.db, self.parameter_dict,
                                                                  analysis_function=FEM_full_analysis,
                                                                  res_dict=self.res_dict,
                                                                  masks=self.masks, frames=frames, db_info=self.db_info)

    def calculate_contractile_measures(self, frames):  # calculation of contractility and contractile energy
        self.db_info, self.masks, self.res_dict = apply_to_frames(self.db, self.parameter_dict,
                                                                  analysis_function=get_contractillity_contractile_energy,
                                                                  masks=self.masks, res_dict=self.res_dict,
                                                                  frames=frames, db_info=self.db_info)

    def set_frames(self):
        if self.mode == "current frame":  # only current frame
            frames = self.frame
        if self.mode == "all frames":  # all frames
            frames = self.all_frames
        return frames

    def drift_correction(self):  # calculation of contractility and contractile energy
        cdb_frame = self.cp.getCurrentFrame()
        self.frame = self.db_info["cbd_frames_ref_dict"][cdb_frame]
        self.mode = self.analysis_mode.currentText()  # only current frame or all frames
        frames = self.set_frames()
        self.db_info, self.masks, self.res_dict = apply_to_frames(self.db, self.parameter_dict,
                                                                  analysis_function=simple_shift_correction,
                                                                  masks=self.masks, res_dict=self.res_dict,
                                                                  frames=frames, db_info=self.db_info)
        print("calculation complete")

    def segmentation(self):  # calculation of contractility and contractile energy
        self.cdb_frame = self.cp.getCurrentFrame()
        self.frame = self.db_info["cbd_frames_ref_dict"][self.cdb_frame]
        self._new_window_slider = SegSlider(self)
        self._new_window_slider.show()

    # switching the type of cell colony
    def switch_colony_type_mode(self, first=False):
        setup_mask_wrapper(self, self.db, self.db_info, self.parameter_dict, delete_all=False)
        self.cp.reloadMaskTypes()  # reloading mask to display in clickpoints window
        try:
            self.db.setOption(key="FEM_mode", value=self.parameter_dict["FEM_mode"])
        except KeyError:
            self.db._AddOption(key="FEM_mode", value=self.parameter_dict["FEM_mode"])
            self.db.setOption(key="FEM_mode", value=self.parameter_dict["FEM_mode"])

    def start(self):
        # store parameters in settings
        for key in self.param_dict_keys:
            self.settings.setValue(key, self.parameter_dict[key])
        self.settings.sync()

        # workaround because plt.figure() sometimes gets overloaded when other addons are imported
        if "figures" in list(plt.figure.__globals__.keys()):
            importlib.reload(plt)

        # generating objects needed for the following calculation, if they are not exsisting already
        print_parameters(self.parameter_dict)
        print("output file: ", self.outfile_path)
        self.db_info, self.all_frames = get_db_info_for_analysis(self.db)
        cdb_frame = self.cp.getCurrentFrame()
        self.frame = self.db_info["cbd_frames_ref_dict"][cdb_frame]
        self.mode = self.analysis_mode.currentText()  # only current frame or all frames
        self.res_dict = defaultdict(lambda: defaultdict(list))

        frames = self.set_frames()
        print("analyzing frames = ", frames)
        self.masks = cells_masks(frames, self.db, self.db_info, self.parameter_dict)
        self.outfile_path = write_output_file(self.parameter_dict, "parameters", self.outfile_path, new_file=True)

        if self.check_box_def.isChecked():
            self.calculate_deformation(frames)
        if self.check_box_tra.isChecked():
            self.calculate_traction(frames)
        self.calculate_general_properties(frames)
        if self.check_box_FEM.isChecked():
            self.calculate_FEM_analysis(frames)
        if self.check_box_contract.isChecked():
            self.calculate_contractile_measures(frames)

        self.outfile_path = write_output_file(self.res_dict, "results", self.outfile_path,
                                              new_file=False)  # writing to output file
        print("calculation complete")

    # run in a separate thread to keep clickpoints gui responsive // now using QThread and stuff
    def start_thread(self, run_function=None):
        self.thread = Worker(self, run_function=run_function)
        self.thread.start()  # starting thread
        self.thread.finished.connect(self.reload_all)  # connecting function on thread finish

        # x.join()

    def buttonPressedEvent(self):
        # show the addon window when the button in ClickPoints is pressed
        self.show()

    # disable running in other thread other wise "figsize" is somehow overloaded
    async def run(self):
        pass


class Worker(QtCore.QThread):
    output = pyqtSignal()

    def __init__(self, main, parent=None, run_function=None):
        QtCore.QThread.__init__(self, parent)
        self.main = main
        if run_function is None:
            self.run_function = self.main.start
        else:
            self.run_function = run_function

    def run(self):
        self.run_function()


def setup_mask_wrapper(window, db, db_info, parameter_dict, delete_all=False, warn_popup=True):
    other_masks = check_existing_masks(db, parameter_dict)
    del_str = "all previous masks" if delete_all else "the masks " + str(other_masks)[1:-1]
    if len(other_masks) > 0 and not delete_all:
        if warn_popup:
            choice = QtWidgets.QMessageBox.question(window, 'continue',
                                                    "This will delete %s. Do you want to continue?" % del_str,
                                                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if choice == QtWidgets.QMessageBox.Yes:
                setup_masks(db, db_info, parameter_dict, delete_all=delete_all, delete_specific=other_masks)
    else:
        setup_masks(db, db_info, parameter_dict, delete_all=delete_all, delete_specific=other_masks)


# TODO: use qt designer for better layout and stuff
