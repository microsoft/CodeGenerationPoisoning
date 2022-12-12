# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import codecs
import os
import random
import string
from itertools import chain

import yaml
from docker import from_env
from docker.client import DockerClient
from docker.errors import ImageNotFound
from docker.models.containers import Container  # pylint: disable=unused-import
from docker.models.images import Image
from jinja2.environment import Environment
from jinja2.loaders import FileSystemLoader
from jinja2.runtime import StrictUndefined
from markupsafe import Markup


class NoModulesToInstall(Exception):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors


def _get_top_dirs(image: Image, prepared_image: Image, client: DockerClient) -> "list":
    """Returns a list of paths to all top level folders
     and files of python module that must be installed in image
    :param image: image without intaled modules
    :type image: Image
    :param prepared_image: image with intaled modules
    :type prepared_image: Image
    :param d_client: docker client
    :type d_client: DockerClient
    :return: list of path on image fs to module files
    :rtype: list
    """
    # list of packages from image without installed python modules
    default_module_list = _get_modules_list(image, client)

    # list of packages from image with installed installed modules
    modified_module_list = _get_modules_list(prepared_image, client)

    # list of packages tham must be installed
    modules = list(
        map(lambda x: x.split('==')[0], set(modified_module_list).difference(default_module_list))
    )

    modules_data = yaml.safe_load_all(
        client.containers.run(
            prepared_image, f'pip show -f {" ".join(modules)}', remove=True
        ).decode("utf-8")
    )
    return list(
        chain.from_iterable(
            map(
                lambda x: [
                    os.path.join(x['Location'], i)
                    for i in list(
                        dict.fromkeys(
                            map(lambda y: os.path.normpath(y).split(os.sep)[0], x['Files'].split())
                        )
                    )
                    if i not in ['..', '.']
                ],
                modules_data,
            )
        )
    )


def _get_modules_list(image: Image, client: DockerClient) -> "list":
    """Run pip freeze in docker container from given image.
    Returns output as a list.

    :param image: image name
    :type image: Image
    :param client: docker client
    :type client: DockerClient
    :return: list of installed python pkgs in given inamge freeze format
    :rtype: list
    """
    return (
        client.containers.run(image, '/bin/sh -c "pip freeze"', remove=True).decode("utf-8").split()
    )


def _get_prepared_container(pkgs: list, image: Image, client: DockerClient) -> "Container":
    """Install python pkgs to container from given image

    :param pkgs: List of python packages
    :type pkgs: list
    :param image: image name
    :type image: Image
    :param client: docker client
    :type client: DockerClient
    :return: container with installed python packages
    :rtype: Container
    """
    command = '/bin/sh -c "'
    if pkgs.get('system_pkg'):
        command += 'apk add ' + ' '.join(pkgs.get('system_pkg')) + ' >/dev/null ;'
    command += ' pip install ' + ' '.join(pkgs.get('python_mod')) + ' >/dev/null"'
    return client.containers.run(image, command, detach=True)


def _copy_pkgs_files(path, dirs, image: Image, volumes: dict, client: DockerClient):
    """Copy list of dirs from container from given image to path.

    :param path: path where to copy
    :type path: str
    :param dirs: paths what need to be copied
    :type dirs: list
    :param image: image that contains needed paths
    :type image: Image
    :param volumes: volumes that must be mounted to container.
    :type volumes: dict
    :param client: docker client
    :type client: DockerClient
    """
    dirs = list(dict.fromkeys(dirs))  # filter on keys of duplicate elements
    command = f'/bin/sh -c "mkdir {path}; cp -r {" ".join(dirs)} {path} ;'
    command += f' chown -R {os.getuid()} {path}"'
    client.containers.run(image, command, volumes=volumes, remove=True)


def _get_prepared_image(pkgs, image: Image, client: DockerClient) -> "Image":
    """Install pgks to container from given image and commits container to a new image

    :return: returns image with installed required python packages
    :rtype: Image
    """
    container = _get_prepared_container(pkgs, image, client)
    container.wait()

    prepared_image_name = [
        image.tags[0].split(':')[0],
        ''.join(random.sample(string.ascii_lowercase, 5)),
    ]
    prepared_image = container.commit(repository=prepared_image_name[0], tag=prepared_image_name[1])
    container.remove()
    return prepared_image


def python_mod_req(source_path, workspace, **kwargs):
    with open(os.path.join(source_path, kwargs['requirements']), 'r', encoding='utf-8') as file:
        pkgs = yaml.safe_load(file)
        if pkgs.get('python_mod'):
            client = from_env()
            # choose image where to install python pkgs
            # by default adcm:latest but i think this may be bad practice
            # better to use adcm_min_version of bundle
            image_name = "arenadata/adcm:latest" if not kwargs.get('image') else kwargs['image']
            image = client.images.pull(image_name)
            # clean up flag
            rm_prepared_image = True

            # prepared image is an image with intalled python packages
            # that need to be packed in bundle
            # for debug purposes there may be an prepared_image variable received from spec.yaml
            if kwargs.get('prepared_image'):
                try:
                    prepared_image = client.images.get(kwargs['prepared_image'])
                    rm_prepared_image = False
                except ImageNotFound:
                    prepared_image = _get_prepared_image(pkgs, image, client)
            else:
                prepared_image = _get_prepared_image(pkgs, image, client)

            # list of all highlevel dirs of python pkgs that must be packed
            dirs = _get_top_dirs(image, prepared_image, client)

            # volume that contains workspace
            volumes = {workspace: {'bind': workspace, 'mode': 'rw'}}

            if kwargs.get('target_dir'):
                path = os.path.join(source_path, kwargs['target_dir'], 'pmod')
            else:
                path = os.path.join(source_path, 'pmod')
            _copy_pkgs_files(path, dirs, prepared_image, volumes, client)

            if rm_prepared_image:
                client.images.remove(prepared_image.id)

        else:
            raise NoModulesToInstall('Can`t get python modules list to be inatalled')


def splitter(*args, **kwargs):
    loader = FileSystemLoader(args[0])
    env = Environment(loader=loader, undefined=StrictUndefined)

    def include_raw(name):
        """Format: {{ include_raw('<template_name>') }}"""
        return Markup(loader.get_source(env, name)[0])

    env.globals['include_raw'] = include_raw

    for file in kwargs['files']:
        tmpl = env.get_template(file)
        with codecs.open(os.path.join(args[0], (os.path.splitext(file)[0])), 'w', 'utf-8') as f:
            f.write(tmpl.render(**kwargs['jinja_values']))


def get_type_func(tpe):
    types = {'python_mod_req': python_mod_req, 'splitter': splitter}
    return types[tpe]
