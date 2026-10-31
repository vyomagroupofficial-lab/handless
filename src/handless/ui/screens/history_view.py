"""History Screen for Vyoma Handless.

Matches the History screen design:
- Header: "History" + "Everything Handless has done for you." + "Review, search, and manage your past tasks and activities." + 3D Clock sculpture
- 4 Stat/Metric Cards computed from the HistoryJournal: tasks, dictations, words, apps
- Search & Filter:
  - Search bar: "Search your history... (e.g. \"show my Chrome tasks\")"
  - "All time ⌵" dropdown pill
- Category filter pills: All, Dictation (Wispr Flow), Apps, Files, Web, System, Automation
- Wispr Flow Dictation History integration:
  - Raw speech vs Cleaned AI output
  - 4 Cleanup Levels (None, Light, Medium, High)
  - 1-click Raw Diff toggle
  - 1-click Copy, 1-click Re-Paste, 1-click Revert to Raw
- Timeline Activity Feed:
  - Today
  - Yesterday
- Bottom Synchronized Prompt Bar: "Tell Handless what to do..."
"""

from __future__ import annotations

import logging
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from handless.dictation.history_journal import HistoryEntry, HistoryJournal
from handless.dictation.paste_controller import paste_text
from handless.ui.icons import (
    SVG_APPS_GRID,
    SVG_ARROW_UP,
    SVG_BRAND_CHROME,
    SVG_BRAND_EDGE,
    SVG_BRAND_GMAIL,
    SVG_BRAND_NOTION,
    SVG_BRAND_VSCODE,
    SVG_BRAND_YOUTUBE,
    SVG_CHECK,
    SVG_CLOCK,
    SVG_COPY,
    SVG_DOWNLOAD,
    SVG_FILE_TEXT,
    SVG_FOLDER,
    SVG_GLOBE,
    SVG_IMAGE,
    SVG_LIGHTNING,
    SVG_MORE_HORIZONTAL,
    SVG_PAPERCLIP,
    SVG_REFRESH,
    SVG_SEARCH,
    SVG_SETTINGS,
    SVG_SPARKLE,
    SVG_VOICE_WAVE,
    render_svg_icon,
    render_svg_pixmap,
)
from .illustrations import History3DIllustration

logger = logging.getLogger(__name__)


class TimelineNodeWidget(QWidget):
    """Vertical timeline connecting line with a circular node dot."""

    def __init__(self, is_first: bool = False, is_last: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.is_first = is_first
        self.is_last = is_last
        self.setFixedWidth(16)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0

        # Draw vertical connecting line
        pen = QPen(QColor(220, 218, 212), 1.5)
        painter.setPen(pen)

        top_y = cy if self.is_first else 0.0
        bottom_y = cy if self.is_last else float(h)
        painter.drawLine(int(cx), int(top_y), int(cx), int(bottom_y))

        # Draw circle dot
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(113, 113, 122))  # #71717A
        dot_radius = 2.8
        painter.drawEllipse(QPoint(int(cx), int(cy)), dot_radius, dot_radius)


class TimelineRowWidget(QFrame):
    """An activity timeline row matching the reference design."""
    clicked = Signal(str)

    def __init__(
        self,
        title: str,
        subtitle: str,
        timestamp: str,
        status: str,  # "Completed" or "Failed"
        icon_type: str,  # "chrome", "youtube", "word", "folder", "settings", "edge", "notion", "vscode", "gmail", "excel", "image"
        is_first: bool = False,
        is_last: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.task_title = title
        self.setObjectName("timelineRow")
        self.setStyleSheet("""
            QFrame#timelineRow {
                background-color: transparent;
                border: none;
                border-radius: 8px;
            }
            QFrame#timelineRow:hover {
                background-color: #F8F7F3;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 4, 0)
        layout.setSpacing(8)

        # 1. Timeline node & connecting line
        node = TimelineNodeWidget(is_first=is_first, is_last=is_last, parent=self)
        layout.addWidget(node)

        # 2. App / File Icon
        icon_widget = self._create_icon_widget(icon_type)
        layout.addWidget(icon_widget)

        # 3. Title & Subtitle column
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(1)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_lbl = QLabel(title, self)
        title_lbl.setStyleSheet("color: #18181B; font-size: 11.5px; font-weight: 600; border: none; background: transparent;")
        title_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text_col.addWidget(title_lbl)

        sub_lbl = QLabel(subtitle, self)
        sub_lbl.setStyleSheet("color: #71717A; font-size: 9.5px; border: none; background: transparent;")
        sub_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text_col.addWidget(sub_lbl)
        layout.addLayout(text_col, stretch=1)

        # 4. Timestamp
        time_lbl = QLabel(timestamp, self)
        time_lbl.setStyleSheet("color: #71717A; font-size: 10px; border: none; background: transparent;")
        time_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(time_lbl)

        # 5. Status Badge ("Completed" / "Failed")
        badge = QLabel(status, self)
        if status.lower() == "completed":
            badge.setStyleSheet("""
                background-color: #DCFCE7;
                color: #15803D;
                font-size: 9px;
                font-weight: 700;
                border-radius: 9px;
                padding: 2px 7px;
                border: none;
            """)
        else:
            badge.setStyleSheet("""
                background-color: #FEE2E2;
                color: #B91C1C;
                font-size: 9px;
                font-weight: 700;
                border-radius: 9px;
                padding: 2px 7px;
                border: none;
            """)
        badge.setFixedHeight(18)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(badge)

        # 6. Action button (three dots)
        menu_btn = QPushButton(self)
        menu_btn.setIcon(render_svg_icon(SVG_MORE_HORIZONTAL, 14, color="#A1A1AA"))
        menu_btn.setFixedSize(20, 20)
        menu_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ECEAE4;
            }
        """)
        menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(menu_btn)

    def _create_icon_widget(self, icon_type: str) -> QWidget:
        """Create a 26x26 app/file icon container."""
        container = QWidget(self)
        container.setFixedSize(26, 26)
        container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if icon_type == "chrome":
            lbl = QLabel(container)
            lbl.setPixmap(render_svg_pixmap(SVG_BRAND_CHROME, 22, 22))
            c_layout.addWidget(lbl)
        elif icon_type == "youtube":
            lbl = QLabel(container)
            lbl.setPixmap(render_svg_pixmap(SVG_BRAND_YOUTUBE, 22, 22))
            c_layout.addWidget(lbl)
        elif icon_type == "word":
            lbl = QLabel("W", container)
            lbl.setFixedSize(24, 24)
            lbl.setStyleSheet("background-color: #2563EB; color: #FFFFFF; font-size: 11px; font-weight: 800; border-radius: 6px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c_layout.addWidget(lbl)
        elif icon_type == "folder":
            lbl = QLabel(container)
            lbl.setPixmap(render_svg_pixmap(SVG_FOLDER, 20, 20, color="#4B5563"))
            c_layout.addWidget(lbl)
        elif icon_type == "settings":
            lbl = QLabel(container)
            lbl.setPixmap(render_svg_pixmap(SVG_SETTINGS, 20, 20, color="#4B5563"))
            c_layout.addWidget(lbl)
        elif icon_type == "edge":
            lbl = QLabel(container)
            lbl.setPixmap(render_svg_pixmap(SVG_BRAND_EDGE, 22, 22))
            c_layout.addWidget(lbl)
        elif icon_type == "notion":
            lbl = QLabel(container)
            lbl.setPixmap(render_svg_pixmap(SVG_BRAND_NOTION, 22, 22))
            c_layout.addWidget(lbl)
        elif icon_type == "vscode":
            lbl = QLabel(container)
            lbl.setPixmap(render_svg_pixmap(SVG_BRAND_VSCODE, 22, 22))
            c_layout.addWidget(lbl)
        elif icon_type == "gmail":
            lbl = QLabel(container)
            lbl.setPixmap(render_svg_pixmap(SVG_BRAND_GMAIL, 22, 22))
            c_layout.addWidget(lbl)
        elif icon_type == "excel":
            lbl = QLabel("X", container)
            lbl.setFixedSize(24, 24)
            lbl.setStyleSheet("background-color: #10B981; color: #FFFFFF; font-size: 11px; font-weight: 800; border-radius: 6px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c_layout.addWidget(lbl)
        elif icon_type == "image":
            lbl = QLabel(container)
            lbl.setPixmap(render_svg_pixmap(SVG_IMAGE, 20, 20, color="#4B5563"))
            c_layout.addWidget(lbl)
        else:
            lbl = QLabel(container)
            lbl.setPixmap(render_svg_pixmap(SVG_FILE_TEXT, 20, 20, color="#4B5563"))
            c_layout.addWidget(lbl)

        return container

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.task_title)
        super().mousePressEvent(event)


class DictationRowWidget(QFrame):
    """An interactive card for a recorded dictation session.
    
    Includes:
    - App badge and spoken language code (100+ languages)
    - Cleanup level badge (None, Light, Medium, High)
    - Expandable raw transcript view
    - 1-click Copy to clipboard
    - 1-click Re-Paste into active window
    - 1-click Revert to raw speech
    """
    revert_requested = Signal(str, str)  # (cleaned_text, raw_text)

    def __init__(self, entry: HistoryEntry, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("dictationRow")
        self.setStyleSheet("""
            QFrame#dictationRow {
                background-color: #FFFFFF;
                border: 1px solid #ECEAE4;
                border-radius: 12px;
            }
            QFrame#dictationRow:hover {
                border-color: #D4D2C9;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 1. Header: Target App + Language + Cleanup Level + Time + Status
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(6)

        app_lbl = QLabel(f"💻 {entry.target_app or 'Desktop'}", self)
        app_lbl.setStyleSheet("background-color: #F4F4F5; color: #18181B; font-size: 10px; font-weight: 600; border-radius: 6px; padding: 2px 7px;")
        hdr.addWidget(app_lbl)

        lang_code = (entry.language or "en").upper()
        lang_lbl = QLabel(f"🌐 {lang_code}", self)
        lang_lbl.setStyleSheet("background-color: #EFF6FF; color: #1D4ED8; font-size: 10px; font-weight: 600; border-radius: 6px; padding: 2px 6px;")
        hdr.addWidget(lang_lbl)

        # Cleanup Level Tag
        lvl_color = "#4B5563"
        lvl_bg = "#F3F4F6"
        lvl_name = entry.cleanup_level.capitalize()
        if entry.cleanup_level.lower() == "light":
            lvl_color = "#1D4ED8"
            lvl_bg = "#DBEAFE"
        elif entry.cleanup_level.lower() == "medium":
            lvl_color = "#047857"
            lvl_bg = "#D1FAE5"
        elif entry.cleanup_level.lower() == "high":
            lvl_color = "#6D28D9"
            lvl_bg = "#EDE9FE"

        lvl_badge = QLabel(f"✦ {lvl_name}", self)
        lvl_badge.setStyleSheet(f"background-color: {lvl_bg}; color: {lvl_color}; font-size: 9.5px; font-weight: 700; border-radius: 6px; padding: 2px 6px;")
        hdr.addWidget(lvl_badge)

        hdr.addStretch(1)

        time_lbl = QLabel(entry.formatted_time, self)
        time_lbl.setStyleSheet("color: #71717A; font-size: 10px;")
        hdr.addWidget(time_lbl)

        st = entry.status.lower()
        st_color = "#15803D" if st == "completed" else ("#1D4ED8" if st == "recovered" else "#B91C1C")
        st_bg = "#DCFCE7" if st == "completed" else ("#DBEAFE" if st == "recovered" else "#FEE2E2")
        status_lbl = QLabel(entry.status.capitalize(), self)
        status_lbl.setStyleSheet(f"background-color: {st_bg}; color: {st_color}; font-size: 9px; font-weight: 700; border-radius: 6px; padding: 2px 6px;")
        hdr.addWidget(status_lbl)

        layout.addLayout(hdr)

        # 2. Text Content (Cleaned text)
        disp_text = entry.cleaned_text or entry.raw_text
        body_lbl = QLabel(disp_text, self)
        body_lbl.setStyleSheet("color: #18181B; font-size: 11.5px; font-weight: 500; line-height: 1.4;")
        body_lbl.setWordWrap(True)
        body_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(body_lbl)

        # 3. Collapsible Raw Diff Box
        self.diff_container = QWidget(self)
        self.diff_container.setVisible(False)
        self.diff_container.setStyleSheet("background-color: #F8F7F3; border-radius: 8px; border: 1px dashed #D4D2C9;")
        diff_layout = QVBoxLayout(self.diff_container)
        diff_layout.setContentsMargins(8, 6, 8, 6)
        diff_layout.setSpacing(3)

        raw_title = QLabel("Original Raw Transcript (Verbatim):", self.diff_container)
        raw_title.setStyleSheet("color: #71717A; font-size: 9px; font-weight: 600;")
        diff_layout.addWidget(raw_title)

        raw_lbl = QLabel(entry.raw_text or "(No raw transcript)", self.diff_container)
        raw_lbl.setStyleSheet("color: #991B1B; font-size: 10.5px; font-style: italic;")
        raw_lbl.setWordWrap(True)
        raw_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        diff_layout.addWidget(raw_lbl)

        layout.addWidget(self.diff_container)

        # Action Row (Compact & guaranteed to fit within card width)
        act_row = QHBoxLayout()
        act_row.setContentsMargins(0, 2, 0, 0)
        act_row.setSpacing(4)

        # Toggle Raw Diff
        self.diff_btn = QPushButton("Inspect Raw ▾", self)
        self.diff_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #ECEAE4;
                border-radius: 6px;
                color: #52525B;
                font-size: 9.5px;
                font-weight: 500;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background-color: #F4F4F5;
                color: #18181B;
            }
        """)
        self.diff_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.diff_btn.clicked.connect(self._toggle_diff)
        act_row.addWidget(self.diff_btn)

        act_row.addStretch(1)

        # Copy Button
        self.copy_btn = QPushButton("Copy", self)
        self.copy_btn.setIcon(render_svg_icon(SVG_COPY, 10, color="#52525B"))
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #F4F4F5;
                border: 1px solid #E4E4E7;
                border-radius: 6px;
                color: #18181B;
                font-size: 9.5px;
                font-weight: 600;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background-color: #E4E4E7;
            }
        """)
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._handle_copy)
        act_row.addWidget(self.copy_btn)

        # Re-Paste Button
        self.paste_btn = QPushButton("Re-Paste", self)
        self.paste_btn.setIcon(render_svg_icon(SVG_FILE_TEXT, 10, color="#52525B"))
        self.paste_btn.setStyleSheet("""
            QPushButton {
                background-color: #F4F4F5;
                border: 1px solid #E4E4E7;
                border-radius: 6px;
                color: #18181B;
                font-size: 9.5px;
                font-weight: 600;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background-color: #E4E4E7;
            }
        """)
        self.paste_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.paste_btn.clicked.connect(self._handle_repaste)
        act_row.addWidget(self.paste_btn)

        # Revert to Raw Button (shown when cleaned text differs from raw)
        if entry.cleaned_text and entry.raw_text and entry.cleaned_text.strip() != entry.raw_text.strip():
            self.revert_btn = QPushButton("Undo Edit", self)
            self.revert_btn.setIcon(render_svg_icon(SVG_REFRESH, 10, color="#92400E"))
            self.revert_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FEF3C7;
                    border: 1px solid #FDE68A;
                    border-radius: 6px;
                    color: #92400E;
                    font-size: 9.5px;
                    font-weight: 600;
                    padding: 2px 6px;
                }
                QPushButton:hover {
                    background-color: #FDE68A;
                }
            """)
            self.revert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.revert_btn.clicked.connect(self._handle_revert)
            act_row.addWidget(self.revert_btn)

        layout.addLayout(act_row)

    def _toggle_diff(self) -> None:
        vis = not self.diff_container.isVisible()
        self.diff_container.setVisible(vis)
        self.diff_btn.setText("Hide Raw ▴" if vis else "Inspect Raw ▾")

    def _handle_copy(self) -> None:
        import pyperclip
        txt = self.entry.cleaned_text or self.entry.raw_text
        pyperclip.copy(txt)
        self.copy_btn.setText("Copied! ✓")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("Copy"))

    def _handle_repaste(self) -> None:
        txt = self.entry.cleaned_text or self.entry.raw_text
        paste_text(txt)
        self.paste_btn.setText("Pasted! ✓")
        QTimer.singleShot(1500, lambda: self.paste_btn.setText("Re-Paste"))

    def _handle_revert(self) -> None:
        self.revert_requested.emit(self.entry.cleaned_text, self.entry.raw_text)
        paste_text(self.entry.raw_text)


class HistoryScreenView(QWidget):
    """Complete History Screen for Vyoma Handless."""
    command_submitted = Signal(str)
    voice_toggled = Signal()
    undo_dictation_requested = Signal(str, str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("historyScreenView")
        self.journal: Optional[HistoryJournal] = None
        self.active_category: str = "All"

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(14, 10, 14, 10)
        outer_layout.setSpacing(10)

        # Scroll Area for all sections
        scroll = QScrollArea(self)
        scroll.setObjectName("chatScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background-color: transparent; border: none;")

        self.content_widget = QWidget()
        self.content_widget.setObjectName("scrollContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 16)
        self.content_layout.setSpacing(16)

        # 1. Header (History + 3D Clock illustration)
        header_widget = self._build_header()
        self.content_layout.addWidget(header_widget)

        # 2. Metric Stat Cards Row (4 cards)
        metrics_widget = self._build_metrics_row()
        self.content_layout.addWidget(metrics_widget)

        # 3. Search and Dropdown Filter Row
        search_filter_widget = self._build_search_filter_row()
        self.content_layout.addWidget(search_filter_widget)

        # 4. Category Filter Pills
        pills_widget = self._build_category_pills()
        self.content_layout.addWidget(pills_widget)

        # 5. Dictation Section Container (Populated dynamically from HistoryJournal)
        self.dictation_container = QWidget(self.content_widget)
        self.dictation_layout = QVBoxLayout(self.dictation_container)
        self.dictation_layout.setContentsMargins(0, 0, 0, 0)
        self.dictation_layout.setSpacing(8)
        self.content_layout.addWidget(self.dictation_container)

        # 6-7. Illustrative timeline sections. Kept for the design reference but hidden:
        # the real activity feed above comes from the HistoryJournal.
        self.today_widget = self._build_today_section()
        self.content_layout.addWidget(self.today_widget)
        self.today_widget.setVisible(False)

        self.yesterday_widget = self._build_yesterday_section()
        self.content_layout.addWidget(self.yesterday_widget)
        self.yesterday_widget.setVisible(False)

        self.content_layout.addStretch(1)
        scroll.setWidget(self.content_widget)
        outer_layout.addWidget(scroll, stretch=1)

        # 8. Synchronized Bottom Prompt Bar
        self.bottom_bar = self._build_bottom_bar()
        outer_layout.addWidget(self.bottom_bar)

    def set_journal(self, journal: HistoryJournal) -> None:
        """Bind the persistent HistoryJournal to populate live dictations."""
        self.journal = journal
        self.refresh_dictations()

    def refresh_dictations(self) -> None:
        """Re-render activity and dictation cards from the journal."""
        # Clear existing dictation widgets
        while self.dictation_layout.count():
            item = self.dictation_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.journal:
            self.dictation_container.setVisible(False)
            return

        self._refresh_metrics()

        sector_filter = None if self.active_category == "All" else self.active_category
        entries = self.journal.get_entries(limit=30, sector_filter=sector_filter)
        if not entries:
            empty_lbl = QLabel(f"No {self.active_category.lower()} activities recorded yet.", self.dictation_container)
            empty_lbl.setStyleSheet("color: #71717A; font-size: 11px; padding: 12px; font-style: italic;")
            self.dictation_layout.addWidget(empty_lbl)
            self.dictation_container.setVisible(True)
            return

        self.dictation_container.setVisible(True)

        # Header for Dictation / Sector Section
        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(2, 4, 2, 2)
        title_text = f"✦ {self.active_category} Sector Activity ({len(entries)})" if self.active_category != "All" else f"✦ Recent Activities ({len(entries)})"
        title_lbl = QLabel(title_text, self.dictation_container)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #18181B;")
        hdr_row.addWidget(title_lbl)

        hdr_row.addStretch(1)

        export_btn = QPushButton("Export Markdown", self.dictation_container)
        export_btn.setIcon(render_svg_icon(SVG_DOWNLOAD, 11, color="#71717A"))
        export_btn.setStyleSheet("color: #71717A; font-size: 10px; font-weight: 500; border: none; background: transparent;")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.clicked.connect(self._handle_export_markdown)
        hdr_row.addWidget(export_btn)

        self.dictation_layout.addLayout(hdr_row)

        for entry in entries:
            row = DictationRowWidget(entry, parent=self.dictation_container)
            row.revert_requested.connect(self._on_dictation_revert)
            self.dictation_layout.addWidget(row)

    def _refresh_metrics(self) -> None:
        entries = self.journal.get_entries(limit=100000) if self.journal else []
        dictations = [e for e in entries if e.entry_type == "dictation"]
        words = sum(len((e.cleaned_text or e.raw_text).split()) for e in dictations)
        apps = {e.target_app for e in entries if e.target_app and e.target_app != "Active Window"}
        values = {
            "tasks": len([e for e in entries if e.status == "completed"]),
            "dictations": len(dictations),
            "words": words,
            "apps": len(apps),
        }
        for key, value in values.items():
            label = self.metric_labels.get(key)
            if label is not None:
                label.setText(f"{value:,}")

    def _handle_export_markdown(self) -> None:
        if self.journal:
            out_file = self.journal.export_to_markdown()
            self.command_submitted.emit(f"Exported transcription history to {out_file.name}")

    def _on_dictation_revert(self, cleaned: str, raw: str) -> None:
        self.undo_dictation_requested.emit(cleaned, raw)

    def _build_header(self) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(2, 4, 2, 2)
        layout.setSpacing(10)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        title_lbl = QLabel("History", container)
        title_lbl.setStyleSheet("font-family: 'Playfair Display', Georgia, serif; font-size: 26px; font-weight: 700; color: #18181B; line-height: 1.1;")
        text_col.addWidget(title_lbl)

        sub_lbl = QLabel("Everything Handless has done for you.", container)
        sub_lbl.setStyleSheet("font-size: 12.5px; font-weight: 500; color: #52525B;")
        text_col.addWidget(sub_lbl)

        desc_lbl = QLabel("Review, search, and manage your past tasks, dictations, and activities.", container)
        desc_lbl.setStyleSheet("font-size: 10.5px; color: #71717A;")
        desc_lbl.setWordWrap(True)
        text_col.addWidget(desc_lbl)

        layout.addLayout(text_col, stretch=1)

        self.illustration = History3DIllustration(container)
        self.illustration.setFixedSize(94, 82)
        layout.addWidget(self.illustration)

        return container

    def _build_metrics_row(self) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Values are filled from the HistoryJournal in refresh_dictations()
        stats = [
            ("tasks", "0", "Tasks completed", "All time", SVG_SPARKLE),
            ("dictations", "0", "Dictations", "All time", SVG_VOICE_WAVE),
            ("words", "0", "Words dictated", "All time", SVG_FILE_TEXT),
            ("apps", "0", "Apps used", "All time", SVG_APPS_GRID),
        ]
        self.metric_labels: dict = {}

        for key, val, label_text, delta_text, svg_icon in stats:
            card = QFrame(container)
            card.setObjectName("metricStatCard")
            card.setStyleSheet("""
                QFrame#metricStatCard {
                    background-color: #FFFFFF;
                    border: 1px solid #ECEAE4;
                    border-radius: 12px;
                }
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(8, 8, 8, 8)
            c_layout.setSpacing(4)

            ic_lbl = QLabel(card)
            ic_lbl.setPixmap(render_svg_pixmap(svg_icon, 14, 14, color="#71717A"))
            c_layout.addWidget(ic_lbl)

            val_lbl = QLabel(val, card)
            val_lbl.setStyleSheet("color: #18181B; font-size: 17px; font-weight: 700; border: none; background: transparent;")
            c_layout.addWidget(val_lbl)
            self.metric_labels[key] = val_lbl

            lbl = QLabel(label_text, card)
            lbl.setStyleSheet("color: #71717A; font-size: 9.5px; border: none; background: transparent;")
            c_layout.addWidget(lbl)

            delta_lbl = QLabel(delta_text, card)
            delta_lbl.setStyleSheet("color: #A1A1AA; font-size: 9px; font-weight: 600; border: none; background: transparent;")
            c_layout.addWidget(delta_lbl)

            layout.addWidget(card)

        return container

    def _build_search_filter_row(self) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        search_card = QFrame(container)
        search_card.setObjectName("searchCard")
        search_card.setStyleSheet("""
            QFrame#searchCard {
                background-color: #F3F1EC;
                border: 1px solid #E8E6E0;
                border-radius: 17px;
            }
        """)
        search_card.setFixedHeight(34)
        s_layout = QHBoxLayout(search_card)
        s_layout.setContentsMargins(10, 0, 10, 0)
        s_layout.setSpacing(6)

        search_icon = QLabel(search_card)
        search_icon.setPixmap(render_svg_pixmap(SVG_SEARCH, 14, 14, color="#71717A"))
        s_layout.addWidget(search_icon)

        search_input = QLineEdit(search_card)
        search_input.setPlaceholderText('Search your history or dictations... (e.g. "meeting summary")')
        search_input.setStyleSheet("background: transparent; border: none; color: #18181B; font-size: 11px;")
        search_input.returnPressed.connect(lambda: self._handle_search(search_input.text()))
        s_layout.addWidget(search_input, stretch=1)
        layout.addWidget(search_card, stretch=1)

        filter_btn = QPushButton("All time  ⌵", container)
        filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #ECEAE4;
                border-radius: 17px;
                padding: 6px 12px;
                color: #18181B;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #F8F7F3;
            }
        """)
        filter_btn.setFixedHeight(34)
        filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(filter_btn)

        return container

    def _build_category_pills(self) -> QWidget:
        # Pills wrap onto a second line at narrow widths (see ui.responsive.flow_pill_rows)
        container = QWidget(self)
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        categories = [
            ("All", None, True),
            ("Dictation", SVG_VOICE_WAVE, False),
            ("Apps", SVG_APPS_GRID, False),
            ("Files", SVG_FILE_TEXT, False),
            ("Web", SVG_GLOBE, False),
            ("System", SVG_SETTINGS, False),
            ("Automation", SVG_LIGHTNING, False),
        ]

        self.cat_buttons = []
        for name, icon_svg, is_active in categories:
            btn = QPushButton(container)
            btn.setText(f"  {name}" if icon_svg else name)
            if icon_svg:
                btn.setIcon(render_svg_icon(icon_svg, 12, color="#18181B" if is_active else "#52525B"))

            if is_active:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #18181B;
                        color: #FFFFFF;
                        border-radius: 13px;
                        border: none;
                        font-size: 10.5px;
                        font-weight: 600;
                        padding: 4px 10px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FFFFFF;
                        color: #3F3F46;
                        border-radius: 13px;
                        border: 1px solid #ECEAE4;
                        font-size: 10.5px;
                        font-weight: 500;
                        padding: 4px 10px;
                    }
                    QPushButton:hover {
                        background-color: #F5F4EE;
                    }
                """)

            btn.setFixedHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, n=name: self._filter_category(n))
            self.cat_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch(1)
        return container

    def _build_today_section(self) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(2, 4, 2, 6)

        title = QLabel("Today", container)
        title.setStyleSheet("font-size: 13px; font-weight: 700; color: #18181B;")
        header_row.addWidget(title)

        header_row.addStretch(1)

        see_all = QPushButton("See all →", container)
        see_all.setStyleSheet("color: #71717A; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        see_all.setCursor(Qt.CursorShape.PointingHandCursor)
        header_row.addWidget(see_all)
        layout.addLayout(header_row)

        today_tasks = [
            ("Opened Chrome", "and searched for latest design trends", "4:58 PM", "Completed", "chrome"),
            ("Created a YouTube thumbnail", "using reference images", "4:32 PM", "Completed", "youtube"),
            ("Summarized a document", "Project_Proposal.pdf", "3:44 PM", "Completed", "word"),
            ("Organized Downloads folder", "Sorted files into categories", "2:18 PM", "Completed", "folder"),
            ("Changed system settings", "Adjusted display brightness", "1:03 PM", "Completed", "settings"),
            ("Researched latest AI news", "and summarized key points", "11:26 AM", "Completed", "edge"),
            ("Created meeting notes", "from today's discussion", "10:14 AM", "Completed", "notion"),
            ("Opened VS Code", "and started a new project", "9:02 AM", "Completed", "vscode"),
        ]

        total = len(today_tasks)
        for idx, (t, s, time_str, status, ic_type) in enumerate(today_tasks):
            is_first = (idx == 0)
            is_last = (idx == total - 1)
            row = TimelineRowWidget(t, s, time_str, status, ic_type, is_first=is_first, is_last=is_last, parent=container)
            row.clicked.connect(self._handle_timeline_click)
            layout.addWidget(row)

        return container

    def _build_yesterday_section(self) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(2, 10, 2, 6)

        title = QLabel("Yesterday", container)
        title.setStyleSheet("font-size: 13px; font-weight: 700; color: #18181B;")
        header_row.addWidget(title)

        header_row.addStretch(1)

        see_all = QPushButton("See all →", container)
        see_all.setStyleSheet("color: #71717A; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        see_all.setCursor(Qt.CursorShape.PointingHandCursor)
        header_row.addWidget(see_all)
        layout.addLayout(header_row)

        yesterday_tasks = [
            ("Checked unread emails", "and summarized important ones", "8:45 PM", "Completed", "gmail"),
            ("Analyzed budget sheet", "Created summary and charts", "6:20 PM", "Failed", "excel"),
            ("Generated images", "for social media post", "4:11 PM", "Completed", "image"),
        ]

        total = len(yesterday_tasks)
        for idx, (t, s, time_str, status, ic_type) in enumerate(yesterday_tasks):
            is_first = (idx == 0)
            is_last = (idx == total - 1)
            row = TimelineRowWidget(t, s, time_str, status, ic_type, is_first=is_first, is_last=is_last, parent=container)
            row.clicked.connect(self._handle_timeline_click)
            layout.addWidget(row)

        return container

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

    def _handle_search(self, query: str) -> None:
        if query.strip():
            self.command_submitted.emit(f"Search history: {query.strip()}")

    def _handle_timeline_click(self, title: str) -> None:
        self.command_submitted.emit(title)

    def _filter_category(self, category: str) -> None:
        self.active_category = category
        logger.info(f"Filtering history by category: {category}")
        for btn in self.cat_buttons:
            is_active = (btn.text().strip() == category)
            if is_active:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #18181B;
                        color: #FFFFFF;
                        border-radius: 14px;
                        border: none;
                        font-size: 11px;
                        font-weight: 600;
                        padding: 5px 12px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FFFFFF;
                        color: #3F3F46;
                        border-radius: 14px;
                        border: 1px solid #ECEAE4;
                        font-size: 11px;
                        font-weight: 500;
                        padding: 5px 12px;
                    }
                    QPushButton:hover {
                        background-color: #F5F4EE;
                    }
                """)

        if category == "All":
            self.today_widget.setVisible(True)
            self.yesterday_widget.setVisible(True)
            self.refresh_dictations()
        else:
            self.today_widget.setVisible(False)
            self.yesterday_widget.setVisible(False)
            self.refresh_dictations()
