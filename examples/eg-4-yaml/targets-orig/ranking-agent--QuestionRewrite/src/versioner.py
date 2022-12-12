import yaml


def version_spec(new_version: str):
    """
    puts new version info in the open api spec.

    :param new_version: str - the new version
    :return: nothing
    """

    # load the open api spec
    with open('swagger_ui/openapi.yml', 'r') as fp:
        the_spec = yaml.load(fp, Loader=yaml.FullLoader)

    # update the version
    the_spec['info']['version'] = new_version

    with open('swagger_ui/openapi.yml', 'w') as fp:
        # write the spec back out
        yaml.dump(the_spec, fp)
