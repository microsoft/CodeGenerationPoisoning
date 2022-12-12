from collections import OrderedDict

import presc
from presc.configuration import PrescConfig

from confuse import Configuration
import yaml


CONFIG_OVERRIDE_FILE = """
report:
    title: ABC
evaluations:
  conditional_metric:
    computation:
      num_bins: 3
"""


def test_package_config():
    # Check that package-wide config has been initialized and some expected
    # default settings are present.
    assert isinstance(presc.global_config, PrescConfig)
    assert isinstance(presc.global_config.settings, Configuration)
    assert presc.global_config["report"]["title"].get()
    assert isinstance(
        presc.global_config["evaluations"]["conditional_metric"]["computation"].get(),
        dict,
    )


def test_presc_config(tmp_path):
    conf = PrescConfig()

    # Default settings have been loaded.
    # This is raise an error if the value is not defined in the config
    default_title = conf["report"]["title"].get()
    default_cm_comp = conf["evaluations"]["conditional_metric"]["computation"].get()

    assert default_title is not None
    assert isinstance(default_cm_comp, dict)

    # Overriding settings with another config file
    override_file = tmp_path / "config_override.yaml"
    with open(override_file, "w") as f:
        f.write(CONFIG_OVERRIDE_FILE)

    conf.update_from_file(override_file)
    assert (
        conf["evaluations"]["conditional_metric"]["computation"]["num_bins"].get(int)
        == 3
    )
    assert conf["report"]["title"].get(str) == "ABC"
    assert conf["evaluations"]["conditional_metric"]["computation"] != default_cm_comp

    # Overriding settings manually.
    conf.set({"report": {"title": "ABCDEF", "author": "Xyz"}})
    assert conf["report"]["title"].get() == "ABCDEF"
    assert conf["report"]["author"].get() == "Xyz"
    conf.set(
        {
            "evaluations.conditional_metric.computation.num_bins": 7,
            "evaluations.conditional_metric.columns_include": ["a", "b"],
            "evaluations.conditional_metric.computation.columns.a.num_bins": 5,
        }
    )
    assert (
        conf["evaluations"]["conditional_metric"]["computation"]["num_bins"].get(int)
        == 7
    )
    assert conf["evaluations"]["conditional_metric"]["columns_include"].get(list) == [
        "a",
        "b",
    ]
    assert (
        conf["evaluations"]["conditional_metric"]["computation"]["columns"]["a"][
            "num_bins"
        ].get(int)
        == 5
    )

    # Reverting back to defaults
    conf.reset_defaults()
    assert conf["report"]["title"].get() == default_title
    assert (
        conf["evaluations"]["conditional_metric"]["computation"].get()
        == default_cm_comp
    )

    # dump() should give valid YAML. Parsing should not fail.
    yaml.load(conf.dump(), Loader=yaml.FullLoader)

    # flatten() should give an OrderedDict
    assert isinstance(conf.flatten(), OrderedDict)


def test_local_config():
    local_conf = PrescConfig(presc.global_config)

    # Local config changes don't carry through to underlying config
    orig_dump = presc.global_config.dump()
    local_conf.set({"report.title": "ABC"})
    local_conf.set({"report": {"author": "XYZ"}})
    assert local_conf["report"]["title"].get() == "ABC"
    assert local_conf["report"]["author"].get() == "XYZ"
    assert presc.global_config.dump() == orig_dump

    # Underlying config changes are picked up in local config
    assert local_conf["report"]["evaluations_include"].get() == "*"
    presc.global_config.set({"report.evaluations_include": "a"})
    assert local_conf["report"]["evaluations_include"].get() == "a"

    # Local configs can be nested
    orig_dump = presc.global_config.dump()
    lc_dump = local_conf.dump()
    local_conf2 = PrescConfig(local_conf)
    local_conf2.set({"report.title": "IJK"})
    assert local_conf2["report"]["title"].get() == "IJK"
    assert local_conf2["report"]["author"].get() == "XYZ"
    assert presc.global_config.dump() == orig_dump
    assert local_conf.dump() == lc_dump

    local_conf.set({"report": {"author": "PQR"}})
    assert local_conf2["report"]["title"].get() == "IJK"
    assert local_conf2["report"]["author"].get() == "PQR"
    assert presc.global_config.dump() == orig_dump
