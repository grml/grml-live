import datetime

import pytest

from ..main import _build_iso_volid, source_date_epoch_datetime


def test_source_date_epoch_datetime_valid(monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1")
    assert source_date_epoch_datetime() == datetime.datetime(1970, 1, 1, 0, 0, 1, tzinfo=datetime.UTC)


@pytest.mark.parametrize("value", ["asdf", "-1", "1.1", "0", " 1", "1 ", "+10", "100_000", "inf", "1e30"])
def test_source_date_epoch_datetime_invalid(monkeypatch, value):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", value)
    with pytest.raises(ValueError):
        source_date_epoch_datetime()


@pytest.mark.parametrize("value", ["", " "])
def test_source_date_epoch_datetime_empty(monkeypatch, value):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", value)
    assert source_date_epoch_datetime() is None


@pytest.mark.parametrize(
    "name,version,expected",
    [
        ("grml", "0.0.1", "grml_0.0.1"),
        ("grml-small-amd64", "2099.77", "grml-small-amd64_2099.77"),
        ("grml-small-amd64", "daily20260905build842testing", "grm_daily20260905build842testing"),
    ],
)
def test__build_iso_volid(name, version, expected):
    assert _build_iso_volid(name, version) == expected
