import pytest
from handless.actions.launcher import ApplicationLauncher, COMMON_APP_MAP, WEB_APP_MAP


def test_launcher_initialization():
    launcher = ApplicationLauncher()
    assert isinstance(launcher._start_menu_cache, dict)
    assert isinstance(launcher._app_paths_cache, dict)
    assert isinstance(launcher._start_apps_cache, dict)


def test_launcher_known_web_app():
    launcher = ApplicationLauncher()
    executed_uris = []
    def mock_uri(uri):
        executed_uris.append(uri)
        return uri != "whatsapp:"

    launcher._execute_uri = mock_uri

    assert launcher.launch("youtube") is True
    assert "https://www.youtube.com" in executed_uris

    assert launcher.launch("open whatsapp") is True
    assert "https://web.whatsapp.com" in executed_uris


def test_launcher_start_apps_fuzzy():
    launcher = ApplicationLauncher()
    launched_apps = []
    launcher._execute_start_app = lambda app_id: launched_apps.append(app_id) or True

    launcher._start_apps_cache["discord"] = "com.squirrel.Discord.Discord"
    assert launcher.launch("discord") is True
    assert launched_apps == ["com.squirrel.Discord.Discord"]


def test_launcher_app_paths():
    launcher = ApplicationLauncher()
    targets = []
    launcher._execute_target = lambda path: targets.append(path) or True

    launcher._app_paths_cache["customapp"] = "C:\\Tools\\customapp.exe"
    assert launcher.launch("customapp") is True
    assert targets == ["C:\\Tools\\customapp.exe"]


def test_launcher_empty_and_invalid():
    launcher = ApplicationLauncher()
    assert launcher.launch("") is False
    assert launcher.launch("   ") is False
