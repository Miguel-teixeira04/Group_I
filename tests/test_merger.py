"""Unit tests for merge behavior in app.merger."""

import importlib
import re
import sys
import types
from types import ModuleType
from unittest.mock import Mock
import pandas as pd
import pytest


@pytest.fixture
def merger_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
	"""Import `app.merger` safely by mocking import-time file reads.

	The production module currently executes example code during import. This
	fixture stubs geopandas and pandas readers so importing the module remains
	deterministic in tests.
	"""
	fake_geopandas = types.SimpleNamespace(
		GeoDataFrame=pd.DataFrame,
		read_file=lambda *_args, **_kwargs: pd.DataFrame(
			{"ISO_A3": ["PRT"], "geometry": [None]}
		),
	)

	monkeypatch.setitem(sys.modules, "geopandas", fake_geopandas)
	monkeypatch.setattr(
		pd,
		"read_csv",
		lambda *_args, **_kwargs: pd.DataFrame({"Code": ["PRT"], "value": [1]}),
	)

	if "app.merger" in sys.modules:
		del sys.modules["app.merger"]

	return importlib.import_module("app.merger")


def test_merge_dataframes_basic_left_join_and_filters_codes(
	merger_module: ModuleType,
) -> None:
	"""Merge keeps left rows, filters invalid codes, and aligns expected values."""
	# Arrange
	geopd = pd.DataFrame(
		{
			"ISO_A3": ["PRT", "ESP", "FRA"],
			"geometry": [Mock(), Mock(), Mock()],
		}
	)
	df = pd.DataFrame(
		{
			"Code": [" PRT ", "ESP", "OWID_WRL", "US"],
			"value": [10, 20, 999, 123],
		}
	)

	# Act
	result = merger_module.merge_dataframes(geopd, df)

	# Assert
	assert isinstance(result, pd.DataFrame)
	assert list(result["ISO_A3"]) == ["PRT", "ESP", "FRA"]
	assert len(result) == 3
	assert "Code" in result.columns
	assert "value" in result.columns
	assert result.loc[result["ISO_A3"] == "PRT", "value"].iloc[0] == 10
	assert result.loc[result["ISO_A3"] == "ESP", "value"].iloc[0] == 20
	assert pd.isna(result.loc[result["ISO_A3"] == "FRA", "value"].iloc[0])


@pytest.mark.parametrize(
	"geopd,df,expected_message",
	[
		(
			pd.DataFrame({"country": ["PRT"]}),
			pd.DataFrame({"Code": ["PRT"]}),
			"world doesn't have 'ISO_A3'",
		),
		(
			pd.DataFrame({"ISO_A3": ["PRT"]}),
			pd.DataFrame({"country_code": ["PRT"]}),
			"df doesn't have 'Code' (ISO-3)",
		),
	],
)
def test_merge_dataframes_raises_for_missing_required_columns(
	merger_module: ModuleType,
	geopd: pd.DataFrame,
	df: pd.DataFrame,
	expected_message: str,
) -> None:
	"""Raise ValueError when required columns are missing from either input."""
	

	
	with pytest.raises(ValueError, match=re.escape(expected_message)):
		merger_module.merge_dataframes(geopd, df)
