import yaml


class ConfigurationParser:
    def __init__(self, conf_path='.conf'):
        with open(f'{conf_path}/projects.yaml', 'r') as f:
            self.projects = self.validate_projects(yaml.load(f, Loader=yaml.FullLoader))

    def validate_projects(self, conf):
        if conf['version'] not in ['1']:
            raise KeyError('Invalid version number, should be string!')
        if 'projects' not in conf:
            raise KeyError('Projects not specified.')

        for project_name, project_conf in conf['projects'].items():
            if 'repository' not in project_conf:
                raise KeyError('Missing project repository!')
        return conf

    def get_project(self, project_name):
        return self.projects['projects'][project_name]
