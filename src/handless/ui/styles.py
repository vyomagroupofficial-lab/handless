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

QLineEdit#cmdInput {
    background-color: #FEFCF7;
    border: 1px solid #E8DFD0;
    border-radius: 8px;
    padding: 3px 8px;
    color: #2C2418;
    font-size: 12px;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
}

QLineEdit#cmdInput:focus {
    border: 1px solid #C4704B;
    background-color: #FFFFFF;
}

QLineEdit#cmdInput::placeholder {
    color: #9C8E80;
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

QPushButton#modeButton {
    background-color: #FEFCF7;
    border: 1px solid #E8DFD0;
    border-radius: 12px;
    color: #6B5D4F;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
}

QPushButton#modeButton:hover {
    background-color: #F7EFE4;
    border-color: #C4704B;
    color: #2C2418;
}

QPushButton#modeButton[dictation="true"] {
    background-color: #7C3AED;
    border: 1px solid #6D28D9;
    color: #FFFFFF;
}

QWidget#voiceBarContainer[dictation="true"] {
    background-color: #FDF6EC;
    border: 1.5px solid #8B5CF6;
    border-radius: 20px;
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

SIDEBAR_QSS = """
/* Vyoma Handless Modern AI Sidebar Stylesheet - Luxury Cream & Tactile */

QWidget#sidebarContainer {
    background-color: #FBFBF9;
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-top: 1.5px solid rgba(255, 255, 255, 0.95);
    border-radius: 26px;
}

/* Left Navigation Rail */
QWidget#leftNavRail {
    background-color: transparent;
    border-right: 1px solid #ECEAE3;
    padding: 12px 0px;
}

QPushButton.navRailBtn {
    background-color: transparent;
    border: none;
    border-radius: 11px;
    padding: 7px;
}

QPushButton.navRailBtn:hover {
    background-color: #F0EEE7;
}

QPushButton.navRailBtnActive {
    background-color: #18181B;
    border: none;
    border-radius: 11px;
    padding: 7px;
}

QPushButton.navRailBtnActive:hover {
    background-color: #27272A;
}

QLabel#navAvatarBadge {
    background-color: #EAE7DE;
    color: #18181B;
    font-size: 13px;
    font-weight: 700;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    border-radius: 16px;
    qproperty-alignment: AlignCenter;
}

/* Header */
QWidget#headerContainer {
    background-color: transparent;
    border-bottom: 1px solid #ECEAE3;
    padding: 8px 16px;
}

QLabel#headerBrandTitle {
    color: #18181B;
    font-size: 17px;
    font-weight: 800;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    letter-spacing: -0.5px;
}

QLabel#headerBrandSubtitle {
    color: #71717A;
    font-size: 10.5px;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-weight: 500;
}

QWidget#readyStatusPill {
    background-color: #F4F3EE;
    border: 1px solid #E5E3DC;
    border-radius: 12px;
    padding: 3px 8px;
}

QLabel#readyStatusText {
    color: #18181B;
    font-size: 11.5px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}

QPushButton#headerButton {
    background-color: transparent;
    border: none;
    border-radius: 14px;
    padding: 4px;
}

QPushButton#headerButton:hover {
    background-color: #EFECE6;
}

QPushButton#headerButton:pressed {
    background-color: #E2DFD7;
}

/* Hero Section */
QWidget#heroContainer {
    background-color: transparent;
    padding: 10px 4px 6px 4px;
}

QLabel#heroTitle {
    color: #18181B;
    font-size: 26px;
    font-weight: 600;
    line-height: 1.15;
    font-family: 'Georgia', 'Playfair Display', 'Times New Roman', serif;
}

QLabel#heroSubtitle {
    color: #71717A;
    font-size: 11.5px;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    line-height: 1.45;
}

/* Unified Interaction Card */
QWidget#promptContainerCard {
    background-color: #F5F4EE;
    border: 1px solid #E7E4DA;
    border-radius: 18px;
    padding: 10px;
}

QWidget#promptInputRow {
    background-color: #FFFFFF;
    border: 1px solid #E2DFD4;
    border-radius: 18px;
    padding: 4px 6px 4px 10px;
}

QWidget#promptInputRow:focus-within {
    border-color: #18181B;
}

QLineEdit#heroPromptInput {
    background-color: transparent;
    border: none;
    color: #18181B;
    font-size: 12px;
    font-family: 'Segoe UI', -apple-system, sans-serif;
}

QLineEdit#heroPromptInput::placeholder {
    color: #9CA3AF;
}

QPushButton#promptAttachBtn {
    background-color: transparent;
    border: none;
    border-radius: 12px;
    padding: 3px;
}

QPushButton#promptAttachBtn:hover {
    background-color: #F0ECE2;
}

QPushButton#promptSendBtn {
    background-color: #18181B;
    border: none;
    border-radius: 15px;
    padding: 4px;
}

QPushButton#promptSendBtn:hover {
    background-color: #27272A;
}

QPushButton#promptSendBtn:pressed {
    background-color: #09090B;
}

/* Quick Action Cards */
QWidget#quickCardsGrid {
    background-color: transparent;
}

QPushButton.quickCard {
    background-color: #FFFFFF;
    border: 1px solid #E4E0D5;
    border-radius: 12px;
    min-height: 66px;
    max-height: 72px;
    padding: 6px 2px 6px 2px;
    text-align: center;
}

QPushButton.quickCard:hover {
    background-color: #FAF9F5;
    border-color: #D3CEBF;
}

QPushButton.quickCard:pressed {
    background-color: #F0ECE1;
}

QLabel.quickCardTitle {
    color: #18181B;
    font-size: 10px;
    font-weight: 600;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    qproperty-alignment: AlignCenter;
}

/* Recent Activity Feed */
QWidget#recentSectionContainer {
    background-color: transparent;
    padding: 8px 2px;
}

QLabel#recentSectionTitle {
    color: #18181B;
    font-size: 14px;
    font-weight: 700;
    font-family: 'Segoe UI', -apple-system, sans-serif;
}

QPushButton#recentSeeAllBtn {
    background-color: transparent;
    border: none;
    color: #71717A;
    font-size: 11.5px;
    font-weight: 500;
    font-family: 'Segoe UI', sans-serif;
    padding: 2px 4px;
}

QPushButton#recentSeeAllBtn:hover {
    color: #18181B;
    text-decoration: underline;
}

QWidget.recentItemRow {
    background-color: transparent;
    border: none;
    border-radius: 10px;
    padding: 6px 6px;
}

QWidget.recentItemRow:hover {
    background-color: #F2EFE8;
}

QWidget.recentIconContainer {
    background-color: #F5F3EC;
    border: 1px solid #ECE8DE;
    border-radius: 10px;
}

QLabel.recentItemTitle {
    color: #18181B;
    font-size: 12.5px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}

QLabel.recentItemTime {
    color: #71717A;
    font-size: 11px;
    font-family: 'Segoe UI', sans-serif;
}

/* Bottom Status Pill */
QWidget#footerPillContainer {
    background-color: #FAF9F6;
    border: 1px solid #EBE7DD;
    border-radius: 20px;
    padding: 6px 14px;
}

QLabel#footerCommandModeLabel {
    color: #18181B;
    font-size: 12px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}

QLabel#footerListeningBadge {
    color: #18181B;
    font-size: 11.5px;
    font-weight: 500;
    font-family: 'Segoe UI', sans-serif;
}

/* Scroll Area & Chat Stream */
QStackedWidget {
    background-color: transparent;
}

QScrollArea#chatScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea#chatScrollArea > QWidget {
    background-color: transparent;
}

QWidget#chatStreamContainer, QWidget#dashboardContent {
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 6px 0 6px 0;
}

QScrollBar::handle:vertical {
    background: rgba(148, 163, 184, 0.45);
    min-height: 28px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(100, 116, 139, 0.75);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Welcome / Greeting Card */
QWidget#greetingCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF,
        stop:1 #F8FAFC);
    border: 1px solid rgba(0, 0, 0, 0.07);
    border-top: 1px solid rgba(255, 255, 255, 0.95);
    border-radius: 14px;
}

QLabel#greetingTitle {
    color: #0F172A;
    font-size: 14.5px;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}

QLabel#greetingBody {
    color: #334155;
    font-size: 12.5px;
    line-height: 1.5;
    font-family: 'Segoe UI', sans-serif;
}

/* Quick Suggestion Chips */
QPushButton#chipButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:1 #F1F5F9);
    border: 1px solid #E2E8F0;
    border-top: 1px solid rgba(255, 255, 255, 0.9);
    border-radius: 12px;
    color: #334155;
    font-size: 11px;
    font-weight: 600;
    padding: 5px 11px;
}

QPushButton#chipButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #F8FAFC, stop:1 #E2E8F0);
    border-color: #CBD5E1;
    color: #0F172A;
}

/* User Message Bubble */
QWidget#userBubble {
    background-color: #FFFFFF;
    border: 1px solid #EBE7DD;
    border-radius: 14px;
    border-bottom-right-radius: 4px;
}

QLabel#userBubbleText {
    color: #18181B;
    font-size: 12.5px;
    line-height: 1.45;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 450;
}

/* Mini Floating Toolbar on Message */
QWidget#messageToolbar {
    background: #18181B;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 2px 4px;
}

QPushButton#toolButton {
    background: transparent;
    border: none;
    padding: 3px 5px;
    border-radius: 5px;
}

QPushButton#toolButton:hover {
    background-color: rgba(255, 255, 255, 0.18);
}

QPushButton#toolButton:pressed {
    background-color: rgba(255, 255, 255, 0.28);
}

/* Assistant Message Bubble */
QWidget#assistantBubble {
    background-color: #F6F4ED;
    border: 1px solid #ECE7DC;
    border-radius: 14px;
    border-bottom-left-radius: 4px;
}

QLabel#assistantBubbleText {
    color: #18181B;
    font-size: 12.5px;
    line-height: 1.45;
    font-family: 'Segoe UI', sans-serif;
}

/* Dark Rich Action Card */
QWidget#actionCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #1E293B,
        stop:1 #0F172A);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-top: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 11px;
    padding: 9px 13px;
}

QLabel#actionCardTitle {
    color: #F8FAFC;
    font-size: 12.5px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}

QLabel#actionCardSubtitle {
    color: #94A3B8;
    font-size: 10.5px;
    font-family: 'Segoe UI', sans-serif;
}

QPushButton#actionCardBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 0.18),
        stop:1 rgba(255, 255, 255, 0.08));
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 13px;
    padding: 4px 10px;
}

QPushButton#actionCardBtn:hover {
    background-color: rgba(255, 255, 255, 0.28);
    border-color: rgba(255, 255, 255, 0.35);
}

QPushButton#actionCardBtn:pressed {
    background-color: rgba(255, 255, 255, 0.38);
}

/* Bottom Input Area (Legacy compatibility) */
QWidget#inputPill {
    background-color: #FFFFFF;
    border: 1.5px solid #E2E8F0;
    border-radius: 23px;
    padding: 4px 10px;
}

QLineEdit#sidebarInput {
    background-color: transparent;
    border: none;
    color: #0F172A;
    font-size: 13px;
    font-family: 'Segoe UI', sans-serif;
}

QLineEdit#sidebarInput::placeholder {
    color: #94A3B8;
}

QPushButton#micCircleBtn {
    background: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 17px;
}

QPushButton#micCircleBtn:hover {
    background-color: #EEF2F6;
}

QPushButton#micCircleBtn[listening="true"] {
    background: #18181B;
    border: 1.5px solid #000000;
}

/* Footer / Mode Bar (Legacy compatibility) */
QPushButton#modePill {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 11px;
    color: #334155;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 9px;
}

QPushButton#modePill:hover {
    background-color: #F8FAFC;
}

QPushButton#stopPill {
    background-color: #FEF2F2;
    border: 1px solid #FECACA;
    border-radius: 11px;
    color: #DC2626;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 9px;
}

QPushButton#stopPill:hover {
    background-color: #FCA5A5;
}

"""
