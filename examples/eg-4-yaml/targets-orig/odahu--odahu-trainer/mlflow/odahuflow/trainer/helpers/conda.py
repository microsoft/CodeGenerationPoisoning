#
#    Copyright 2020 EPAM Systems
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
import json
import logging
import os
import shutil
from os.path import join
from typing import Any, Dict

import yaml
from odahuflow.trainer.helpers.wrapper.entities import MLFlowWrapperOutput
from odahuflow.sdk import io_proc_utils
from odahuflow.sdk.models import ModelTraining

MLFLOW_WRAPPER_OUTPUT_FILE_PATH = 'mlflow-output.json'
MLFLOW_WRAPPER_INPUT_FILE_PATH = "mlflow-input.json"
MLPROJECT_FILE_NAME = "mlproject"
DEFAULT_CONDA_FILE_NAME = "conda.yaml"
ODAHU_MODEL_CONDA_ENV_NAME = os.environ.get("ODAHU_CONDA_ENV_NAME", "odahu_model")


logger = logging.getLogger(__name__)


def _find_mlproject_file_path(model_training: ModelTraining) -> str:
    work_dir = join(os.getcwd(), model_training.spec.work_dir)

    filenames = os.listdir(work_dir)
    for filename in filenames:
        if filename.lower() == MLPROJECT_FILE_NAME:
            return join(work_dir, filename)

    raise ValueError(f"Can't find a MLProject file in the '{work_dir}' dir")


def _extract_conda_file_name(ml_project: dict) -> str:
    """
    Extract conda dependencies file name from MLProject file
    :param mlproject_file_path: MLFlow MLProject file path
    :return: conda file name
    """
    return ml_project.get("conda_env", DEFAULT_CONDA_FILE_NAME)


def _get_conda_bin_executable(executable_name):
    """
    Return path to the specified executable, assumed to be discoverable within the 'bin'
    subdirectory of a conda installation.
    """
    # Use CONDA_EXE as per https://github.com/conda/conda/issues/7126
    if "CONDA_EXE" in os.environ:
        conda_bin_dir = os.path.dirname(os.environ["CONDA_EXE"])
        return os.path.join(conda_bin_dir, executable_name)
    return executable_name


def _get_conda_command(conda_env_name):
    #  Checking for newer conda versions
    if os.name != 'nt' and ('CONDA_EXE' in os.environ or 'MLFLOW_CONDA_HOME' in os.environ):
        conda_path = _get_conda_bin_executable("conda")
        activate_conda_env = [f'source {os.path.dirname(conda_path)}/../etc/profile.d/conda.sh']
        activate_conda_env += [f'conda activate {conda_env_name} 1>&2']
    else:
        activate_path = _get_conda_bin_executable("activate")
        # in case os name is not 'nt', we are not running on windows. It introduces
        # bash command otherwise.
        if os.name != 'nt':
            return [f'source {activate_path} {conda_env_name} 1>&2']
        else:
            return [f'conda activate {conda_env_name}']
    return activate_conda_env


def update_model_conda_env(model_training: ModelTraining):
    """
    Update model conda dependencies
    :param model_training:
    """

    mlproject_file_path = _find_mlproject_file_path(model_training)
    with open(mlproject_file_path, encoding='utf-8') as f:
        ml_project = yaml.safe_load(f)

    conda_env_configured_explicitly = ml_project.get("conda_env") is not None

    default_conda_full_path = os.path.join(
        os.getcwd(), model_training.spec.work_dir, DEFAULT_CONDA_FILE_NAME
    )
    default_file_exists = os.path.exists(default_conda_full_path)

    if not conda_env_configured_explicitly and not default_file_exists:
        logger.info(
            f"Conda file is not configured explicitly. "
            f"Default file {DEFAULT_CONDA_FILE_NAME} does not exists. "
            f"Skip updating conda environment for training. "
            f"Conda environment name: ODAHU_MODEL_CONDA_ENV_NAME={ODAHU_MODEL_CONDA_ENV_NAME}"
        )
        return

    io_proc_utils.run(
        "conda", "env", "update", "-n", ODAHU_MODEL_CONDA_ENV_NAME,
        "-f", _extract_conda_file_name(ml_project),
        cwd=os.path.join(os.getcwd(), model_training.spec.work_dir)
    )


def run_mlflow_wrapper(mlflow_input: Dict[str, Any]) -> str:
    """
    Prepare parameters and run MLFlow wrapper inside the model conda environment
    :param mlflow_input: parameters which will be passed to mlflow.run function
    :return: MLFlow run ID
    """
    with open(MLFLOW_WRAPPER_INPUT_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(mlflow_input, f)

    sep = ' && '
    args = _get_conda_command(ODAHU_MODEL_CONDA_ENV_NAME)
    args += [f'{shutil.which("odahu-flow-mlflow-wrapper")} '
             f'--input {MLFLOW_WRAPPER_INPUT_FILE_PATH} '
             f'--output {MLFLOW_WRAPPER_OUTPUT_FILE_PATH}']
    command = sep.join(args)

    logger.info(f'Run command {command}')

    io_proc_utils.run('bash', '-c', command)

    with open(MLFLOW_WRAPPER_OUTPUT_FILE_PATH, encoding='utf-8') as f:
        return MLFlowWrapperOutput(**json.load(f)).run_id
