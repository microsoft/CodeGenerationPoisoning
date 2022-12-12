#!/usr/bin/env python3
#
#    Copyright 2019 EPAM Systems
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
import argparse
import contextlib
import json
import logging
import os
import os.path
import shutil
import sys
import tarfile
from typing import Optional
from urllib import parse

import yaml
from odahuflow.sdk.gppi.executor import GPPITrainedModelBinary
from odahuflow.sdk.gppi.models import OdahuflowProjectManifest, OdahuflowProjectManifestBinaries, \
    OdahuflowProjectManifestModel, OdahuflowProjectManifestToolchain, OdahuflowProjectManifestOutput
from odahuflow.sdk.models import K8sTrainer, ModelIdentity
from odahuflow.sdk.models import ModelTraining

from odahuflow.trainer.helpers.conda import run_mlflow_wrapper, update_model_conda_env
from odahuflow.trainer.helpers.fs import copytree

import mlflow
import mlflow.models
import mlflow.projects
import mlflow.pyfunc
import mlflow.tracking
from mlflow.tracking import set_tracking_uri, get_tracking_uri, MlflowClient

MODEL_SUBFOLDER = 'odahuflow_model'
ODAHUFLOW_PROJECT_DESCRIPTION = 'odahuflow.project.yaml'
ENTRYPOINT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'entrypoint.py')



def parse_model_training_entity(source_file: str) -> K8sTrainer:
    """
    Parse model training file
    """
    logging.info(f'Parsing Model Training file: {source_file}')

    # Validate resource file exist
    if not os.path.exists(source_file) or not os.path.isfile(source_file):
        raise ValueError(f'File {source_file} is not readable')

    with open(source_file, 'r', encoding='utf-8') as mt_file:
        mt = mt_file.read()
        logging.debug(f'Content of {source_file}:\n{mt}')

        try:
            mt = json.loads(mt)
        except json.JSONDecodeError:
            try:
                mt = yaml.safe_load(mt)
            except json.JSONDecodeError as decode_error:
                raise ValueError(f'Cannot decode ModelTraining resource file: {decode_error}') from decode_error

    return K8sTrainer.from_dict(mt)


def save_models(mlflow_run_id: str, model_training: ModelTraining, target_directory: str) -> None:
    """
    Save models after run
    """
    # Using internal API for getting store and artifacts location
    store = mlflow.tracking._get_store()
    artifact_uri = store.get_run(mlflow_run_id).info.artifact_uri
    logging.info(f"Artifacts location detected. Using store {store}")

    parsed_url = parse.urlparse(artifact_uri)
    if parsed_url.scheme and parsed_url.scheme != 'file':
        raise ValueError(f'Unsupported scheme of url: {parsed_url}')
    artifacts_path = parsed_url.path

    logging.info(f"Analyzing directory {artifact_uri} for models")
    artifacts_abs_paths = map(lambda path: os.path.join(artifacts_path, path), os.listdir(artifacts_path))
    found_models = list(filter(lambda path: load_pyfunc_model(path, none_on_failure=True), artifacts_abs_paths))

    if len(found_models) != 1:
        raise ValueError(f'Expected to find exactly 1 model, found {len(found_models)}')

    mlflow_to_gppi(model_training.spec.model, found_models[0], target_directory, mlflow_run_id)


def load_pyfunc_model(path: str, none_on_failure=False) -> Optional[mlflow.models.Model]:
    """Loads Mlflow models with pyfunc flavor
    :param none_on_failure: return None instead of raising exception on failure
    :raises Exception: if provided path is not an MLFlow model
    """
    try:
        mlflow_model = mlflow.models.Model.load(path)
    except Exception:
        if none_on_failure:
            return None
        raise

    if mlflow.pyfunc.FLAVOR_NAME not in mlflow_model.flavors.keys():
        if none_on_failure:
            return None
        raise ValueError(f"{path} does not has {mlflow.pyfunc.FLAVOR_NAME} flavor")
    return mlflow_model


def mlflow_to_gppi(model_meta: ModelIdentity, mlflow_model_path: str, gppi_model_path: str, mlflow_run_id: str):
    """Wraps an MLFlow model with a GPPI interface
    :param model_meta: container for model name and version
    :param mlflow_model_path: path to MLFlow model
    :param gppi_model_path: path to target GPPI directory, should be empty
    :param mlflow_run_id: mlflow run id for model
    """
    try:
        mlflow_model = load_pyfunc_model(mlflow_model_path)
    except Exception as load_exception:
        raise ValueError(f"{mlflow_model_path} is not a MLflow model: {load_exception}") from load_exception

    mlflow_target_directory = os.path.join(gppi_model_path, MODEL_SUBFOLDER)

    logging.info(f"Copying MLflow model from {mlflow_model_path} to {mlflow_target_directory}")

    if not os.path.exists(mlflow_target_directory):
        os.makedirs(mlflow_target_directory)
    copytree(mlflow_model_path, mlflow_target_directory)

    py_flavor = mlflow_model.flavors[mlflow.pyfunc.FLAVOR_NAME]

    env = py_flavor.get('env')
    if not env:
        raise ValueError('Unknown type of env - empty')

    dependencies = 'conda'
    conda_path = os.path.join(MODEL_SUBFOLDER, env)
    logging.info(f'Conda env located in {conda_path}')

    entrypoint_target = os.path.join(mlflow_target_directory, 'entrypoint.py')
    shutil.copyfile(ENTRYPOINT, entrypoint_target)

    project_file_path = os.path.join(gppi_model_path, ODAHUFLOW_PROJECT_DESCRIPTION)

    manifest = OdahuflowProjectManifest(
        odahuflowVersion='1.0',
        binaries=OdahuflowProjectManifestBinaries(
            type='python',
            dependencies=dependencies,
            conda_path=conda_path
        ),
        model=OdahuflowProjectManifestModel(
            name=model_meta.name,
            version=model_meta.version,
            workDir=MODEL_SUBFOLDER,
            entrypoint='entrypoint'
        ),
        toolchain=OdahuflowProjectManifestToolchain(
            name='mlflow',
            version=mlflow.__version__
        ),
        output=OdahuflowProjectManifestOutput(
            run_id=mlflow_run_id
        )
    )

    with open(project_file_path, 'w', encoding='utf-8') as proj_stream:
        yaml.dump(manifest.dict(), proj_stream)

    logging.info("GPPI stored. Starting GPPI validation")
    mb = GPPITrainedModelBinary(gppi_model_path)
    mb.self_check()
    logging.info("GPPI is validated. OK")


def get_or_create_experiment(experiment_name, artifact_location=None) -> str:
    client = MlflowClient()

    # Registering of experiment on tracking server if it is not exist
    logging.info(f"Searching for experiment with name {experiment_name}")
    experiment = client.get_experiment_by_name(experiment_name)

    if experiment:
        experiment_id = experiment.experiment_id
        logging.info(f"Experiment {experiment_id} has been found")
    else:
        logging.info(f"Creating new experiment with name {experiment_name}")

        experiment_id = client.create_experiment(experiment_name, artifact_location=artifact_location)

        logging.info(f"Experiment {experiment_id} has been created")
        client.get_experiment_by_name(experiment_name)
    return experiment_id


def train_models(model_training: ModelTraining, experiment_id: str) -> str:
    """
    Start MLfLow run
    """
    logging.info('Downloading conda dependencies')
    update_model_conda_env(model_training)

    logging.info('Getting of tracking URI')
    tracking_uri = get_tracking_uri()
    if not tracking_uri:
        raise ValueError('Can not get tracking URL')
    logging.info(f"Using MLflow client placed at {tracking_uri}")

    logging.info('Creating MLflow client, setting tracking URI')
    set_tracking_uri(tracking_uri)

    # Starting run and awaiting of finish of run
    logging.info(f"Starting MLflow's run function. Parameters: [project directory: {model_training.spec.work_dir}, "
                 f"entry point: {model_training.spec.entrypoint}, "
                 f"hyper parameters: {model_training.spec.hyper_parameters}, "
                 f"experiment id={experiment_id}]")

    mlflow_input = {
        "uri": model_training.spec.work_dir,
        "entry_point": model_training.spec.entrypoint,
        "parameters": model_training.spec.hyper_parameters,
        "experiment_id": experiment_id,
        "backend": 'local',
        "synchronous": True,
        "use_conda": False,
    }

    run_id = run_mlflow_wrapper(mlflow_input)

    # TODO: refactor
    client = MlflowClient()
    client.set_tag(run_id, "training_id", model_training.id)
    client.set_tag(run_id, "model_name", model_training.spec.model.name)
    client.set_tag(run_id, "model_version", model_training.spec.model.version)

    logging.info(f"MLflow's run function finished. Run ID: {run_id}")

    return run_id


def setup_logging(args: argparse.Namespace) -> None:
    """
    Setup logging instance
    """
    log_level = logging.DEBUG if args.verbose else logging.INFO

    logging.basicConfig(format='[odahuflow][%(levelname)5s] %(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                        level=log_level)


@contextlib.contextmanager
def _remember_cwd():
    curdir = os.getcwd()
    try:
        yield
    finally:
        os.chdir(curdir)


def mlflow_to_gppi_cli():

    def make_dir(string):
        try:
            os.makedirs(string, exist_ok=True)
        except FileExistsError as error:
            raise ValueError(f'A file already exists with the same name: {string}\n'
                             'Rename file or directory and try again.') from error

    def dir_type(string):
        if not os.path.isdir(string):
            raise ValueError
        return string

    parser = argparse.ArgumentParser(description='Converts MLFLow model to GPPI.')

    parser.add_argument('--verbose', action='store_true', help='More extensive logging')
    parser.add_argument('--model-name', type=str, required=True, help='Name of GPPI Model')
    parser.add_argument('--model-version', type=str, required=True, help='Version of GPPI Model')
    parser.add_argument('--mlflow-model-path', '--mlflow', required=True,
                        type=dir_type, help='Path to source MLFlow model directory')
    parser.add_argument('--gppi-model-path', '--gppi', required=True,
                        type=str, help='Path to result GPPI model directory')
    parser.add_argument('--mlflow-run-id', type=str, required=True, help='Run ID for MLFlow model')
    parser.add_argument('--no-tgz', dest='tgz', action='store_false', help='Prevent archiving result directory')
    args = parser.parse_args()

    setup_logging(args)
    gppi_model_path: str = args.gppi_model_path

    make_dir(gppi_model_path)

    if len(os.listdir(gppi_model_path)) > 0:
        logging.error("Result directory must be empty!")

    try:
        mlflow_to_gppi(model_meta=ModelIdentity(name=args.model_name.strip(), version=args.model_version.strip()),
                       mlflow_model_path=args.mlflow_model_path,
                       gppi_model_path=gppi_model_path,
                       mlflow_run_id=args.mlflow_run_id)

        if args.tgz:
            with _remember_cwd(), tarfile.open(f'{gppi_model_path}.tgz', 'w:gz') as tar:  # type: tarfile.TarFile
                os.chdir(args.gppi_model_path)
                for s in os.listdir('.'):
                    tar.add(s)
            shutil.rmtree(gppi_model_path)

    except Exception as e:
        error_message = f'Exception occurs during model conversion. Message: {e}'

        if args.verbose:
            logging.exception(error_message)
        else:
            logging.error(error_message)

        sys.exit(1)
