"""Tests for the first-run setup window and the responsive layout helpers."""

import pytest
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QWidget

from handless.config import AppConfig
from handless.ui import onboarding
from handless.ui.onboarding import OnboardingWizard, should_run_onboarding
from handless.ui.responsive import FlowLayout, clear_inherited_frame_borders, fit_to_width, flow_pill_rows


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_should_run_onboarding(monkeypatch):
    cfg = AppConfig()
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("HANDLESS_SKIP_ONBOARDING", raising=False)
    assert should_run_onboarding(cfg, []) is True
    cfg.ui.onboarding_completed = True
    assert should_run_onboarding(cfg, []) is False
    assert should_run_onboarding(cfg, ["--setup"]) is True
    cfg.ui.onboarding_completed = False
    monkeypatch.setenv("HANDLESS_SKIP_ONBOARDING", "1")
    assert should_run_onboarding(cfg, []) is False


def test_launch_command_runs_in_background():
    assert onboarding.launch_command().endswith("--background")


def test_wizard_finish_saves_choices(qapp, monkeypatch):
    saved = []
    startup = []
    monkeypatch.setattr(onboarding, "save_config", lambda cfg: saved.append(cfg))
    monkeypatch.setattr(onboarding, "set_launch_at_startup", lambda enabled: startup.append(enabled))
    monkeypatch.setattr(onboarding, "is_launch_at_startup_enabled", lambda: False)

    cfg = AppConfig()
    wizard = OnboardingWizard(cfg)
    assert wizard.stack.count() == 6
    for _ in range(5):
        if wizard.stack.currentIndex() == 3:
            wizard.groq_input.clear()
            wizard.gemini_input.clear()
        wizard._next()
    assert wizard.next_btn.text() == "Launch Handless"
    wizard.dock_left_cb.setChecked(True)
    wizard.startup_cb.setChecked(False)
    wizard._next()

    assert cfg.ui.onboarding_completed is True
    assert cfg.ui.sidebar_position == "left"
    assert saved and startup == [False]


def test_flow_layout_wraps(qapp):
    host = QWidget()
    flow = FlowLayout(host, h_spacing=4, v_spacing=4)
    for i in range(6):
        btn = QPushButton(f"Category {i}")
        btn.setFixedSize(80, 24)
        flow.addWidget(btn)
    assert flow.heightForWidth(1000) == 24
    assert flow.heightForWidth(170) > 24


def test_flow_pill_rows_and_fit_to_width(qapp):
    root = QWidget()
    row = QWidget(root)
    layout = QHBoxLayout(row)
    for name in ("All", "Apps", "Files", "Web", "System"):
        layout.addWidget(QPushButton(name))
    layout.addStretch(1)
    label = QLabel("A fairly long description that should wrap at sidebar width", root)

    assert flow_pill_rows(root) == 1
    assert isinstance(row.layout(), FlowLayout)
    fit_to_width(root)
    assert label.wordWrap()


def test_clear_inherited_frame_borders(qapp):
    from PySide6.QtWidgets import QFrame

    card = QFrame()
    card.setStyleSheet("QFrame { border: 1px solid #ECE7DC; }")
    icon = QLabel(card)
    styled = QLabel(card)
    styled.setStyleSheet("color: red;")
    clear_inherited_frame_borders(card)
    assert "border: none" in icon.styleSheet()
    assert styled.styleSheet().startswith("color: red;") and "border: none" in styled.styleSheet()
