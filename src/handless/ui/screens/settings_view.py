"""Modern Settings Screen for Vyoma Handless.

Matches the Settings Screen reference design:
- Left Sub-Navigation Menu:
  * AI Models (selected)
  * Voice & Audio
  * Hotkeys
  * Safety
  * Privacy
  * Architecture
  * General
  * Account
  * About
- Right Scrollable Content Pane:
  * Header: "AI Models" + "Configure your AI models and API keys"
  * Category pills: AI Models, Voice & Audio, Hotkeys, Safety, Privacy, Architecture
  * Card 1: Google Gemini AI Studio API Key Card:
      - Google Logo, "Primary" badge, help tooltip, green toggle switch
      - "(Encrypted in Windows Credential Manager)"
      - "Status: Configured & Active in Windows Vault ✓"
      - Password bullets input with "Show" / "Hide" button
      - "Test Store Key" and "Remove Key" buttons
  * Card 2: Groq Cloud High-Capacity Fallback Key Card:
      - Groq badge, "Fallback" badge, help tooltip, green toggle switch
      - "(Encrypted in Windows Credential Manager)"
      - "Status: Groq Key Configured & Active in Windows Vault ✓"
      - Password bullets input with "Show" / "Hide" button
      - "Store Groq Key" and "Remove Key" buttons
  * Card 3: Intelligence Configuration Card:
      - Intelligence Tier (Hybrid, Local, Cloud)
      - Google AI Model (gemini-2.5-flash)
      - Groq Cloud Model (qwen/qwen3.8-27b)
      - Enable Gemini Vision Screen Fallback toggle
  * Card 4: Advanced Options Card:
      - Auto-fallback toggle
      - Model routing toggle
      - Response language dropdown
      - Max response length dropdown
- Bottom Synchronized Prompt Bar + Mode Bar
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from handless.config import AppConfig, load_config, save_config
from handless.security.credentials import (
    delete_gemini_api_key,
    delete_groq_api_key,
    get_gemini_api_key,
    get_groq_api_key,
    has_gemini_api_key,
    has_groq_api_key,
    store_gemini_api_key,
    store_groq_api_key,
)
from handless.ui.icons import (
    SVG_APPS_GRID,
    SVG_ARROW_UP,
    SVG_BRAIN,
    SVG_BRAND_GOOGLE,
    SVG_CHECK,
    SVG_CLOSE,
    SVG_EYE,
    SVG_FILE_TEXT,
    SVG_HELP_CIRCLE,
    SVG_INFO,
    SVG_KEYBOARD,
    SVG_LOCK,
    SVG_PAPERCLIP,
    SVG_REFRESH,
    SVG_SETTINGS,
    SVG_SHIELD,
    SVG_SLIDERS,
    SVG_SPARKLE,
    SVG_STORAGE,
    SVG_USER,
    SVG_VOICE_WAVE,
    get_bot_logo_pixmap,
    render_svg_icon,
    render_svg_pixmap,
)
from .thunder_view import ModernMiniToggle

logger = logging.getLogger(__name__)


class SettingsSubNavButton(QPushButton):
    """Sub-navigation item button in the Settings sidebar menu."""

    def __init__(
        self,
        text: str,
        svg_icon: str,
        is_active: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.text_label = text
        self.svg_icon = svg_icon
        self.is_active = is_active
        self.setText(f"  {text}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(32)
        self._update_style()

    def set_active(self, active: bool) -> None:
        self.is_active = active
        self._update_style()

    def _update_style(self) -> None:
        if self.is_active:
            self.setIcon(render_svg_icon(self.svg_icon, 14, color="#18181B"))
            self.setStyleSheet("""
                QPushButton {
                    background-color: #F3EFE6;
                    color: #18181B;
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 10px;
                    font-size: 11.5px;
                    font-weight: 600;
                }
            """)
        else:
            self.setIcon(render_svg_icon(self.svg_icon, 14, color="#71717A", hover_color="#18181B"))
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #52525B;
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 10px;
                    font-size: 11.5px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #F6F4ED;
                    color: #18181B;
                }
            """)


class SettingsScreenView(QWidget):
    """Complete, modern, high-fidelity Settings Screen for Vyoma Handless."""
    command_submitted = Signal(str)
    voice_toggled = Signal()
    settings_saved = Signal()

    def __init__(self, config: Optional[AppConfig] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsScreenView")
        self.config = config or load_config()

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 6, 10, 8)
        outer_layout.setSpacing(8)

        # Main Split: Left Sub-Nav + Right Content Stack
        split_layout = QHBoxLayout()
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(10)

        # 1. Left Sub-Nav Menu
        self.sub_nav = self._build_sub_nav()
        split_layout.addWidget(self.sub_nav)

        # Vertical Divider Line
        v_line = QFrame(self)
        v_line.setFrameShape(QFrame.Shape.VLine)
        v_line.setStyleSheet("color: #E8E5DC; background-color: #E8E5DC; min-width: 1px; max-width: 1px;")
        split_layout.addWidget(v_line)

        # 2. Right Content Stack
        self.content_stack = QStackedWidget(self)

        # Page 0: AI Models (Matching Reference Image)
        self.ai_page = self._build_ai_models_page()
        self.content_stack.addWidget(self.ai_page)

        # Page 1: Voice & Audio
        self.voice_page = self._wrap_in_scroll(self._build_voice_page())
        self.content_stack.addWidget(self.voice_page)

        # Page 2: Hotkeys
        self.hotkeys_page = self._wrap_in_scroll(self._build_hotkeys_page())
        self.content_stack.addWidget(self.hotkeys_page)

        # Page 3: Safety
        self.safety_page = self._wrap_in_scroll(self._build_safety_page())
        self.content_stack.addWidget(self.safety_page)

        # Page 4: Privacy
        self.privacy_page = self._wrap_in_scroll(self._build_privacy_page())
        self.content_stack.addWidget(self.privacy_page)

        # Page 5: Architecture
        self.arch_page = self._wrap_in_scroll(self._build_architecture_page())
        self.content_stack.addWidget(self.arch_page)

        # Page 6: General
        self.general_page = self._wrap_in_scroll(self._build_general_page())
        self.content_stack.addWidget(self.general_page)

        # Page 7: Account
        self.account_page = self._wrap_in_scroll(self._build_account_page())
        self.content_stack.addWidget(self.account_page)

        # Page 8: About (Featuring Handless Bot Logo)
        self.about_page = self._wrap_in_scroll(self._build_about_page())
        self.content_stack.addWidget(self.about_page)

        split_layout.addWidget(self.content_stack, stretch=1)
        outer_layout.addLayout(split_layout, stretch=1)

        # 3. Bottom Synchronized Prompt Bar
        self.bottom_bar = self._build_bottom_bar()
        outer_layout.addWidget(self.bottom_bar)

        # Select initial page
        self._select_nav_tab(0)

    # -----------------------------------------------------------------------
    # Left Sub-Nav Menu
    # -----------------------------------------------------------------------

    def _build_sub_nav(self) -> QWidget:
        container = QWidget(self)
        container.setFixedWidth(118)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 4, 4, 4)
        layout.setSpacing(3)

        # Section Header: "Settings"
        header = QLabel("Settings", container)
        header.setStyleSheet("font-family: 'Playfair Display', Georgia, serif; font-size: 15.5px; font-weight: 700; color: #18181B; padding-left: 6px; padding-bottom: 6px;")
        layout.addWidget(header)

        self.nav_buttons: List[SettingsSubNavButton] = []

        tabs = [
            ("AI Models", SVG_BRAIN),
            ("Voice & Audio", SVG_VOICE_WAVE),
            ("Hotkeys", SVG_KEYBOARD),
            ("Safety", SVG_SHIELD),
            ("Privacy", SVG_LOCK),
            ("Architecture", SVG_STORAGE),
        ]

        for idx, (name, icon_svg) in enumerate(tabs):
            btn = SettingsSubNavButton(name, icon_svg, is_active=(idx == 0), parent=container)
            btn.clicked.connect(lambda checked=False, i=idx: self._select_nav_tab(i))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        # Spacing / Subtle Divider
        layout.addSpacing(10)
        sep = QFrame(container)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #E8E5DC; background-color: #E8E5DC; min-height: 1px; max-height: 1px;")
        layout.addWidget(sep)
        layout.addSpacing(6)

        secondary_tabs = [
            ("General", SVG_SETTINGS),
            ("Account", SVG_USER),
            ("About", SVG_INFO),
        ]

        for s_idx, (name, icon_svg) in enumerate(secondary_tabs):
            total_idx = len(tabs) + s_idx
            btn = SettingsSubNavButton(name, icon_svg, is_active=False, parent=container)
            btn.clicked.connect(lambda checked=False, i=total_idx: self._select_nav_tab(i))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch(1)
        return container

    def _select_nav_tab(self, index: int) -> None:
        self.content_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.set_active(i == index)

        # Also sync horizontal category pills on AI Models page if applicable
        if hasattr(self, "top_pills") and index < len(self.top_pills):
            for i, p_btn in enumerate(self.top_pills):
                if i == index:
                    p_btn.setStyleSheet("background-color: #18181B; color: #FFFFFF; border-radius: 12px; padding: 4px 10px; font-size: 10px; font-weight: 600; border: none;")
                else:
                    p_btn.setStyleSheet("background-color: #FAF9F5; color: #52525B; border: 1px solid #E6E2D6; border-radius: 12px; padding: 4px 8px; font-size: 10px; font-weight: 500;")

    # -----------------------------------------------------------------------
    # Page 0: AI Models (Matching Reference Image)
    # -----------------------------------------------------------------------

    def _build_ai_models_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("chatScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background-color: transparent; border: none;")

        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 2, 4, 16)
        layout.setSpacing(14)

        # 1. Header: "AI Models" + Subtitle
        hdr_col = QVBoxLayout()
        hdr_col.setSpacing(2)

        title = QLabel("AI Models", content)
        title.setStyleSheet("font-family: 'Playfair Display', Georgia, serif; font-size: 22px; font-weight: 700; color: #18181B;")
        hdr_col.addWidget(title)

        sub = QLabel("Configure your AI models and API keys", content)
        sub.setStyleSheet("color: #71717A; font-size: 11px;")
        hdr_col.addWidget(sub)
        layout.addLayout(hdr_col)

        # 2. Horizontal Category Pills Row
        pills_widget = self._build_pills_row()
        layout.addWidget(pills_widget)

        # 3. Card 1: Google Gemini AI Studio API Key Card
        gemini_card = self._build_gemini_card(content)
        layout.addWidget(gemini_card)

        # 4. Card 2: Groq Cloud High-Capacity Fallback Key Card
        groq_card = self._build_groq_card(content)
        layout.addWidget(groq_card)

        # 5. Card 3: Intelligence Configuration Card
        intel_card = self._build_intelligence_config_card(content)
        layout.addWidget(intel_card)

        # 6. Card 4: Advanced Options Card
        adv_card = self._build_advanced_options_card(content)
        layout.addWidget(adv_card)

        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_pills_row(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        pill_names = ["AI Models", "Voice & Audio", "Hotkeys", "Safety", "Privacy", "Architecture"]
        self.top_pills: List[QPushButton] = []

        for idx, name in enumerate(pill_names):
            btn = QPushButton(name, container)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if idx == 0:
                btn.setStyleSheet("background-color: #18181B; color: #FFFFFF; border-radius: 12px; padding: 4px 10px; font-size: 10px; font-weight: 600; border: none;")
            else:
                btn.setStyleSheet("background-color: #FAF9F5; color: #52525B; border: 1px solid #E6E2D6; border-radius: 12px; padding: 4px 8px; font-size: 10px; font-weight: 500;")
            btn.clicked.connect(lambda checked=False, i=idx: self._select_nav_tab(i))
            layout.addWidget(btn)
            self.top_pills.append(btn)

        layout.addStretch(1)
        return container

    # --- Card 1: Google Gemini API Key ---
    def _build_gemini_card(self, parent: QWidget) -> QWidget:
        card = QFrame(parent)
        card.setObjectName("settingsCard")
        card.setStyleSheet("QFrame#settingsCard { background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 16px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Top Header Row
        top_row = QHBoxLayout()
        top_row.setSpacing(7)

        # Google colorful logo
        g_logo = QLabel(card)
        g_logo.setPixmap(render_svg_pixmap(SVG_BRAND_GOOGLE, 18, 18))
        top_row.addWidget(g_logo)

        # Title
        t_col = QVBoxLayout()
        t_col.setSpacing(1)
        title_row = QHBoxLayout()
        title_row.setSpacing(6)

        t_lbl = QLabel("Google Gemini AI Studio API Key", card)
        t_lbl.setStyleSheet("color: #18181B; font-size: 12px; font-weight: 700; border: none; background: transparent;")
        title_row.addWidget(t_lbl)

        badge = QLabel("Primary", card)
        badge.setStyleSheet("background-color: #EDEAE0; color: #71717A; font-size: 9px; font-weight: 600; border-radius: 7px; padding: 1px 6px;")
        title_row.addWidget(badge)

        help_icon = QLabel(card)
        help_icon.setPixmap(render_svg_pixmap(SVG_HELP_CIRCLE, 13, 13, color="#A1A1AA"))
        help_icon.setToolTip("Google Gemini powers reasoning, deep inspection, and screen vision.")
        title_row.addWidget(help_icon)
        title_row.addStretch(1)
        t_col.addLayout(title_row)

        sub_lbl = QLabel("(Encrypted in Windows Credential Manager)", card)
        sub_lbl.setStyleSheet("color: #71717A; font-size: 9px; border: none; background: transparent;")
        t_col.addWidget(sub_lbl)
        top_row.addLayout(t_col, stretch=1)

        # Toggle Switch
        self.gemini_toggle = ModernMiniToggle(card, checked=True)
        top_row.addWidget(self.gemini_toggle)
        layout.addLayout(top_row)

        # Status Label
        self.gemini_status_lbl = QLabel(card)
        self._update_gemini_status()
        layout.addWidget(self.gemini_status_lbl)

        # Password Input Row
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.gemini_input = QLineEdit(card)
        self.gemini_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_input.setPlaceholderText("Enter Google AI Studio key (AIzaSy...)")
        self.gemini_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #E8E4DA;
                border-radius: 8px;
                padding: 6px 10px;
                color: #18181B;
                font-size: 11.5px;
            }
            QLineEdit:focus {
                border-color: #18181B;
            }
        """)
        existing = get_gemini_api_key()
        if existing:
            self.gemini_input.setText(existing)
        input_row.addWidget(self.gemini_input, stretch=1)

        self.gemini_show_btn = QPushButton("Show", card)
        self.gemini_show_btn.setFixedSize(54, 30)
        self.gemini_show_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #E8E4DA;
                border-radius: 8px;
                color: #18181B;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #F8F7F3;
            }
        """)
        self.gemini_show_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gemini_show_btn.clicked.connect(self._toggle_show_gemini_key)
        input_row.addWidget(self.gemini_show_btn)
        layout.addLayout(input_row)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        store_btn = QPushButton("Test Store Key", card)
        store_btn.setStyleSheet("""
            QPushButton {
                background-color: #18181B;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #27272A;
            }
        """)
        store_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        store_btn.clicked.connect(self._handle_store_gemini_key)
        btn_row.addWidget(store_btn)

        remove_btn = QPushButton("Remove Key", card)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F3ED;
                color: #18181B;
                border: 1px solid #E6E1D4;
                border-radius: 10px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #EFECE3;
            }
        """)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.clicked.connect(self._handle_remove_gemini_key)
        btn_row.addWidget(remove_btn)

        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        return card

    def _update_gemini_status(self) -> None:
        if has_gemini_api_key():
            self.gemini_status_lbl.setText("Status: Configured & Active in Windows Vault ✓")
            self.gemini_status_lbl.setStyleSheet("color: #15803D; font-size: 10px; font-weight: 700; border: none; background: transparent;")
        else:
            self.gemini_status_lbl.setText("Status: Key not configured in Windows Vault")
            self.gemini_status_lbl.setStyleSheet("color: #B45309; font-size: 10px; font-weight: 600; border: none; background: transparent;")

    def _toggle_show_gemini_key(self) -> None:
        if self.gemini_input.echoMode() == QLineEdit.EchoMode.Password:
            self.gemini_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.gemini_show_btn.setText("Hide")
        else:
            self.gemini_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.gemini_show_btn.setText("Show")

    def _handle_store_gemini_key(self) -> None:
        key = self.gemini_input.text().strip()
        if not key:
            QMessageBox.warning(self, "API Key Missing", "Please enter a valid Google Gemini API Key.")
            return
        success = store_gemini_api_key(key)
        if success:
            self._update_gemini_status()
            self.command_submitted.emit("Google Gemini API Key securely saved & activated ✓")
        else:
            QMessageBox.critical(self, "Vault Error", "Failed to store key into Windows Credential Manager.")

    def _handle_remove_gemini_key(self) -> None:
        delete_gemini_api_key()
        self.gemini_input.clear()
        self._update_gemini_status()
        self.command_submitted.emit("Google Gemini API Key removed from Windows Vault.")

    # --- Card 2: Groq Cloud API Key ---
    def _build_groq_card(self, parent: QWidget) -> QWidget:
        card = QFrame(parent)
        card.setObjectName("settingsCard")
        card.setStyleSheet("QFrame#settingsCard { background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 16px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Top Header Row
        top_row = QHBoxLayout()
        top_row.setSpacing(7)

        # Groq red logo badge
        groq_badge = QLabel("groq", card)
        groq_badge.setFixedSize(22, 22)
        groq_badge.setStyleSheet("background-color: #F05A28; color: #FFFFFF; font-size: 8px; font-weight: 900; border-radius: 5px;")
        groq_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(groq_badge)

        # Title
        t_col = QVBoxLayout()
        t_col.setSpacing(1)
        title_row = QHBoxLayout()
        title_row.setSpacing(6)

        t_lbl = QLabel("Groq Cloud High-Capacity Fallback Key", card)
        t_lbl.setStyleSheet("color: #18181B; font-size: 12px; font-weight: 700; border: none; background: transparent;")
        title_row.addWidget(t_lbl)

        badge = QLabel("Fallback", card)
        badge.setStyleSheet("background-color: #EDE8DD; color: #71717A; font-size: 9px; font-weight: 600; border-radius: 7px; padding: 1px 6px;")
        title_row.addWidget(badge)

        help_icon = QLabel(card)
        help_icon.setPixmap(render_svg_pixmap(SVG_HELP_CIRCLE, 13, 13, color="#A1A1AA"))
        help_icon.setToolTip("Groq Cloud provides lightning-fast Whisper transcription & fallback token generation.")
        title_row.addWidget(help_icon)
        title_row.addStretch(1)
        t_col.addLayout(title_row)

        sub_lbl = QLabel("(Encrypted in Windows Credential Manager)", card)
        sub_lbl.setStyleSheet("color: #71717A; font-size: 9px; border: none; background: transparent;")
        t_col.addWidget(sub_lbl)
        top_row.addLayout(t_col, stretch=1)

        # Toggle Switch
        self.groq_toggle = ModernMiniToggle(card, checked=True)
        top_row.addWidget(self.groq_toggle)
        layout.addLayout(top_row)

        # Status Label
        self.groq_status_lbl = QLabel(card)
        self._update_groq_status()
        layout.addWidget(self.groq_status_lbl)

        # Password Input Row
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.groq_input = QLineEdit(card)
        self.groq_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_input.setPlaceholderText("Enter Groq API key (gsk_...)")
        self.groq_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #E8E4DA;
                border-radius: 8px;
                padding: 6px 10px;
                color: #18181B;
                font-size: 11.5px;
            }
            QLineEdit:focus {
                border-color: #18181B;
            }
        """)
        existing = get_groq_api_key()
        if existing:
            self.groq_input.setText(existing)
        input_row.addWidget(self.groq_input, stretch=1)

        self.groq_show_btn = QPushButton("Show", card)
        self.groq_show_btn.setFixedSize(54, 30)
        self.groq_show_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #E8E4DA;
                border-radius: 8px;
                color: #18181B;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #F8F7F3;
            }
        """)
        self.groq_show_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.groq_show_btn.clicked.connect(self._toggle_show_groq_key)
        input_row.addWidget(self.groq_show_btn)
        layout.addLayout(input_row)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        store_btn = QPushButton("Store Groq Key", card)
        store_btn.setStyleSheet("""
            QPushButton {
                background-color: #18181B;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #27272A;
            }
        """)
        store_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        store_btn.clicked.connect(self._handle_store_groq_key)
        btn_row.addWidget(store_btn)

        remove_btn = QPushButton("Remove Key", card)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F3ED;
                color: #18181B;
                border: 1px solid #E6E1D4;
                border-radius: 10px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #EFECE3;
            }
        """)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.clicked.connect(self._handle_remove_groq_key)
        btn_row.addWidget(remove_btn)

        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        return card

    def _update_groq_status(self) -> None:
        if has_groq_api_key():
            self.groq_status_lbl.setText("Status: Groq Key Configured & Active in Windows Vault ✓")
            self.groq_status_lbl.setStyleSheet("color: #15803D; font-size: 10px; font-weight: 700; border: none; background: transparent;")
        else:
            self.groq_status_lbl.setText("Status: Groq Key not configured in Windows Vault")
            self.groq_status_lbl.setStyleSheet("color: #71717A; font-size: 10px; font-weight: 500; border: none; background: transparent;")

    def _toggle_show_groq_key(self) -> None:
        if self.groq_input.echoMode() == QLineEdit.EchoMode.Password:
            self.groq_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.groq_show_btn.setText("Hide")
        else:
            self.groq_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.groq_show_btn.setText("Show")

    def _handle_store_groq_key(self) -> None:
        key = self.groq_input.text().strip()
        if not key:
            QMessageBox.warning(self, "API Key Missing", "Please enter a valid Groq API Key.")
            return
        success = store_groq_api_key(key)
        if success:
            self._update_groq_status()
            self.command_submitted.emit("Groq API Key securely stored in Windows Vault ✓")
        else:
            QMessageBox.critical(self, "Vault Error", "Failed to store key into Windows Credential Manager.")

    def _handle_remove_groq_key(self) -> None:
        delete_groq_api_key()
        self.groq_input.clear()
        self._update_groq_status()
        self.command_submitted.emit("Groq API Key removed from Windows Vault.")

    # --- Card 3: Intelligence Configuration ---
    def _build_intelligence_config_card(self, parent: QWidget) -> QWidget:
        card = QFrame(parent)
        card.setObjectName("settingsCard")
        card.setStyleSheet("QFrame#settingsCard { background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 16px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(6)
        brain_ic = QLabel(card)
        brain_ic.setPixmap(render_svg_pixmap(SVG_BRAIN, 16, 16, color="#18181B"))
        hdr.addWidget(brain_ic)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(1)
        t = QLabel("Intelligence Configuration", card)
        t.setStyleSheet("color: #18181B; font-size: 13px; font-weight: 700; border: none; background: transparent;")
        txt_col.addWidget(t)

        s = QLabel("Choose how Handless should use AI models", card)
        s.setStyleSheet("color: #71717A; font-size: 10px; border: none; background: transparent;")
        txt_col.addWidget(s)
        hdr.addLayout(txt_col, stretch=1)
        layout.addLayout(hdr)

        combo_qss = """
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #ECE7DC;
                border-radius: 8px;
                padding: 4px 10px;
                color: #18181B;
                font-size: 11px;
                font-weight: 500;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background: #FFFFFF;
                border: 1px solid #ECE7DC;
                selection-background-color: #F3EFE6;
                selection-color: #18181B;
                color: #18181B;
            }
        """

        # Field 1: Intelligence Tier
        f1_row = QHBoxLayout()
        f1_lbl_row = QHBoxLayout()
        f1_lbl_row.setSpacing(5)
        ic1 = QLabel(card)
        ic1.setPixmap(render_svg_pixmap(SVG_SPARKLE, 14, 14, color="#71717A"))
        f1_lbl_row.addWidget(ic1)
        l1 = QLabel("Intelligence Tier", card)
        l1.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        f1_lbl_row.addWidget(l1)
        f1_row.addLayout(f1_lbl_row, stretch=1)

        self.tier_combo = QComboBox(card)
        self.tier_combo.setStyleSheet(combo_qss)
        self.tier_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.tier_combo.setMinimumWidth(130)
        self.tier_combo.setMaximumWidth(220)
        self.tier_combo.addItems([
            "Hybrid (Recommended: Local + Cloud)",
            "Cloud Only (Gemini)",
            "Local Only (Offline)",
        ])
        f1_row.addWidget(self.tier_combo)
        layout.addLayout(f1_row)

        # Field 2: Google AI Model
        f2_row = QHBoxLayout()
        f2_lbl_row = QHBoxLayout()
        f2_lbl_row.setSpacing(5)
        ic2 = QLabel(card)
        ic2.setPixmap(render_svg_pixmap(SVG_BRAND_GOOGLE, 14, 14))
        f2_lbl_row.addWidget(ic2)
        l2 = QLabel("Google AI Model", card)
        l2.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        f2_lbl_row.addWidget(l2)
        f2_row.addLayout(f2_lbl_row, stretch=1)

        self.gemini_combo = QComboBox(card)
        self.gemini_combo.setStyleSheet(combo_qss)
        self.gemini_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.gemini_combo.setMinimumWidth(130)
        self.gemini_combo.setMaximumWidth(220)
        self.gemini_combo.addItems([
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
            "gemma-4-31b-it",
        ])
        f2_row.addWidget(self.gemini_combo)
        layout.addLayout(f2_row)

        # Field 3: Groq Cloud Model
        f3_row = QHBoxLayout()
        f3_lbl_row = QHBoxLayout()
        f3_lbl_row.setSpacing(5)
        ic3 = QLabel("g", card)
        ic3.setFixedSize(14, 14)
        ic3.setStyleSheet("background-color: #F05A28; color: #FFFFFF; font-size: 9px; font-weight: 900; border-radius: 3px;")
        ic3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f3_lbl_row.addWidget(ic3)
        l3 = QLabel("Groq Cloud Model", card)
        l3.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        f3_lbl_row.addWidget(l3)
        f3_row.addLayout(f3_lbl_row, stretch=1)

        self.groq_combo = QComboBox(card)
        self.groq_combo.setStyleSheet(combo_qss)
        self.groq_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.groq_combo.setMinimumWidth(130)
        self.groq_combo.setMaximumWidth(220)
        self.groq_combo.addItems([
            "qwen/qwen3.8-27b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
        ])
        f3_row.addWidget(self.groq_combo)
        layout.addLayout(f3_row)

        # Toggle: Gemini Vision Fallback
        t_row = QHBoxLayout()
        t_row.setSpacing(6)
        eye_ic = QLabel(card)
        eye_ic.setPixmap(render_svg_pixmap(SVG_EYE, 14, 14, color="#18181B"))
        t_row.addWidget(eye_ic)

        v_col = QVBoxLayout()
        v_col.setSpacing(1)
        vt = QLabel("Enable Gemini Vision Screen Fallback", card)
        vt.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        v_col.addWidget(vt)
        vs = QLabel("Use Gemini for screen understanding when needed", card)
        vs.setStyleSheet("color: #71717A; font-size: 9px; border: none; background: transparent;")
        v_col.addWidget(vs)
        t_row.addLayout(v_col, stretch=1)

        self.vision_toggle = ModernMiniToggle(card, checked=True)
        t_row.addWidget(self.vision_toggle)
        layout.addLayout(t_row)

        return card

    # --- Card 4: Advanced Options ---
    def _build_advanced_options_card(self, parent: QWidget) -> QWidget:
        card = QFrame(parent)
        card.setObjectName("settingsCard")
        card.setStyleSheet("QFrame#settingsCard { background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 16px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(6)
        sl_ic = QLabel(card)
        sl_ic.setPixmap(render_svg_pixmap(SVG_SLIDERS, 16, 16, color="#18181B"))
        hdr.addWidget(sl_ic)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(1)
        t = QLabel("Advanced Options", card)
        t.setStyleSheet("color: #18181B; font-size: 13px; font-weight: 700; border: none; background: transparent;")
        txt_col.addWidget(t)

        s = QLabel("Additional AI settings", card)
        s.setStyleSheet("color: #71717A; font-size: 10px; border: none; background: transparent;")
        txt_col.addWidget(s)
        hdr.addLayout(txt_col, stretch=1)
        layout.addLayout(hdr)

        combo_qss = """
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #ECE7DC;
                border-radius: 8px;
                padding: 4px 10px;
                color: #18181B;
                font-size: 11px;
                font-weight: 500;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background: #FFFFFF;
                border: 1px solid #ECE7DC;
                selection-background-color: #F3EFE6;
                selection-color: #18181B;
                color: #18181B;
            }
        """

        # Toggle 1: Auto-fallback
        t1_row = QHBoxLayout()
        ic1 = QLabel(card)
        ic1.setPixmap(render_svg_pixmap(SVG_REFRESH, 14, 14, color="#18181B"))
        t1_row.addWidget(ic1)

        c1 = QVBoxLayout()
        c1.setSpacing(1)
        t1 = QLabel("Auto-fallback", card)
        t1.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        c1.addWidget(t1)
        s1 = QLabel("Automatically use fallback model if primary fails", card)
        s1.setStyleSheet("color: #71717A; font-size: 9px; border: none; background: transparent;")
        c1.addWidget(s1)
        t1_row.addLayout(c1, stretch=1)

        self.autofallback_toggle = ModernMiniToggle(card, checked=True)
        t1_row.addWidget(self.autofallback_toggle)
        layout.addLayout(t1_row)

        # Toggle 2: Model routing
        t2_row = QHBoxLayout()
        ic2 = QLabel(card)
        ic2.setPixmap(render_svg_pixmap(SVG_APPS_GRID, 14, 14, color="#18181B"))
        t2_row.addWidget(ic2)

        c2 = QVBoxLayout()
        c2.setSpacing(1)
        t2 = QLabel("Model routing", card)
        t2.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        c2.addWidget(t2)
        s2 = QLabel("Let Handless choose the best model for each task", card)
        s2.setStyleSheet("color: #71717A; font-size: 9px; border: none; background: transparent;")
        c2.addWidget(s2)
        t2_row.addLayout(c2, stretch=1)

        self.routing_toggle = ModernMiniToggle(card, checked=True)
        t2_row.addWidget(self.routing_toggle)
        layout.addLayout(t2_row)

        # Field 3: Response Language
        f3_row = QHBoxLayout()
        ic3 = QLabel("[A]", card)
        ic3.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 700;")
        f3_row.addWidget(ic3)
        l3 = QLabel("Response language", card)
        l3.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        f3_row.addWidget(l3, stretch=1)

        self.lang_combo = QComboBox(card)
        self.lang_combo.setStyleSheet(combo_qss)
        self.lang_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.lang_combo.setMinimumWidth(110)
        self.lang_combo.setMaximumWidth(170)
        self.lang_combo.addItems([
            "Auto (Same as system)",
            "English",
            "Spanish",
            "French",
            "German",
            "Hindi",
            "Japanese",
        ])
        f3_row.addWidget(self.lang_combo)
        layout.addLayout(f3_row)

        # Field 4: Max response length
        f4_row = QHBoxLayout()
        ic4 = QLabel(card)
        ic4.setPixmap(render_svg_pixmap(SVG_FILE_TEXT, 14, 14, color="#18181B"))
        f4_row.addWidget(ic4)
        l4 = QLabel("Max response length", card)
        l4.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        f4_row.addWidget(l4, stretch=1)

        self.len_combo = QComboBox(card)
        self.len_combo.setStyleSheet(combo_qss)
        self.len_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.len_combo.setMinimumWidth(110)
        self.len_combo.setMaximumWidth(170)
        self.len_combo.addItems(["Default", "Concise", "Detailed", "Unrestricted"])
        f4_row.addWidget(self.len_combo)
        layout.addLayout(f4_row)

        # Field 5: System Diagnostics & Logs
        f5_row = QHBoxLayout()
        ic5 = QLabel(card)
        ic5.setPixmap(render_svg_pixmap(SVG_FILE_TEXT, 14, 14, color="#18181B"))
        f5_row.addWidget(ic5)

        c5 = QVBoxLayout()
        c5.setSpacing(1)
        t5 = QLabel("System logs & diagnostics", card)
        t5.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        c5.addWidget(t5)
        s5 = QLabel("Inspect runtime errors and execution traces", card)
        s5.setStyleSheet("color: #71717A; font-size: 9px; border: none; background: transparent;")
        c5.addWidget(s5)
        f5_row.addLayout(c5, stretch=1)

        self.logs_btn = QPushButton("Open Logs 📁", card)
        self.logs_btn.setStyleSheet("""
            QPushButton {
                background-color: #18181B;
                color: #FFFFFF;
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover {
                background-color: #27272A;
            }
        """)
        self.logs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logs_btn.clicked.connect(self._on_open_logs_clicked)
        f5_row.addWidget(self.logs_btn)
        layout.addLayout(f5_row)

        return card

    def _on_open_logs_clicked(self) -> None:
        try:
            from handless.logging_config import open_logs_directory
            open_logs_directory()
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Other Pages (Voice, Hotkeys, Safety, Privacy, Architecture, General, Account, About)
    # -----------------------------------------------------------------------

    def _wrap_in_scroll(self, content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("chatScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        if scroll.viewport():
            scroll.viewport().setStyleSheet("background-color: transparent;")
        scroll.setWidget(content)
        return scroll

    def _build_voice_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        t = QLabel("Voice & Audio Settings", container)
        t.setStyleSheet("font-family: 'Playfair Display', serif; font-size: 18px; font-weight: 700; color: #18181B;")
        layout.addWidget(t)

        card = QFrame(container)
        card.setStyleSheet("background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 14px; padding: 12px;")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(8)

        stt_lbl = QLabel("Offline / Cloud Speech-to-Text Engine:", card)
        stt_lbl.setWordWrap(True)
        stt_lbl.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 600;")
        c_layout.addWidget(stt_lbl)

        stt_combo = QComboBox(card)
        stt_combo.addItems([
            "Groq Cloud Whisper Large v3 (Fastest & Highest Accuracy)",
            "OpenAI Whisper Base (Local CPU — sherpa-onnx)",
            "Vosk English (Offline Small)",
        ])
        c_layout.addWidget(stt_combo)

        layout.addWidget(card)
        layout.addStretch(1)
        return container

    def _build_hotkeys_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        t = QLabel("Keyboard Hotkeys", container)
        t.setStyleSheet("font-family: 'Playfair Display', serif; font-size: 18px; font-weight: 700; color: #18181B;")
        layout.addWidget(t)

        keys = [
            ("Push-to-Talk / Voice Command", "Ctrl + Space"),
            ("Whispr Flow Mode (Hold to Dictate)", "Ctrl + Shift"),
            ("Toggle Sidebar Window", "Ctrl + Alt + H"),
            ("Emergency Stop Actions", "Ctrl + Shift + Q"),
        ]

        card = QFrame(container)
        card.setStyleSheet("background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 14px; padding: 10px;")
        c_layout = QVBoxLayout(card)
        for label, shortcut in keys:
            row = QHBoxLayout()
            l = QLabel(label, card)
            l.setWordWrap(True)
            l.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 500;")
            row.addWidget(l)
            row.addStretch(1)
            k = QLabel(shortcut, card)
            k.setStyleSheet("background: #FFFFFF; border: 1px solid #E8E5DC; border-radius: 6px; padding: 2px 8px; font-size: 10px; font-weight: 700; color: #18181B;")
            row.addWidget(k)
            c_layout.addLayout(row)

        layout.addWidget(card)
        layout.addStretch(1)
        return container

    def _build_safety_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        t = QLabel("Safety & Guardrails", container)
        t.setStyleSheet("font-family: 'Playfair Display', serif; font-size: 18px; font-weight: 700; color: #18181B;")
        layout.addWidget(t)

        card = QFrame(container)
        card.setStyleSheet("background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 14px; padding: 12px;")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        t1 = QLabel("Active Safety Protections:", card)
        t1.setStyleSheet("color: #18181B; font-size: 11.5px; font-weight: 700;")
        c_layout.addWidget(t1)

        items = [
            "Emergency Stop Trigger (instant kill switch on hotkey or ESC)",
            "Explicit confirmation before file deletions or destructive CLI commands",
            "Sanitized environment boundaries and sandboxed execution verification",
        ]
        for item in items:
            row = QHBoxLayout()
            chk = QLabel("✓", card)
            chk.setStyleSheet("color: #16A34A; font-weight: 800; font-size: 12px;")
            row.addWidget(chk)
            lbl = QLabel(item, card)
            lbl.setStyleSheet("color: #52525B; font-size: 10.5px;")
            lbl.setWordWrap(True)
            row.addWidget(lbl, stretch=1)
            c_layout.addLayout(row)

        layout.addWidget(card)
        layout.addStretch(1)
        return container

    def _build_privacy_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        t = QLabel("Data Privacy & Security", container)
        t.setStyleSheet("font-family: 'Playfair Display', serif; font-size: 18px; font-weight: 700; color: #18181B;")
        layout.addWidget(t)

        card = QFrame(container)
        card.setStyleSheet("background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 14px; padding: 12px;")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(8)

        p1 = QLabel("• Zero telemetry / tracking data sent to third parties.", card)
        p1.setWordWrap(True)
        p1.setStyleSheet("color: #18181B; font-size: 11px;")
        c_layout.addWidget(p1)

        p2 = QLabel("• All API keys are encrypted locally using Windows DPAPI Credential Vault.", card)
        p2.setWordWrap(True)
        p2.setStyleSheet("color: #18181B; font-size: 11px;")
        c_layout.addWidget(p2)

        p3 = QLabel("• Screen captures and voice audio are processed transiently in memory.", card)
        p3.setWordWrap(True)
        p3.setStyleSheet("color: #18181B; font-size: 11px;")
        c_layout.addWidget(p3)

        layout.addWidget(card)
        layout.addStretch(1)
        return container

    def _build_architecture_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        t = QLabel("System Architecture", container)
        t.setStyleSheet("font-family: 'Playfair Display', serif; font-size: 18px; font-weight: 700; color: #18181B;")
        layout.addWidget(t)

        card = QFrame(container)
        card.setStyleSheet("background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 14px; padding: 12px;")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(8)

        arch_info = [
            ("UI Framework", "PySide6 (Qt 6.7+ for Windows)"),
            ("Automation Engine", "UIAutomation / PyWinAuto / SendKeys"),
            ("Primary Cloud LLM", "Google Gemini 2.5 Flash / Flash-Lite"),
            ("Fallback Cloud LLM", "Groq Cloud Qwen 3.8 / Llama 3.3"),
            ("Speech Engine", "Groq Whisper Large v3 / Sherpa-ONNX"),
        ]

        for k, v in arch_info:
            r = QHBoxLayout()
            kl = QLabel(k, card)
            kl.setWordWrap(True)
            kl.setStyleSheet("color: #71717A; font-size: 10.5px;")
            r.addWidget(kl)
            r.addStretch(1)
            vl = QLabel(v, card)
            vl.setWordWrap(True)
            vl.setStyleSheet("color: #18181B; font-size: 10.5px; font-weight: 600;")
            r.addWidget(vl)
            c_layout.addLayout(r)

        layout.addWidget(card)
        layout.addStretch(1)
        return container

    def _build_general_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        t = QLabel("General Preferences", container)
        t.setStyleSheet("font-family: 'Playfair Display', serif; font-size: 18px; font-weight: 700; color: #18181B;")
        layout.addWidget(t)

        card = QFrame(container)
        card.setStyleSheet("background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 14px; padding: 12px;")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        # Start with Windows
        r1 = QHBoxLayout()
        l1 = QLabel("Launch on system startup", card)
        l1.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 500;")
        r1.addWidget(l1)
        r1.addStretch(1)
        sw1 = ModernMiniToggle(card, checked=False)
        r1.addWidget(sw1)
        c_layout.addLayout(r1)

        # Keep on top
        r2 = QHBoxLayout()
        l2 = QLabel("Always stay on top", card)
        l2.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 500;")
        r2.addWidget(l2)
        r2.addStretch(1)
        sw2 = ModernMiniToggle(card, checked=True)
        r2.addWidget(sw2)
        c_layout.addLayout(r2)

        layout.addWidget(card)
        layout.addStretch(1)
        return container

    def _build_account_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        t = QLabel("Account & Workspace", container)
        t.setStyleSheet("font-family: 'Playfair Display', serif; font-size: 18px; font-weight: 700; color: #18181B;")
        layout.addWidget(t)

        card = QFrame(container)
        card.setStyleSheet("background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 14px; padding: 14px;")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(8)

        u_row = QHBoxLayout()
        av = QLabel("V", card)
        av.setFixedSize(36, 36)
        av.setStyleSheet("background-color: #18181B; color: #FFFFFF; font-size: 14px; font-weight: 800; border-radius: 18px;")
        av.setAlignment(Qt.AlignmentFlag.AlignCenter)
        u_row.addWidget(av)

        uc = QVBoxLayout()
        uc.setSpacing(2)
        un = QLabel("Vyoma Workspace User", card)
        un.setStyleSheet("color: #18181B; font-size: 12.5px; font-weight: 700;")
        uc.addWidget(un)
        ue = QLabel("Local Desktop Edition", card)
        ue.setStyleSheet("color: #71717A; font-size: 10px;")
        uc.addWidget(ue)
        u_row.addLayout(uc, stretch=1)
        c_layout.addLayout(u_row)

        layout.addWidget(card)
        layout.addStretch(1)
        return container

    def _build_about_page(self) -> QWidget:
        """About page featuring the official handless-bot.png logo with background."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Hero Bot Logo (With background)
        bot_pix = get_bot_logo_pixmap(without_bg=False, size=110)
        bot_lbl = QLabel(container)
        if not bot_pix.isNull():
            bot_lbl.setPixmap(bot_pix)
            bot_lbl.setStyleSheet("border-radius: 20px; border: 2px solid #E6E1D4;")
        bot_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(bot_lbl)

        # Title
        t = QLabel("handless™", container)
        t.setStyleSheet("font-family: 'Playfair Display', Georgia, serif; font-size: 24px; font-weight: 800; color: #18181B;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(t)

        sub = QLabel("by Vyoma Group · Version 2.0.0", container)
        sub.setStyleSheet("color: #71717A; font-size: 11px; font-weight: 500;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        desc = QLabel(
            "Your desktop, without hands.\n"
            "An agentic AI pairing partner crafted with PySide6, Google Gemini, "
            "and offline whisper speech intelligence.",
            container,
        )
        desc.setStyleSheet("color: #52525B; font-size: 11px; line-height: 1.4;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addStretch(1)
        return container

    # -----------------------------------------------------------------------
    # Bottom Synchronized Prompt Bar
    # -----------------------------------------------------------------------

    def _build_bottom_bar(self) -> QWidget:
        container = QWidget(self)
        container.setObjectName("promptContainerCard")
        container.setStyleSheet("QWidget#promptContainerCard { background-color: #F5F4EE; border: 1px solid #E7E4DA; border-radius: 18px; padding: 6px; }")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 4, 6, 4)
        layout.setSpacing(8)

        wave_btn = QPushButton(container)
        wave_btn.setIcon(render_svg_icon(SVG_VOICE_WAVE, 16, color="#71717A", hover_color="#18181B"))
        wave_btn.setFixedSize(24, 24)
        wave_btn.setStyleSheet("background: transparent; border: none;")
        wave_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        wave_btn.clicked.connect(self.voice_toggled)
        layout.addWidget(wave_btn)

        sep = QWidget(container)
        sep.setFixedSize(1, 16)
        sep.setStyleSheet("background-color: #E2DFD6;")
        layout.addWidget(sep)

        self.input_field = QLineEdit(container)
        self.input_field.setPlaceholderText("Tell Handless what to do...")
        self.input_field.setStyleSheet("background: transparent; border: none; color: #18181B; font-size: 12.5px;")
        self.input_field.returnPressed.connect(self._handle_enter)
        layout.addWidget(self.input_field, stretch=1)

        attach_btn = QPushButton(container)
        attach_btn.setIcon(render_svg_icon(SVG_PAPERCLIP, 16, color="#71717A"))
        attach_btn.setFixedSize(28, 28)
        attach_btn.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(attach_btn)

        send_btn = QPushButton(container)
        send_btn.setIcon(render_svg_icon(SVG_ARROW_UP, 16, color="#FFFFFF"))
        send_btn.setFixedSize(32, 32)
        send_btn.setStyleSheet("background-color: #18181B; border-radius: 16px; border: none;")
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.clicked.connect(self._handle_enter)
        layout.addWidget(send_btn)

        return container

    def _handle_enter(self) -> None:
        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.command_submitted.emit(text)

