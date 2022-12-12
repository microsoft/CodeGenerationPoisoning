import copy
import math
import os
import time

from contextlib import contextmanager
from datetime import datetime

import numpy as np
import pandas as pd
import yaml

from model import Model

TYPE_MAP = {
    "cat": str,
    "multi-cat": str,
    "str": str,
    "num": np.float64,
    "timestamp": "str",
}

PRIMARY_TIMESTAMP = "primary_timestamp"
LABEL_NAME = "label"
TIMESTAMP_TYPE_NAME = "timestamp"
TRAIN_FILE = "train.data"
TEST_FILE = "test.data"
TIME_FILE = "test_time.data"
INFO_FILE = "info.yaml"

CUM = 0
RESET = 1
MODES = set([CUM, RESET])

PROCESSES = ["train", "predict", "update", "save", "load"]
PROCESSES_MODE = {
    "train": RESET,
    "predict": CUM,
    "update": CUM,
    "save": RESET,
    "load": RESET,
}


def _date_parser(millisecs):
    if np.isnan(float(millisecs)):
        return millisecs

    return datetime.fromtimestamp(float(millisecs))


class Dataset:
    def __init__(self, dataset_dir):
        self.dataset_dir_ = dataset_dir
        self.metadata_ = self._read_metadata(os.path.join(dataset_dir, INFO_FILE))
        self.train_dataset = None
        self.test_dataset = None

        self.get_train()
        self.get_test()

        self._pred_time = self._get_pred_time()
        self._primary_timestamp = self.metadata_[PRIMARY_TIMESTAMP]

    def get_train(self):
        if self.train_dataset is None:
            self.train_dataset = self._read_dataset(
                os.path.join(self.dataset_dir_, TRAIN_FILE)
            )

        return copy.deepcopy(self.train_dataset)

    def get_test(self):
        if self.test_dataset is None:
            self.test_dataset = self._read_dataset(
                os.path.join(self.dataset_dir_, TEST_FILE)
            )

        return copy.deepcopy(self.test_dataset)

    def get_metadata(self):
        return copy.deepcopy(self.metadata_)

    def is_end(self, idx):
        return idx == len(self._pred_time)

    def _get_period(self, idx1, idx2):
        next_time = self._get_time_point(idx2)
        timestamp = self.test_dataset[self._primary_timestamp]
        select = timestamp < next_time

        if idx1 is not None:
            last_time = self._get_time_point(idx1)
            select &= timestamp >= last_time

        return self.test_dataset[select]

    def get_history(self, idx):
        if idx > 0:
            ret = self._get_period(idx - 1, idx)
        else:
            ret = self._get_period(None, idx)

        return copy.deepcopy(ret)

    def get_next_pred(self, idx):
        next_time = self._get_time_point(idx)
        select = self.test_dataset[self._primary_timestamp] == next_time
        data = self.test_dataset[select].drop(self.metadata_[LABEL_NAME], axis=1)

        return copy.deepcopy(data)

    def get_all_history(self, idx):
        return copy.deepcopy(self._get_period(None, idx))

    def _get_pred_time(self):
        return pd.read_csv(
            os.path.join(self.dataset_dir_, TIME_FILE),
            parse_dates=[self.metadata_[PRIMARY_TIMESTAMP]],
            date_parser=_date_parser,
        )

    def _get_time_point(self, idx):
        return self._pred_time.iloc[idx, 0]

    @staticmethod
    def _read_metadata(metadata_path):
        with open(metadata_path, "r") as ftmp:
            return yaml.safe_load(ftmp)

    def _read_dataset(self, dataset_path):
        schema = self.metadata_["schema"]
        table_dtype = {key: TYPE_MAP[val] for key, val in schema.items()}
        date_list = [key for key, val in schema.items() if val == TIMESTAMP_TYPE_NAME]
        dataset = pd.read_csv(
            dataset_path,
            sep="\t",
            dtype=table_dtype,
            parse_dates=date_list,
            date_parser=_date_parser,
        )

        return dataset

    def get_test_timestamp(self):
        return copy.deepcopy(self.test_dataset[self._primary_timestamp])

    def get_pred_timestamp(self):
        return copy.deepcopy(self._pred_time)


class Timer:
    def __init__(self):
        self.total = {}
        self.history = {}
        self.modes = {}

    def add_process(self, pname, time_budget, mode=RESET):
        if pname in self.total:
            raise ValueError(f"Existing process of timer: {pname}")
        if mode not in MODES:
            raise ValueError(f"wrong process mode: {mode}")

        self.total[pname] = time_budget
        self.history[pname] = []
        self.modes[pname] = mode

    @contextmanager
    def time_limit(self, pname, verbose=True):
        time_budget = int(math.ceil(self.get_remain(pname)))

        start_time = time.time()

        try:
            yield

        finally:
            exec_time = time.time() - start_time

            if time_budget - exec_time <= 0:
                raise RuntimeError(f"{pname}: Timed out!")

            self.history[pname].append(exec_time)

        if self.get_remain(pname) <= 0:
            raise RuntimeError(f"{pname}: Timed out!")

    def get_remain(self, pname):
        if self.modes[pname] == CUM:
            remain = self.total[pname] - sum(self.history[pname])
        else:
            remain = self.total[pname]

        return remain

    def get_all_remain(self):
        return {key: self.get_remain(key) for key in self.total.keys()}


def _train(umodel, dataset, timer):
    train_dataset = dataset.get_train()

    with timer.time_limit("train"):
        next_step = umodel.train(train_dataset, timer.get_all_remain())

    return next_step


def _update(umodel, idx, dataset, timer):
    train_data = dataset.get_train()
    test_historical_data = dataset.get_all_history(idx)

    with timer.time_limit("update"):
        next_step = umodel.update(
            train_data, test_historical_data, timer.get_all_remain()
        )

    return next_step


def _predict(umodel, args, idx, timer):
    result = {}

    try:
        dataset = Dataset(args["dataset_dir"])

        y_preds = []

        while not dataset.is_end(idx):
            history = dataset.get_history(idx)
            pred_record = dataset.get_next_pred(idx)

            with timer.time_limit("predict", verbose=False):
                y_pred, next_step = umodel.predict(
                    history, pred_record, timer.get_all_remain()
                )

            y_preds.extend(y_pred)

            idx += 1

            if next_step == "update":
                result["is_end"] = False
                break

        else:
            result["is_end"] = True

        result = {
            **result,
            "idx": idx,
            "status": "success",
            "next_step": next_step,
        }

    except RuntimeError as e:
        raise RuntimeError("predicting timeout") from e

    except Exception as e:
        raise RuntimeError("error occurs when predicting") from e

    return result["idx"], result["next_step"], result["is_end"]


def test_model():
    args = {"dataset_dir": "data/autoseries20/demo/train.data"}

    dataset = Dataset(args["dataset_dir"])
    metadata = dataset.get_metadata()

    args["time_budget"] = metadata.get("time_budget")

    umodel = Model(
        dataset.get_metadata(),
        dataset.get_test_timestamp(),
        dataset.get_pred_timestamp(),
    )

    timer = Timer()

    for process in PROCESSES:
        timer.add_process(
            process, args["time_budget"][process], PROCESSES_MODE[process]
        )

    next_step = _train(umodel, dataset, timer)
    idx = 0
    n_update = 0

    while True:
        if next_step == "predict":
            idx, next_step, is_end = _predict(umodel, args, idx, timer)

            if is_end:
                break

        elif next_step == "update":
            n_update += 1
            next_step = _update(umodel, idx, dataset, timer)

        else:
            raise RuntimeError(
                f"wrong next_step [{next_step}], " "should be {predict, update}"
            )
