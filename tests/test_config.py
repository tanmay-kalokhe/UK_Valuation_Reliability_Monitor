"""Checks that the project configuration loads and holds sensible values."""

from valuation_monitor.config import load_config


def test_config_loads():
    config = load_config()
    assert config["project"]["package"] == "valuation_monitor"


def test_target_coverage_is_a_probability():
    coverage = load_config()["intervals"]["target_coverage"]
    assert 0 < coverage < 1
