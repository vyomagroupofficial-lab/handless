from unittest.mock import MagicMock, patch
import pytest

from scripts.setup_flauinspect import is_installed, launch_tool, main, download_and_extract


def test_is_installed_reflects_file_existence():
    with patch("pathlib.Path.is_file", return_value=True):
        assert is_installed() is True

    with patch("pathlib.Path.is_file", return_value=False):
        assert is_installed() is False


def test_main_check_flag():
    with patch("scripts.setup_flauinspect.is_installed", return_value=True):
        with patch("sys.argv", ["setup_flauinspect.py", "--check"]):
            assert main() == 0

    with patch("scripts.setup_flauinspect.is_installed", return_value=False):
        with patch("sys.argv", ["setup_flauinspect.py", "--check"]):
            assert main() == 1


def test_launch_tool_success():
    with patch("scripts.setup_flauinspect.is_installed", return_value=True):
        with patch("subprocess.Popen") as mock_popen:
            res = launch_tool()
            assert res is True
            mock_popen.assert_called_once()


def test_launch_tool_not_installed():
    with patch("scripts.setup_flauinspect.is_installed", return_value=False):
        res = launch_tool()
        assert res is False


def test_download_and_extract_skips_if_already_installed():
    with patch("scripts.setup_flauinspect.is_installed", return_value=True):
        res = download_and_extract(force=False)
        assert res is True
