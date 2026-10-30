"""Desktop UI Element Inspector for Windows.

Provides an interactive GUI to inspect, locate, test, and extract automation
locators for controls in any running Windows desktop application via UI Automation.
Features:
- Chromium & Browser Deep Tracking (Auto-Wake WM_GETOBJECT, [WEB] vs [APP] DOM partitioning)
- Live Desktop Crosshair & Screen Snapping Highlighter with Click-to-Select Freeze
- Multi-Modal Resilient Locator Generator (Tier 1 Dynamic, Tier 2 Structural Anchor, Tier 3 Coordinate/Vision)
- Interactive Inspector Playground (Test Click, Test Type, Scroll into View, Highlight, Copy Actions)
- Dual-View Architecture: Flat Table View + Lazy-Loaded DOM/UIA Tree View
"""

from __future__ import annotations

import ctypes
import json
import logging
from typing import Any, Dict, List, Optional

import pyautogui
from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from handless.screen.cdp_bridge import CDPBridge
from handless.screen.chromium_bridge import (
    is_chromium_window,
    partition_browser_elements,
    wake_chromium_accessibility,
)
from handless.screen.locator_generator import ResilientLocator, generate_resilient_locator
from handless.screen.uia_inspector import UIAInspector
from handless.ui.icons import (
    SVG_CHECK,
    SVG_CLICK,
    SVG_CLOSE,
    SVG_CODE,
    SVG_COPY,
    SVG_CROSSHAIR,
    SVG_EYE,
    SVG_REFRESH,
    SVG_SEARCH,
    SVG_WINDOW,
    render_svg_icon,
)

logger = logging.getLogger(__name__)

INSPECTOR_STYLESHEET = """
QMainWindow {
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: 'Segoe UI', -apple-system, sans-serif;
}

QWidget#inspectorCentral {
    background-color: #0F172A;
}

QFrame.cardFrame {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 10px;
}

QLabel {
    color: #E2E8F0;
    font-size: 13px;
}

QLabel.titleLabel {
    font-size: 15px;
    font-weight: 700;
    color: #38BDF8;
}

QLabel.subLabel {
    font-size: 12px;
    color: #94A3B8;
}

QLabel.badge {
    background-color: #334155;
    color: #38BDF8;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: 600;
}

QLineEdit, QComboBox {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F8FAFC;
    font-size: 13px;
    selection-background-color: #0284C7;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #38BDF8;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QPushButton {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #F8FAFC;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
}

QPushButton:pressed {
    background-color: #0F172A;
}

QPushButton.primaryButton {
    background-color: #0284C7;
    border: 1px solid #0284C7;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton.primaryButton:hover {
    background-color: #0369A1;
    border-color: #0369A1;
}

QPushButton.accentButton {
    background-color: #0D9488;
    border: 1px solid #0D9488;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton.accentButton:hover {
    background-color: #0F766E;
}

QPushButton:checked {
    background-color: #E11D48;
    border-color: #F43F5E;
    color: #FFFFFF;
}

QTabWidget::pane {
    border: 1px solid #334155;
    background-color: #1E293B;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #0F172A;
    color: #94A3B8;
    padding: 7px 16px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
    font-size: 12px;
}

QTabBar::tab:selected {
    background-color: #1E293B;
    color: #38BDF8;
    border: 1px solid #334155;
    border-bottom: none;
}

QTableWidget, QTreeWidget {
    background-color: #1E293B;
    border: none;
    gridline-color: #334155;
    color: #F8FAFC;
    font-size: 12px;
    selection-background-color: #0284C7;
    selection-color: #FFFFFF;
}

QTableWidget::item, QTreeWidget::item {
    padding: 5px;
}

QTableWidget::item:selected, QTreeWidget::item:selected {
    background-color: #0284C7;
}

QHeaderView::section {
    background-color: #0F172A;
    color: #94A3B8;
    font-weight: 600;
    font-size: 12px;
    border: none;
    border-bottom: 1px solid #334155;
    padding: 6px;
}

QScrollBar:vertical {
    background-color: #0F172A;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #334155;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QCheckBox {
    color: #E2E8F0;
    font-size: 12px;
    spacing: 6px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #0F172A;
}

QCheckBox::indicator:checked {
    background-color: #0284C7;
    border-color: #38BDF8;
}
"""


class ElementHighlightOverlay(QWidget):
    """Transparent on-screen overlay that highlights bounding boxes of inspected elements.

    Displays neon glowing borders, type tags, source badges ([WEB] vs [APP]), and voice triggers.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._rect: Optional[QRect] = None
        self._label: str = ""
        self._badge: str = ""
        self._voice_cmd: str = ""
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self.hide_overlay)
        self.hide()

    def show_element(
        self,
        rect: Dict[str, int],
        label: str = "",
        badge: str = "",
        voice_cmd: str = "",
        flash_duration_ms: Optional[int] = None,
    ) -> None:
        """Position overlay around the element rectangle and paint glowing border."""
        try:
            left = rect.get("left", 0)
            top = rect.get("top", 0)
            width = max(rect.get("width", 0), 10)
            height = max(rect.get("height", 0), 10)

            pad = 6
            tag_height = 42 if voice_cmd else (24 if label else 0)

            target_x = max(0, left - pad)
            target_y = max(0, top - pad - tag_height)
            target_w = width + (pad * 2)
            target_h = height + (pad * 2) + tag_height

            self.setGeometry(target_x, target_y, target_w, target_h)
            self._rect = QRect(pad, tag_height + pad, width, height)
            self._label = label
            self._badge = badge
            self._voice_cmd = voice_cmd

            if flash_duration_ms:
                self._flash_timer.start(flash_duration_ms)
            else:
                self._flash_timer.stop()

            self.show()
            self.update()
        except Exception as exc:
            logger.debug("Overlay show_element error: %s", exc)

    def hide_overlay(self) -> None:
        """Dismiss bounding box overlay."""
        self._rect = None
        self._label = ""
        self._badge = ""
        self._voice_cmd = ""
        self.hide()

    def paintEvent(self, event: Any) -> None:
        if not self._rect:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Draw glowing translucent bounding box over element
        fill_color = QColor(2, 132, 199, 40)
        border_color = QColor(0, 210, 255, 240)  # Neon Cyan
        border_pen = QPen(border_color, 2.5)

        painter.setBrush(fill_color)
        painter.setPen(border_pen)
        painter.drawRoundedRect(self._rect, 5, 5)

        # 2. Draw element label chip at top if provided
        if self._label:
            tag_rect = QRect(self._rect.left(), max(0, self._rect.top() - 24), min(self.width() - 8, 300), 20)
            chip_color = QColor(16, 185, 129, 235) if "[WEB]" in self._badge else QColor(2, 132, 199, 235)
            painter.setBrush(chip_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(tag_rect, 4, 4)

            painter.setPen(QColor("#FFFFFF"))
            font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            painter.setFont(font)
            display_tag = f"{self._badge} {self._label}" if self._badge else self._label
            painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, display_tag[:45])

        # 3. Draw voice command trigger chip if available
        if self._voice_cmd:
            v_rect = QRect(self._rect.left(), max(0, self._rect.top() - 44), min(self.width() - 8, 260), 18)
            painter.setBrush(QColor(15, 23, 42, 220))
            painter.setPen(QPen(QColor(56, 189, 248, 180), 1))
            painter.drawRoundedRect(v_rect, 3, 3)

            painter.setPen(QColor("#38BDF8"))
            font_v = QFont("Segoe UI", 7, QFont.Weight.DemiBold)
            painter.setFont(font_v)
            painter.drawText(v_rect, Qt.AlignmentFlag.AlignCenter, f"🗣️ {self._voice_cmd[:40]}")

        painter.end()


class DesktopElementInspector(QMainWindow):
    """High-precision Desktop UI Element Inspector and Automation Workbench."""

    def __init__(self, uia: Optional[UIAInspector] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.uia = uia or UIAInspector()
        self.cdp = CDPBridge()
        self.overlay = ElementHighlightOverlay()

        self._windows_cache: List[Dict[str, Any]] = []
        self._elements_cache: List[Dict[str, Any]] = []
        self._selected_element: Optional[Dict[str, Any]] = None
        self._current_locator: Optional[ResilientLocator] = None
        self._current_window_rect: Optional[Dict[str, int]] = None

        # Hover & Pick mode inspection timer
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(65)
        self._hover_timer.timeout.connect(self._on_hover_tick)
        self._pick_freeze_active = False

        self._init_window()
        self._init_ui()
        self.refresh_windows()

    def _init_window(self) -> None:
        self.setWindowTitle("Vyoma Handless - Desktop Element Inspector")
        self.resize(1120, 740)
        self.setMinimumSize(920, 560)
        self.setStyleSheet(INSPECTOR_STYLESHEET)

    def _init_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("inspectorCentral")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 1. Top Target Selection & Scan Toolbar
        top_card = QFrame(central)
        top_card.setProperty("class", "cardFrame")
        top_card_layout = QHBoxLayout(top_card)
        top_card_layout.setContentsMargins(8, 8, 8, 8)
        top_card_layout.setSpacing(10)

        win_icon_lbl = QLabel(top_card)
        win_icon_lbl.setPixmap(render_svg_icon(SVG_WINDOW, 18, color="#38BDF8").pixmap(18, 18))
        top_card_layout.addWidget(win_icon_lbl)

        win_lbl = QLabel("Target Window:", top_card)
        win_lbl.setStyleSheet("font-weight: 600; color: #94A3B8;")
        top_card_layout.addWidget(win_lbl)

        self.window_combo = QComboBox(top_card)
        self.window_combo.setMinimumWidth(320)
        self.window_combo.addItem("🎯 Active Focused Window (Auto-Detect)", None)
        top_card_layout.addWidget(self.window_combo, stretch=1)

        self.btn_refresh_wins = QPushButton("Refresh", top_card)
        self.btn_refresh_wins.setIcon(render_svg_icon(SVG_REFRESH, 14, color="#E2E8F0"))
        self.btn_refresh_wins.setToolTip("Refresh list of open desktop applications")
        self.btn_refresh_wins.clicked.connect(self.refresh_windows)
        top_card_layout.addWidget(self.btn_refresh_wins)

        self.btn_scan = QPushButton("Scan Controls", top_card)
        self.btn_scan.setProperty("class", "primaryButton")
        self.btn_scan.setIcon(render_svg_icon(SVG_SEARCH, 14, color="#FFFFFF"))
        self.btn_scan.clicked.connect(self.scan_target_window)
        top_card_layout.addWidget(self.btn_scan)

        self.btn_hover = QPushButton("🎯 Live Hover / Pick Element", top_card)
        self.btn_hover.setCheckable(True)
        self.btn_hover.setToolTip("Hover over any control or click to freeze/inspect (Click-to-Select)")
        self.btn_hover.clicked.connect(self._toggle_hover_mode)
        top_card_layout.addWidget(self.btn_hover)

        self.btn_cdp = QPushButton("🌐 Check CDP Tabs", top_card)
        self.btn_cdp.setToolTip("Check Chrome / Edge remote debugging port (localhost:9222)")
        self.btn_cdp.clicked.connect(self._check_cdp_status)
        top_card_layout.addWidget(self.btn_cdp)

        layout.addWidget(top_card)

        # 2. Live Element Inspection & 3-Tier Locator Card
        self.detail_card = QFrame(central)
        self.detail_card.setProperty("class", "cardFrame")
        detail_layout = QVBoxLayout(self.detail_card)
        detail_layout.setContentsMargins(10, 8, 10, 8)
        detail_layout.setSpacing(6)

        detail_header = QHBoxLayout()
        self.detail_title = QLabel("Select an element or enable Live Hover to inspect", self.detail_card)
        self.detail_title.setProperty("class", "titleLabel")
        detail_header.addWidget(self.detail_title, stretch=1)

        self.badge_source = QLabel("APP", self.detail_card)
        self.badge_source.setStyleSheet("background-color: #0369A1; color: #E0F2FE; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 700;")
        detail_header.addWidget(self.badge_source)

        self.type_badge = QLabel("None", self.detail_card)
        self.type_badge.setProperty("class", "badge")
        detail_header.addWidget(self.type_badge)

        self.state_badge = QLabel("Ready", self.detail_card)
        self.state_badge.setStyleSheet("background-color: #064E3B; color: #34D399; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600;")
        detail_header.addWidget(self.state_badge)

        detail_layout.addLayout(detail_header)

        # Meta properties row
        meta_row = QHBoxLayout()
        meta_row.setSpacing(16)

        self.lbl_auto_id = QLabel("AutomationId: —", self.detail_card)
        self.lbl_auto_id.setStyleSheet("color: #94A3B8; font-size: 12px;")
        meta_row.addWidget(self.lbl_auto_id)

        self.lbl_coords = QLabel("Bounding Box: —", self.detail_card)
        self.lbl_coords.setStyleSheet("color: #94A3B8; font-size: 12px;")
        meta_row.addWidget(self.lbl_coords)

        self.lbl_window = QLabel("Window: —", self.detail_card)
        self.lbl_window.setStyleSheet("color: #94A3B8; font-size: 12px;")
        meta_row.addWidget(self.lbl_window, stretch=1)

        detail_layout.addLayout(meta_row)

        # 3-Tier Locator Recipe Row
        locator_box = QFrame(self.detail_card)
        locator_box.setStyleSheet("background-color: #0F172A; border: 1px solid #334155; border-radius: 6px; padding: 6px;")
        locator_layout = QHBoxLayout(locator_box)
        locator_layout.setContentsMargins(6, 4, 6, 4)
        locator_layout.setSpacing(12)

        self.lbl_tier1 = QLabel("<b>Tier 1 (Dynamic):</b> —", locator_box)
        self.lbl_tier1.setStyleSheet("color: #38BDF8; font-size: 11px;")
        locator_layout.addWidget(self.lbl_tier1, stretch=1)

        self.lbl_tier2 = QLabel("<b>Tier 2 (Structural):</b> —", locator_box)
        self.lbl_tier2.setStyleSheet("color: #F59E0B; font-size: 11px;")
        locator_layout.addWidget(self.lbl_tier2, stretch=1)

        self.lbl_tier3 = QLabel("<b>Tier 3 (Coordinate):</b> —", locator_box)
        self.lbl_tier3.setStyleSheet("color: #34D399; font-size: 11px;")
        locator_layout.addWidget(self.lbl_tier3, stretch=1)

        detail_layout.addWidget(locator_box)
        layout.addWidget(self.detail_card)

        # 3. Filter Bar
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        self.search_input = QLineEdit(central)
        self.search_input.setPlaceholderText("Filter controls by name, automation ID, or class...")
        self.search_input.textChanged.connect(self._apply_filters)
        filter_row.addWidget(self.search_input, stretch=1)

        self.type_filter_combo = QComboBox(central)
        self.type_filter_combo.addItems([
            "All Types",
            "Button",
            "Edit",
            "MenuItem",
            "TabItem",
            "Hyperlink",
            "CheckBox",
            "RadioButton",
            "ComboBox",
            "List",
            "ListItem",
            "Pane",
            "Text",
            "Document",
        ])
        self.type_filter_combo.currentTextChanged.connect(self._apply_filters)
        filter_row.addWidget(self.type_filter_combo)

        self.cb_visible_only = QCheckBox("Visible Only", central)
        self.cb_visible_only.setChecked(True)
        self.cb_visible_only.toggled.connect(self._apply_filters)
        filter_row.addWidget(self.cb_visible_only)

        self.cb_web_only = QCheckBox("Web Elements Only", central)
        self.cb_web_only.setChecked(False)
        self.cb_web_only.toggled.connect(self._apply_filters)
        filter_row.addWidget(self.cb_web_only)

        self.btn_clear_filter = QPushButton("Clear", central)
        self.btn_clear_filter.clicked.connect(self._clear_filters)
        filter_row.addWidget(self.btn_clear_filter)

        layout.addLayout(filter_row)

        # 4. Dual View Modes: Table View vs DOM/UIA Tree View
        self.tab_widget = QTabWidget(central)

        # 4.1 Flat Table View
        table_container = QWidget()
        t_layout = QVBoxLayout(table_container)
        t_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(table_container)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Type", "Name / Text", "Automation ID", "Coordinates (L, T, W, H)", "State", "Source"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_table_double_clicked)
        t_layout.addWidget(self.table)
        self.tab_widget.addTab(table_container, "📋 Flat Table View")

        # 4.2 Hierarchical DOM / UIA Tree View (Lazy Loaded)
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeWidget(tree_container)
        self.tree.setHeaderLabels(["DOM / Control Hierarchy", "Type", "Source", "Automation ID"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.tree.itemExpanded.connect(self._on_tree_item_expanded)
        self.tree.itemDoubleClicked.connect(lambda item, col: self.test_click_element())
        tree_layout.addWidget(self.tree)
        self.tab_widget.addTab(tree_container, "🌳 DOM / UIA Tree View (Lazy)")

        layout.addWidget(self.tab_widget, stretch=1)

        # 5. Bottom Action Suite & Status Bar
        actions_card = QFrame(central)
        actions_card.setProperty("class", "cardFrame")
        actions_layout = QHBoxLayout(actions_card)
        actions_layout.setContentsMargins(8, 6, 8, 6)
        actions_layout.setSpacing(8)

        self.btn_click = QPushButton("Test Click", actions_card)
        self.btn_click.setProperty("class", "accentButton")
        self.btn_click.setIcon(render_svg_icon(SVG_CLICK, 14, color="#FFFFFF"))
        self.btn_click.setToolTip("Simulate clicking this element")
        self.btn_click.clicked.connect(self.test_click_element)
        actions_layout.addWidget(self.btn_click)

        self.btn_type = QPushButton("Test Type Text", actions_card)
        self.btn_type.setIcon(render_svg_icon(SVG_CODE, 14, color="#E2E8F0"))
        self.btn_type.setToolTip("Send test typing keystrokes into this element")
        self.btn_type.clicked.connect(self.test_type_text)
        actions_layout.addWidget(self.btn_type)

        self.btn_scroll = QPushButton("Scroll Into View", actions_card)
        self.btn_scroll.setToolTip("Scroll window to reveal element via UIA ScrollItemPattern")
        self.btn_scroll.clicked.connect(self.scroll_into_view)
        actions_layout.addWidget(self.btn_scroll)

        self.btn_highlight = QPushButton("Highlight on Screen", actions_card)
        self.btn_highlight.setIcon(render_svg_icon(SVG_EYE, 14, color="#E2E8F0"))
        self.btn_highlight.clicked.connect(self.highlight_selected_element)
        actions_layout.addWidget(self.btn_highlight)

        actions_layout.addStretch(1)

        self.btn_copy_cmd = QPushButton("Copy Voice Command", actions_card)
        self.btn_copy_cmd.setIcon(render_svg_icon(SVG_COPY, 14, color="#E2E8F0"))
        self.btn_copy_cmd.clicked.connect(self.copy_voice_command)
        actions_layout.addWidget(self.btn_copy_cmd)

        self.btn_copy_id = QPushButton("Copy Auto ID", actions_card)
        self.btn_copy_id.setIcon(render_svg_icon(SVG_COPY, 14, color="#E2E8F0"))
        self.btn_copy_id.clicked.connect(self.copy_automation_id)
        actions_layout.addWidget(self.btn_copy_id)

        self.btn_copy_code = QPushButton("Copy 3-Tier Locator", actions_card)
        self.btn_copy_code.setIcon(render_svg_icon(SVG_CODE, 14, color="#E2E8F0"))
        self.btn_copy_code.clicked.connect(self.copy_python_locator)
        actions_layout.addWidget(self.btn_copy_code)

        self.btn_copy_macro = QPushButton("Copy Macro Step", actions_card)
        self.btn_copy_macro.clicked.connect(self.copy_macro_action)
        actions_layout.addWidget(self.btn_copy_macro)

        layout.addWidget(actions_card)

        # Status text
        self.status_lbl = QLabel("Ready. Select a window and click Scan Controls.", central)
        self.status_lbl.setProperty("class", "subLabel")
        layout.addWidget(self.status_lbl)

    # -----------------------------------------------------------------------
    # Window & Element Enumeration
    # -----------------------------------------------------------------------

    def refresh_windows(self) -> None:
        """Scan open desktop top-level application windows and populate dropdown."""
        current_data = self.window_combo.currentData()
        self.window_combo.blockSignals(True)
        self.window_combo.clear()
        self.window_combo.addItem("🎯 Active Focused Window (Auto-Detect)", None)

        self._windows_cache = self.uia.get_top_level_windows()
        for idx, win in enumerate(self._windows_cache):
            title = win.get("title", "")
            pid = win.get("pid", "")
            handle = win.get("handle", 0)
            is_chrom = is_chromium_window(handle)
            tag = "🌐 [Browser/Electron]" if is_chrom else "🪟"
            display = f"{tag} {title[:40]} (PID {pid})" if pid else f"{tag} {title[:50]}"
            self.window_combo.addItem(display, idx)

        self.window_combo.blockSignals(False)
        self.status_lbl.setText(f"Found {len(self._windows_cache)} open application windows.")

    def scan_target_window(self) -> None:
        """Enumerate controls in the targeted window with Chromium wake-up."""
        self.overlay.hide_overlay()
        target_idx = self.window_combo.currentData()

        target_win = None
        target_name = "Active Window"
        target_hwnd = None
        if target_idx is not None and 0 <= target_idx < len(self._windows_cache):
            target_win = self._windows_cache[target_idx].get("wrapper")
            target_name = self._windows_cache[target_idx].get("title", "Window")
            target_hwnd = self._windows_cache[target_idx].get("handle")
        else:
            target_win = self.uia.get_active_window()
            if target_win:
                try:
                    target_name = target_win.window_text() or "Active Window"
                    target_hwnd = getattr(target_win, "handle", None)
                except Exception:
                    pass

        if not target_win:
            self.status_lbl.setText("Error: Could not identify target application window.")
            return

        # 1. Auto-Wake Chromium UIA Accessibility
        if target_hwnd:
            if is_chromium_window(target_hwnd):
                self.status_lbl.setText(f"Waking Chromium accessibility engine in '{target_name[:35]}'...")
                QApplication.processEvents()
                wake_chromium_accessibility(target_hwnd)

        self.status_lbl.setText(f"Scanning controls in '{target_name}'...")
        QApplication.processEvents()

        try:
            rect_obj = target_win.rectangle()
            self._current_window_rect = {
                "left": rect_obj.left,
                "top": rect_obj.top,
                "width": rect_obj.width(),
                "height": rect_obj.height(),
            }
        except Exception:
            self._current_window_rect = None

        try:
            self._elements_cache = self.uia.inspect_window_elements(target_win)
            self._apply_filters()
            self._populate_tree_view(target_win, target_name)

            visible_count = sum(1 for e in self._elements_cache if e.get("is_visible"))
            web_count = sum(1 for e in self._elements_cache if e.get("is_web_content"))
            self.status_lbl.setText(
                f"Scanned {len(self._elements_cache)} controls ({visible_count} visible, {web_count} web DOM) in '{target_name}'."
            )
            self.lbl_window.setText(f"Window: {target_name[:40]}")
        except Exception as exc:
            logger.error("Scan controls failed: %s", exc)
            self.status_lbl.setText(f"Scan failed: {exc}")

    def _apply_filters(self) -> None:
        """Filter cached elements according to search text, control type, visibility, and web flag."""
        search_query = self.search_input.text().strip().lower()
        selected_type = self.type_filter_combo.currentText()
        visible_only = self.cb_visible_only.isChecked()
        web_only = self.cb_web_only.isChecked()

        filtered: List[Dict[str, Any]] = []
        for elem in self._elements_cache:
            if visible_only and not elem.get("is_visible", False):
                continue
            if web_only and not elem.get("is_web_content", False):
                continue
            if selected_type != "All Types" and elem.get("control_type", "").lower() != selected_type.lower():
                continue
            if search_query:
                name = elem.get("name", "").lower()
                auto_id = elem.get("auto_id", "").lower()
                ctype = elem.get("control_type", "").lower()
                if search_query not in name and search_query not in auto_id and search_query not in ctype:
                    continue
            filtered.append(elem)

        self._populate_table(filtered)

    def _clear_filters(self) -> None:
        self.search_input.clear()
        self.type_filter_combo.setCurrentIndex(0)
        self.cb_visible_only.setChecked(True)
        self.cb_web_only.setChecked(False)

    def _populate_table(self, elements: List[Dict[str, Any]]) -> None:
        """Populate the UI elements table with inspected metadata."""
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)

        for row_idx, elem in enumerate(elements):
            self.table.insertRow(row_idx)

            # Type
            type_item = QTableWidgetItem(elem.get("control_type", "Control"))
            type_item.setData(Qt.ItemDataRole.UserRole, elem)

            # Source Badge ([WEB] vs [APP])
            source_tag = elem.get("source_tag", "[APP]")
            source_item = QTableWidgetItem(source_tag)
            if source_tag == "[WEB]":
                source_item.setForeground(QColor("#34D399"))  # Emerald Green
            elif source_tag == "[SHELL]":
                source_item.setForeground(QColor("#F59E0B"))  # Amber
            else:
                source_item.setForeground(QColor("#38BDF8"))  # Sky Blue

            # Name / Text
            name_text = elem.get("name", "")
            name_item = QTableWidgetItem(name_text or "(unnamed)")
            if not name_text:
                name_item.setForeground(QColor("#64748B"))

            # Automation ID
            auto_id = elem.get("auto_id", "")
            id_item = QTableWidgetItem(auto_id)
            if not auto_id:
                id_item.setForeground(QColor("#64748B"))

            # Coordinates
            rect = elem.get("rect", {})
            coords_str = f"({rect.get('left', 0)}, {rect.get('top', 0)}, {rect.get('width', 0)}×{rect.get('height', 0)})"
            coord_item = QTableWidgetItem(coords_str)

            # State
            vis = "Visible" if elem.get("is_visible") else "Hidden"
            en = "Enabled" if elem.get("is_enabled") else "Disabled"
            state_item = QTableWidgetItem(f"{vis}, {en}")

            self.table.setItem(row_idx, 0, type_item)
            self.table.setItem(row_idx, 1, name_item)
            self.table.setItem(row_idx, 2, id_item)
            self.table.setItem(row_idx, 3, coord_item)
            self.table.setItem(row_idx, 4, state_item)
            self.table.setItem(row_idx, 5, source_item)

    # -----------------------------------------------------------------------
    # Hierarchical DOM / UIA Tree View (Lazy Loaded)
    # -----------------------------------------------------------------------

    def _populate_tree_view(self, target_win: Any, win_title: str) -> None:
        """Create root window node in the Tree Widget and populate top-level children lazily."""
        self.tree.clear()
        root_item = QTreeWidgetItem(self.tree)
        root_item.setText(0, f"🪟 {win_title}")
        root_item.setText(1, "Window")
        root_item.setText(2, "[ROOT]")
        auto_id_val = getattr(target_win, "automation_id", lambda: "")()
        root_item.setText(3, auto_id_val if isinstance(auto_id_val, str) else "")
        root_item.setData(0, Qt.ItemDataRole.UserRole, {
            "wrapper": target_win,
            "name": win_title,
            "control_type": "Window",
            "is_visible": True,
            "is_enabled": True,
            "source_tag": "[ROOT]",
            "rect": self._current_window_rect or {},
        })

        # Add dummy child so expansion arrow (+) appears
        dummy = QTreeWidgetItem(root_item)
        dummy.setText(0, "Loading controls...")
        root_item.setExpanded(True)

    def _on_tree_item_expanded(self, item: QTreeWidgetItem) -> None:
        """Lazily load direct children of an expanded tree item on demand."""
        # Check if already populated
        if item.childCount() == 1 and item.child(0).text(0) == "Loading controls...":
            item.takeChild(0)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if not data:
                return
            wrapper = data.get("wrapper")
            if not wrapper:
                return

            children = self.uia.get_element_children(wrapper)
            # Tag children with browser partitioning
            tagged_children = partition_browser_elements(children, window_title=self.lbl_window.text())

            for c in tagged_children:
                c_item = QTreeWidgetItem(item)
                icon_tag = "🌐" if c.get("is_web_content") else "🔹"
                c_item.setText(0, f"{icon_tag} {c.get('name') or '(unnamed)'}")
                c_item.setText(1, c.get("control_type", "Control"))
                c_item.setText(2, c.get("source_tag", "[APP]"))
                c_id = c.get("auto_id", "")
                c_item.setText(3, c_id if isinstance(c_id, str) else "")
                c_item.setData(0, Qt.ItemDataRole.UserRole, c)

                # Add dummy child for further nested lazy expansion if container
                if c.get("control_type") in ("Pane", "Group", "Window", "Document", "List", "Tree"):
                    c_dummy = QTreeWidgetItem(c_item)
                    c_dummy.setText(0, "Loading controls...")

    # -----------------------------------------------------------------------
    # Hover Mode & Click-to-Select Freeze
    # -----------------------------------------------------------------------

    def _toggle_hover_mode(self, checked: bool) -> None:
        if checked:
            self.btn_hover.setText("⏹ Stop Pick Mode (Click to Lock)")
            self.status_lbl.setText("🎯 Pick mode active! Hover over any element, or LEFT-CLICK to freeze & select.")
            self._hover_timer.start()
        else:
            self.btn_hover.setText("🎯 Live Hover / Pick Element")
            self._hover_timer.stop()
            self.status_lbl.setText("Pick mode stopped.")

    def _on_hover_tick(self) -> None:
        """Sample element directly under mouse cursor and check for Click-to-Select freeze."""
        try:
            # 1. Sample element at cursor point
            pos = pyautogui.position()
            elem = self.uia.inspect_element_at_point(pos.x, pos.y)
            if not elem:
                return

            # Avoid inspecting inspector's own window or overlay
            wrapper = elem.get("wrapper")
            if wrapper:
                try:
                    title = (wrapper.window_text() or "").strip()
                    if "Vyoma Handless" in title or "Desktop Element Inspector" in title or "Element Inspector" in title:
                        return
                except Exception:
                    pass

            # Tag element source
            elem_tagged = partition_browser_elements([elem], window_title=self.lbl_window.text())[0]
            self._selected_element = elem_tagged
            self._update_detail_card(elem_tagged)

            rect = elem_tagged.get("rect", {})
            label = f"[{elem_tagged.get('control_type', 'Control')}] {elem_tagged.get('name', '')[:25]}"
            badge = elem_tagged.get("source_tag", "[APP]")
            voice_cmd = self._current_locator.voice_command if self._current_locator else ""
            self.overlay.show_element(rect, label=label, badge=badge, voice_cmd=voice_cmd)

            # 2. Check if user clicked left mouse button to FREEZE selection
            # GetAsyncKeyState(0x01) checks physical state of VK_LBUTTON
            if (ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000) != 0:
                self._toggle_hover_mode(False)
                self.btn_hover.setChecked(False)
                self.raise_()
                self.activateWindow()
                self.status_lbl.setText(f"🔒 Locked element: '{self._selected_element.get('name', 'Control')}'.")
                self.highlight_selected_element()
                return
        except Exception as exc:
            logger.debug("Hover tick error: %s", exc)

    def _update_detail_card(self, elem: Dict[str, Any]) -> None:
        """Update top live inspection card and 3-tier resilient locator."""
        name = elem.get("name", "")
        ctype = elem.get("control_type", "Control")
        auto_id = elem.get("auto_id", "")
        rect = elem.get("rect", {})
        source_tag = elem.get("source_tag", "[APP]")

        display_title = name if name else f"Unnamed {ctype}"
        self.detail_title.setText(display_title[:55])
        self.type_badge.setText(ctype)

        # Source badge styling
        self.badge_source.setText(source_tag)
        if source_tag == "[WEB]":
            self.badge_source.setStyleSheet("background-color: #064E3B; color: #34D399; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 700;")
        elif source_tag == "[SHELL]":
            self.badge_source.setStyleSheet("background-color: #78350F; color: #FBBF24; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 700;")
        else:
            self.badge_source.setStyleSheet("background-color: #0369A1; color: #E0F2FE; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 700;")

        vis = "Visible" if elem.get("is_visible") else "Hidden"
        en = "Enabled" if elem.get("is_enabled") else "Disabled"
        self.state_badge.setText(f"{vis} • {en}")

        self.lbl_auto_id.setText(f"AutomationId: {auto_id or '—'}")
        self.lbl_coords.setText(f"Rect: ({rect.get('left')}, {rect.get('top')}, {rect.get('width')}×{rect.get('height')})")

        # Generate and display 3-Tier Resilient Locator Recipe
        self._current_locator = generate_resilient_locator(
            elem,
            window_rect=self._current_window_rect,
            siblings=self._elements_cache,
        )
        t1_text = self._current_locator.tier1_dynamic.get("code", "")[:45]
        t2_text = self._current_locator.tier2_structural.get("code", "")[:45]
        t3_text = self._current_locator.tier3_coordinate.get("code", "")[:45]

        self.lbl_tier1.setText(f"<b>Tier 1 (Dynamic):</b> <code>{t1_text}</code>")
        self.lbl_tier2.setText(f"<b>Tier 2 (Structural):</b> <code>{t2_text}</code>")
        self.lbl_tier3.setText(f"<b>Tier 3 (Coordinate):</b> <code>{t3_text}</code>")

    # -----------------------------------------------------------------------
    # Table & Tree Selection Synchronizers
    # -----------------------------------------------------------------------

    def _on_table_selection_changed(self) -> None:
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
        row = selected_items[0].row()
        item = self.table.item(row, 0)
        if item:
            elem = item.data(Qt.ItemDataRole.UserRole)
            if elem:
                self._selected_element = elem
                self._update_detail_card(elem)
                self.highlight_selected_element()

    def _on_tree_selection_changed(self) -> None:
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return
        item = selected_items[0]
        elem = item.data(0, Qt.ItemDataRole.UserRole)
        if elem:
            self._selected_element = elem
            self._update_detail_card(elem)
            self.highlight_selected_element()

    def _on_table_double_clicked(self, item: QTableWidgetItem) -> None:
        self.test_click_element()

    def highlight_selected_element(self) -> None:
        if not self._selected_element:
            return
        rect = self._selected_element.get("rect", {})
        label = f"[{self._selected_element.get('control_type', 'Control')}] {self._selected_element.get('name', '')[:25]}"
        badge = self._selected_element.get("source_tag", "[APP]")
        voice_cmd = self._current_locator.voice_command if self._current_locator else ""
        self.overlay.show_element(rect, label=label, badge=badge, voice_cmd=voice_cmd, flash_duration_ms=1600)

    # -----------------------------------------------------------------------
    # Automation Actions & Locators Playground
    # -----------------------------------------------------------------------

    def test_click_element(self) -> None:
        """Perform verified click on the selected element."""
        if not self._selected_element:
            QMessageBox.information(self, "No Element", "Please select an element first.")
            return

        elem = self._selected_element
        name = elem.get("name", "element")
        wrapper = elem.get("wrapper")

        try:
            clicked = False
            # 1. Try pywinauto wrapper click_input()
            if wrapper:
                try:
                    wrapper.click_input()
                    clicked = True
                except Exception:
                    pass

            # 2. Coordinate fallback click
            if not clicked:
                rect = elem.get("rect", {})
                cx = rect.get("left", 0) + (rect.get("width", 0) // 2)
                cy = rect.get("top", 0) + (rect.get("height", 0) // 2)
                if cx > 0 and cy > 0:
                    pyautogui.click(cx, cy)
                    clicked = True

            if clicked:
                self.status_lbl.setText(f"✓ Clicked '{name}'.")
            else:
                self.status_lbl.setText(f"Failed to click '{name}'.")
        except Exception as exc:
            self.status_lbl.setText(f"Click error: {exc}")

    def test_type_text(self) -> None:
        """Send typing text into the selected element."""
        if not self._selected_element:
            QMessageBox.information(self, "No Element", "Please select an element first.")
            return

        elem = self._selected_element
        name = elem.get("name", "element")

        dialog = QDialog(self)
        dialog.setWindowTitle("Test Type Text")
        dialog.setMinimumWidth(340)
        d_layout = QFormLayout(dialog)

        text_input = QLineEdit(dialog)
        text_input.setPlaceholderText("Enter test text to type...")
        d_layout.addRow("Text:", text_input)

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, dialog)
        bbox.accepted.connect(dialog.accept)
        bbox.rejected.connect(dialog.reject)
        d_layout.addRow(bbox)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            to_type = text_input.text()
            if to_type:
                try:
                    wrapper = elem.get("wrapper")
                    if wrapper:
                        try:
                            wrapper.set_focus()
                        except Exception:
                            pass
                    pyautogui.write(to_type, interval=0.03)
                    self.status_lbl.setText(f"✓ Typed '{to_type}' into '{name}'.")
                except Exception as exc:
                    self.status_lbl.setText(f"Type error: {exc}")

    def scroll_into_view(self) -> None:
        """Scroll window to bring off-screen element into view via UIA ScrollItemPattern."""
        if not self._selected_element:
            return
        wrapper = self._selected_element.get("wrapper")
        if wrapper and hasattr(wrapper, "scroll"):
            try:
                wrapper.scroll("down")
                self.status_lbl.setText("Scrolled Element into view.")
                self.highlight_selected_element()
                return
            except Exception:
                pass
        self.status_lbl.setText("Element already in view.")

    def copy_voice_command(self) -> None:
        """Copy speech command string to clipboard."""
        if not self._selected_element:
            return
        if not self._current_locator:
            self._current_locator = generate_resilient_locator(
                self._selected_element,
                window_rect=self._current_window_rect,
                siblings=self._elements_cache,
            )
        cmd = self._current_locator.voice_command if self._current_locator else f"click \"{self._selected_element.get('name', 'element')}\""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(cmd)
        self.last_copied = cmd
        QApplication.processEvents()
        self.status_lbl.setText(f"Copied voice command to clipboard: {cmd}")

    def copy_automation_id(self) -> None:
        """Copy automation ID to clipboard."""
        if not self._selected_element:
            return
        auto_id = self._selected_element.get("auto_id", "")
        if auto_id:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(auto_id)
            self.last_copied = auto_id
            QApplication.processEvents()
            self.status_lbl.setText(f"Copied Automation ID: {auto_id}")
        else:
            self.status_lbl.setText("Selected element has no Automation ID.")

    def copy_python_locator(self) -> None:
        """Copy resilient 3-tier Python snippet to clipboard."""
        if not self._selected_element:
            return
        if not self._current_locator:
            self._current_locator = generate_resilient_locator(
                self._selected_element,
                window_rect=self._current_window_rect,
                siblings=self._elements_cache,
            )
        code = self._current_locator.python_code
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(code)
        self.last_copied = code
        QApplication.processEvents()
        self.status_lbl.setText("Copied 3-Tier Python Locator to clipboard.")

    def copy_macro_action(self) -> None:
        """Copy JSON macro action snippet for Handless workflow automation."""
        if not self._selected_element:
            return
        if not self._current_locator:
            self._current_locator = generate_resilient_locator(
                self._selected_element,
                window_rect=self._current_window_rect,
                siblings=self._elements_cache,
            )
        macro_json = json.dumps(self._current_locator.macro_action, indent=2)
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(macro_json)
        self.last_copied = macro_json
        QApplication.processEvents()
        self.status_lbl.setText("Copied Macro Action JSON to clipboard.")
        self.status_lbl.setText("Copied Macro Action JSON to clipboard.")

    def _check_cdp_status(self) -> None:
        """Query Chrome/Edge CDP port 9222 and display active web tabs."""
        if not self.cdp.is_available():
            QMessageBox.information(
                self,
                "CDP Bridge Status",
                "Chrome/Edge DevTools port (localhost:9222) is not active.\n\n"
                "Tip: You can launch Chrome with:\n"
                "chrome.exe --remote-debugging-port=9222\n\n"
                "In the meantime, Handless is using deep Chromium UIA accessibility with full DOM access!",
            )
            return

        tabs = self.cdp.get_open_tabs()
        tab_list = "\n".join(f"• {t.get('title', 'Tab')} ({t.get('url')[:45]}...)" for t in tabs[:6])
        QMessageBox.information(
            self,
            "CDP Connected ✓",
            f"Successfully connected to Chrome DevTools Protocol!\n\nOpen Tabs ({len(tabs)}):\n{tab_list}",
        )

    def closeEvent(self, event: Any) -> None:
        self._hover_timer.stop()
        self.overlay.hide_overlay()
        self.overlay.close()
        super().closeEvent(event)
