from chaos_test import YamlChaosFile
import tempfile
import pytest
import yaml
from werkzeug.utils import ImportStringError

def get_temp_file(content):
    f = tempfile.NamedTemporaryFile("w")
    f.write(content)
    f.seek(0)
    return f

def test_no_entry_point(_pytest):
    f = get_temp_file("""
    entry-point1: factory
    """)    
    
    if hasattr(YamlChaosFile, "from_parent"):
        from py._path.local import LocalPath
        plugin = YamlChaosFile.from_parent(_pytest.request.node, fspath=LocalPath(f.name))
    else:
        plugin = YamlChaosFile(f.name, _pytest.request.node)

    with pytest.raises(AssertionError, match="Define entry point to run chaos testing."):
        plugin.collect()
    f.close()

def test_entry_point_detected(_pytest):
    f = get_temp_file("""
    entry-point: factory
    """)
    if hasattr(YamlChaosFile, "from_parent"):
        from py._path.local import LocalPath
        plugin = YamlChaosFile.from_parent(_pytest.request.node, fspath=LocalPath(f.name))
    else:
        plugin = YamlChaosFile(f.name, _pytest.request.node)

    with pytest.raises(ImportStringError):
        plugin.collect()
    f.close()

def test_scenario_collection(_pytest):
    data = """
    acts:
        - test: a
        - test: b
    """
    f = get_temp_file(data)
    assert len(YamlChaosFile.extract_acts(yaml.safe_load(data))) == 2
    f.close()
