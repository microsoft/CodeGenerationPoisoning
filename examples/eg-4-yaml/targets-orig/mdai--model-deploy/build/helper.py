import os
import yaml
from shutil import rmtree
import docker
from shutil import copytree
import sys


BASE_DIRECTORY = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

PLACEHOLDER_VALUES = {
    "{{PARENT_IMAGE}}": [],
    "{{COPY}}": ["COPY lib /src/lib/"],
    "{{COMMAND_MDAI}}": ['CMD ["/bin/bash", "-c", "source activate mdai-env ; python server.py"]'],
    "{{COMMAND}}": ['CMD ["/bin/bash", "-c", "python server.py"]'],
    "{{ENV}}": [],
}

PARENT_IMAGE_DICT = {
    "cpu": "gcr.io/deeplearning-platform-release/base-cpu",
    "gpu": {
        "11.3": "gcr.io/deeplearning-platform-release/base-cu113",
        "11.0": "gcr.io/deeplearning-platform-release/base-cu110",
        "10.1": "gcr.io/deeplearning-platform-release/base-cu101",
        "10.0": "gcr.io/deeplearning-platform-release/base-cu100",
    },
    "nvidia": {
        "4.1.0": "nvcr.io/nvidia/clara-train-sdk:v4.1",
        "4.0": "nvcr.io/nvidia/clara-train-sdk:v4.0",
        "3.1.01": "nvcr.io/nvidia/clara-train-sdk:v3.1.01",
        "3.1": "nvcr.io/nvidia/clara-train-sdk:v3.1",
        "3.0": "nvcr.io/nvidia/clara-train-sdk:v3.0",
        "2.0": "nvcr.io/nvidia/clara-train-sdk:v2.0",
    },
}


def replace_lines(infile, outfile, replace_dict):
    for line in infile:
        key = line.rstrip()
        if key in replace_dict:
            outfile.write("\n".join(replace_dict[key]))
        else:
            outfile.write(line)


def process_dockerfile(docker_env, placeholder_values):
    src_dockerfile = os.path.join(BASE_DIRECTORY, "docker", docker_env, "Dockerfile")
    dest_dockerfile = "./Dockerfile"
    print(f"\nCopying Dockerfile from {src_dockerfile} to {dest_dockerfile} ...")
    with open(src_dockerfile, "r") as infile, open(dest_dockerfile, "w") as outfile:
        replace_lines(infile, outfile, placeholder_values)
    return dest_dockerfile


def process_config_file(config_file):
    cwd = os.getcwd()
    config_file = os.path.abspath(config_file)
    parent_dir = os.path.dirname(config_file)
    os.chdir(parent_dir)

    with open(config_file, "r") as stream:
        data = yaml.safe_load(stream)

        os.chdir(cwd)
    return data


def get_paths(args):
    target_folder = os.path.abspath(args.target_folder)
    mdai_folder = os.path.join(target_folder, args.mdai_folder)
    config_path = os.path.join(mdai_folder, "config.yaml")
    if not os.path.exists(config_path):
        config_path = os.path.join(mdai_folder, "config.yml")
    if not os.path.exists(config_path):
        config_path = None
    return target_folder, mdai_folder, config_path


def remove_files(copies):
    print("\nRemoving copied files...")
    for file_copy in copies:
        if os.path.isdir(file_copy):
            rmtree(file_copy)
        else:
            os.remove(file_copy)


def build_image(client, docker_image, relative_mdai_folder):
    print(f"\nBuilding docker image {docker_image} ...\n")
    build_dict = {"MDAI_PATH": relative_mdai_folder}
    response = client.api.build(
        path=".", tag=docker_image, quiet=False, decode=True, buildargs=build_dict
    )
    for line in response:
        if list(line.keys())[0] in ("stream", "error"):
            value = list(line.values())[0]
            if value:
                print(value.strip())


def add_env_variables(placeholder_values, env_variables):
    ENV = "{{ENV}}"
    if env_variables is None:
        return
    for key in env_variables:
        arg_string = f"ARG {key}"
        env_string = f"ENV {key}={env_variables[key]}"
        placeholder_values[ENV].append(arg_string)
        placeholder_values[ENV].append(env_string)


def copy_files(target_folder, docker_env):
    dest_dockerfile = process_dockerfile(docker_env, PLACEHOLDER_VALUES)

    src_lib = target_folder
    dest_lib = "./lib"
    print(f"\nCopying target dir from {src_lib} to {dest_lib} ...")
    copytree(src_lib, dest_lib)

    copies = [dest_lib, dest_dockerfile]
    return [os.path.abspath(file_copy) for file_copy in copies]


def resolve_parent_image(placeholder_dict, config, image_dict, mdai_folder):
    framework = None
    base_image = config.get("base_image", "py37").lower()
    device_type = config.get("device_type", "cpu").lower()
    cuda_version = str(config.get("cuda_version", "11.0"))
    clara_version = config.get("clara_version", "4.1.0")

    if device_type not in ["cpu", "gpu"]:
        print(
            f"Device type '{device_type}' is not supported. Please select one from CPU or GPU.",
            file=sys.stderr,
        )
        sys.exit()

    if base_image == "custom":
        try:
            with open(os.path.join(mdai_folder, "Dockerfile")) as f:
                parent_image = f.readlines()
            command = "".join(parent_image)
        except IOError:
            print(
                "Custom Dockerfile missing. Please upload Dockerfile in the .mdai folder.",
                file=sys.stderr,
            )
            sys.exit()
    elif base_image == "nvidia":
        if clara_version not in ["4.1.0"]:
            print("Only NVIDIA Clara v4.1.0 models are supported currently.", file=sys.stderr)
            sys.exit()
        parent_image = image_dict["nvidia"].get(str(clara_version))
        command = " ".join(["FROM", parent_image])
    else:
        if device_type == "cpu":
            parent_image = image_dict.get("cpu")
        elif device_type == "gpu" and cuda_version in image_dict.get("gpu"):
            parent_image = image_dict["gpu"].get(cuda_version)
        else:
            print(
                f"Cuda version {cuda_version} is not supported. Please check documentation for the correct versions.",
                file=sys.stderr,
            )
            sys.exit()
        command = " ".join(["FROM", parent_image])
    placeholder_dict["{{PARENT_IMAGE}}"].append(command)

    # Add opencv-python GUI libraries for CPU base image
    if device_type == "cpu":
        placeholder_dict["{{PARENT_IMAGE}}"].append(
            "RUN apt-get update && apt-get install -y libgl1-mesa-glx"
        )


def create_docker_image(args):
    client = docker.from_env()
    cwd = os.getcwd()

    docker_env = args.docker_env
    docker_image = args.image_name
    env = None
    config = {}

    target_folder, mdai_folder, config_path = get_paths(args)

    # Prioritize config file values if it exists
    if config_path is not None:
        config = process_config_file(config_path)

    resolve_parent_image(PLACEHOLDER_VALUES, config, PARENT_IMAGE_DICT, mdai_folder)
    add_env_variables(PLACEHOLDER_VALUES, config.get("env"))
    relative_mdai_folder = os.path.relpath(mdai_folder, target_folder)
    os.chdir(os.path.join(BASE_DIRECTORY, "mdai"))
    copies = copy_files(target_folder, config["base_image"])

    try:
        build_image(client, docker_image, relative_mdai_folder)
    except docker.errors.APIError as e:
        print("\nBuild Error: {}".format(e))
    finally:
        remove_files(copies)
        os.chdir(cwd)
