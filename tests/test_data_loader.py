"""Unit tests for dataset downloading behavior in app.data_loader."""

import os
from unittest.mock import Mock, mock_open, patch

import pytest

from app.data_loader import download_datasets


@pytest.fixture
def expected_download_files():
    """Return the expected filenames written by `download_datasets`."""
    return [
        "annual_change_forest_area.csv",
        "annual_deforestation.csv",
        "share_protected_land.csv",
        "share_degraded_land.csv",
        "share_covered_forest_land.csv",
        "ne_110m_admin_0_countries.zip",
    ]


@patch("builtins.open", new_callable=mock_open)
@patch("app.data_loader.requests.get")
def test_download_datasets_downloads_all_files(
    mock_get, mock_file, expected_download_files
):
    """Download all resources, write all files, and check each response status."""
    # Arrange
    responses = []
    for idx in range(len(expected_download_files)):
        response = Mock()
        response.content = f"payload-{idx}".encode()
        response.raise_for_status = Mock()
        responses.append(response)

    mock_get.side_effect = responses

    # Act
    download_datasets("downloads")

    # Assert
    assert mock_get.call_count == 6
    assert mock_file.call_count == 6

    opened_paths = [args[0] for args, _kwargs in mock_file.call_args_list]
    assert opened_paths == [
        os.path.join("downloads", filename) for filename in expected_download_files
    ]

    for response in responses:
        response.raise_for_status.assert_called_once()


@pytest.mark.parametrize("download_dir", ["downloads", "custom_dir"])
@patch("builtins.open", new_callable=mock_open)
@patch("app.data_loader.requests.get")
def test_download_datasets_uses_provided_directory(
    mock_get, mock_file, download_dir, expected_download_files
):
    """Use the provided download directory when composing output file paths."""
    # Arrange
    response = Mock()
    response.content = b"data"
    response.raise_for_status = Mock()
    mock_get.side_effect = [response] * 6

    # Act
    download_datasets(download_dir)

    # Assert
    first_open_path = mock_file.call_args_list[0].args[0]
    last_open_path = mock_file.call_args_list[-1].args[0]

    assert first_open_path == os.path.join(download_dir, expected_download_files[0])
    assert last_open_path == os.path.join(download_dir, expected_download_files[-1])
