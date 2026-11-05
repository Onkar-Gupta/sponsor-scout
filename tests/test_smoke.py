import yaml

import sponsor_scout


def test_version_is_set():
    assert sponsor_scout.__version__


def test_config_names_the_frozen_base_model():
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg["base_model"] == "microsoft/Phi-4-mini-instruct"
