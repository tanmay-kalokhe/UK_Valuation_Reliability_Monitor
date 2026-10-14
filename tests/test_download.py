"""Checks for the download plan and the safe zip extraction."""

import zipfile

import pytest

from valuation_monitor.config import load_config
from valuation_monitor.download import plan, safe_extract


def test_plan_covers_every_group():
    jobs = plan(load_config())
    assert set(jobs) == {"price_paid", "house_price_index", "postcode_lookup", "boundaries"}
    years = load_config()["sources"]["price_paid"]["years"]
    assert len(jobs["price_paid"]) == len(years) + 1  # yearly files plus the monthly update


def test_safe_extract_rejects_path_traversal(tmp_path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escaped.txt", "should not be written")
    with pytest.raises(ValueError):
        safe_extract(archive, tmp_path / "out")
    assert not (tmp_path / "escaped.txt").exists()


def test_safe_extract_writes_normal_members(tmp_path):
    archive = tmp_path / "good.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("Data/lookup.csv", "pcds,lad\nM1 1AA,E08000003\n")
    extracted = safe_extract(archive, tmp_path / "out")
    assert extracted[0].read_text() == "pcds,lad\nM1 1AA,E08000003\n"
