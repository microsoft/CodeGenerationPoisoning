import yaml

from .file import MacroFile


class MacroYAML(MacroFile):

    def __init__(self, lock, filename: str, dump=True):
        super().__init__(lock, filename, dump)
        with open(self.dumped or self._filename, 'r') as f:
            lines = f.readlines()[1:]
            self._data = yaml.load('\n'.join(lines), Loader=yaml.SafeLoader)

    def _flush(self):
        with open(self._filename, 'w') as f:
            f.write('%YAML:1.0\n')
            f.write(yaml.dump(self._data, Dumper=yaml.SafeDumper))
