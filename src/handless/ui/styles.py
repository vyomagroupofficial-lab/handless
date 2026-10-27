"""Cream & Paper Theme Stylesheet and Palette for Vyoma Handless.

Inspired by premium stationery, warm paper textures, and elegant typography.
Avoids generic dark dashboards in favor of a bespoke tactile aesthetic.
"""

from __future__ import annotations

CREAM_PALETTE = {
    "bg_main": "#FDF6EC",
    "bg_card": "#FEFCF7",
    "border": "#E8DFD0",
    "ink_primary": "#2C2418",
    "ink_secondary": "#6B5D4F",
    "ink_muted": "#9C8E80",
    "accent_terracotta": "#C4704B",
    "accent_terracotta_hover": "#B3603B",
    "accent_sage": "#7B9E7B",
    "accent_soft_blue": "#6B8CAE",
    "accent_error": "#C45B5B",
    "shadow": "rgba(44, 36, 24, 0.08)",
}

VOICE_BAR_QSS = """
QWidget#voiceBarContainer {
    background-color: #FDF6EC;
    border: 1px solid #E8DFD0;
    border-radius: 20px;
}

QLabel {
    color: #2C2418;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
}

QLabel#transcriptLabel {
    color: #2C2418;
    font-size: 13px;
    font-weight: 600;
}

QLabel#statusLabel {
    color: #6B5D4F;
    font-size: 11px;
    font-style: italic;
}

QPushButton#micButton {
    background-color: #FEFCF7;
    border: 1.5px solid #E8DFD0;
    border-radius: 22px;
    font-size: 18px;
    color: #6B5D4F;
}

QPushButton#micButton:hover {
    background-color: #F7EFE4;
    border-color: #C4704B;
    color: #C4704B;
}

QPushButton#micButton[listening="true"] {
    background-color: #C4704B;
    border: 2px solid #B3603B;
    color: #FEFCF7;
}

QPushButton#iconButton {
    background-color: transparent;
    border: none;
    border-radius: 12px;
    color: #6B5D4F;
    font-size: 13px;
    padding: 4px;
}

QPushButton#iconButton:hover {
    background-color: #E8DFD0;
    color: #2C2418;
}

QPushButton#stopButton {
    background-color: #FEFCF7;
    border: 1px solid #E8DFD0;
    border-radius: 12px;
    color: #C45B5B;
    font-size: 12px;
    font-weight: bold;
    padding: 3px 8px;
}

QPushButton#stopButton:hover {
    background-color: #C45B5B;
    color: #FFFFFF;
}
"""

SETTINGS_PANEL_QSS = """
QDialog {
    background-color: #FDF6EC;
    color: #2C2418;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}

QTabWidget::pane {
    border: 1px solid #E8DFD0;
    border-radius: 8px;
    background-color: #FEFCF7;
    top: -1px;
    padding: 14px;
}

QTabBar::tab {
    background-color: #F3EBDD;
    border: 1px solid #E8DFD0;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 18px;
    margin-right: 4px;
    color: #6B5D4F;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #FEFCF7;
    color: #2C2418;
    font-weight: 600;
    border-bottom: 1px solid #FEFCF7;
}

QTabBar::tab:hover:!selected {
    background-color: #EDE3D4;
}

QLabel {
    color: #2C2418;
    font-size: 12px;
}

QLabel#headingLabel {
    font-size: 14px;
    font-weight: 700;
    color: #2C2418;
    margin-bottom: 6px;
}

QLabel#helpLabel {
    color: #6B5D4F;
    font-size: 11px;
}

QLineEdit, QComboBox, QSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #D8CFC0;
    border-radius: 6px;
    padding: 7px 10px;
    color: #2C2418;
    font-size: 12px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1.5px solid #C4704B;
}

QPushButton#primaryButton {
    background-color: #C4704B;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton#primaryButton:hover {
    background-color: #B3603B;
}

QPushButton#secondaryButton {
    background-color: #FEFCF7;
    border: 1px solid #E8DFD0;
    border-radius: 6px;
    padding: 8px 16px;
    color: #2C2418;
    font-weight: 500;
    font-size: 12px;
}

QPushButton#secondaryButton:hover {
    background-color: #F3EBDD;
}

QCheckBox {
    color: #2C2418;
    font-size: 12px;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #D8CFC0;
    border-radius: 4px;
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    background-color: #C4704B;
    border-color: #C4704B;
}

QGroupBox {
    border: 1px solid #E8DFD0;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 16px;
    font-weight: 600;
    color: #2C2418;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 10px;
}
"""
