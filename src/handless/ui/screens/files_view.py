"""Files Screen for Vyoma Handless.

Matches the Files screen design:
- Header: "Files" + "Find, organize, and work with your files — without hands." + 3D Folder sculpture
- Search bar: "Search files, folders, or ask Handless..."
- Category filter pills: All, Documents, Images, Videos, Audio, Other
- Quick actions (4 horizontal cards): Find a file, Summarize a file, Analyze image, Organize files
- Recent files list: Project_Proposal.pdf, Meeting_Notes.docx, Budget_2026.xlsx, Thumbnail.png, Intro_Video.mp4
- Storage overview card: "86.4 GB used of 476 GB" (18%) with segmented progress bar and category metrics
- Bottom Synchronized Prompt Bar: "Tell Handless what to do with your files..."
"""

from __future__ import annotations

import logging
import os
import shutil
from typing import Callable, List, Optional

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
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

from handless.ui.icons import (
    SVG_ARROW_UP,
    SVG_CLOUD_SEARCH,
    SVG_FILE_TEXT,
    SVG_FOLDER,
    SVG_IMAGE,
    SVG_MORE_HORIZONTAL,
    SVG_MUSIC,
    SVG_PAPERCLIP,
    SVG_PLAY,
    SVG_SEARCH,
    SVG_STORAGE,
    SVG_VOICE_WAVE,
    render_svg_icon,
    render_svg_pixmap,
)
from .illustrations import Files3DIllustration

logger = logging.getLogger(__name__)


class StorageProgressBar(QWidget):
    """Segmented dual-color storage progress bar."""

    def __init__(self, parent: Optional[QWidget] = None, percentage: float = 0.18) -> None:
        super().__init__(parent)
        self.percentage = percentage
        self.setFixedHeight(8)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = h / 2.0

        # Background track
        painter.setBrush(QColor(230, 228, 222))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, w, h, radius, radius)

        # Active filled bar
        fill_w = max(int(w * self.percentage), int(radius * 2))
        painter.setBrush(QColor(24, 24, 27))
        painter.drawRoundedRect(0, 0, fill_w, h, radius, radius)


class FilesScreenView(QWidget):
    """Complete Files Screen for Vyoma Handless."""
    command_submitted = Signal(str)
    voice_toggled = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("filesScreenView")

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(14, 10, 14, 10)
        outer_layout.setSpacing(10)

        # Scroll Area for all sections
        scroll = QScrollArea(self)
        scroll.setObjectName("chatScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        if scroll.viewport():
            scroll.viewport().setStyleSheet("background-color: transparent;")

        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(2, 2, 2, 8)
        c_layout.setSpacing(14)

        # 1. Header (Files + Subtitle + 3D Folder Sculpture)
        header_widget = self._build_header()
        c_layout.addWidget(header_widget)

        # 2. Full-Width Search Bar
        search_bar = self._build_search_bar()
        c_layout.addWidget(search_bar)

        # 3. Category Filter Pills
        pills_row = self._build_filter_pills()
        c_layout.addWidget(pills_row)

        # 4. Quick Actions (4 Horizontal Tiles)
        quick_actions = self._build_quick_actions()
        c_layout.addWidget(quick_actions)

        # 5. Recent Files List
        recent_files = self._build_recent_files()
        c_layout.addWidget(recent_files)

        # 6. Storage Overview Card
        storage_card = self._build_storage_overview()
        c_layout.addWidget(storage_card)

        c_layout.addStretch(1)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll, stretch=1)

        # 7. Synchronized Bottom Prompt Bar
        bottom_bar = self._build_bottom_bar()
        outer_layout.addWidget(bottom_bar)

    def _build_header(self) -> QWidget:
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        title = QLabel("Files", header)
        title.setStyleSheet("color: #18181B; font-size: 22px; font-weight: 700; font-family: 'Playfair Display', 'Georgia', serif;")
        title_col.addWidget(title)

        sub = QLabel("Find, organize, and work with\nyour files — without hands.", header)
        sub.setStyleSheet("color: #71717A; font-size: 11px; line-height: 1.35;")
        title_col.addWidget(sub)

        h_layout.addLayout(title_col, stretch=1)

        # 3D Folder Sculpture
        folder_3d = Files3DIllustration(header, width=95, height=90)
        h_layout.addWidget(folder_3d, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        return header

    def _build_search_bar(self) -> QWidget:
        pill = QFrame()
        pill.setStyleSheet("QFrame { background-color: #FAF9F5; border: 1px solid #E6E2D6; border-radius: 16px; } QFrame:focus-within { border-color: #18181B; background-color: #FFFFFF; }")
        layout = QHBoxLayout(pill)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        lens = QLabel(pill)
        lens.setPixmap(render_svg_pixmap(SVG_SEARCH, 14, 14, color="#71717A"))
        layout.addWidget(lens)

        self.file_search = QLineEdit(pill)
        self.file_search.setPlaceholderText("Search files, folders, or ask Handless...")
        self.file_search.setStyleSheet("border: none; background: transparent; color: #18181B; font-size: 11.5px;")
        self.file_search.returnPressed.connect(lambda: self.command_submitted.emit(f"search files for {self.file_search.text()}"))
        layout.addWidget(self.file_search, stretch=1)

        return pill

    def _build_filter_pills(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        categories = [
            ("All", None, True),
            ("Documents", SVG_FILE_TEXT, False),
            ("Images", SVG_IMAGE, False),
            ("Videos", SVG_PLAY, False),
            ("Audio", SVG_MUSIC, False),
            ("Other", None, False),
        ]

        self.pill_btns = []
        for name, svg, active in categories:
            btn = QPushButton(name, container)
            if active:
                btn.setStyleSheet("QPushButton { background-color: #18181B; color: #FFFFFF; border-radius: 12px; padding: 4px 10px; font-size: 10.5px; font-weight: 600; border: none; }")
            else:
                btn.setStyleSheet("QPushButton { background-color: #FAF9F5; color: #52525B; border: 1px solid #E6E2D6; border-radius: 12px; padding: 4px 8px; font-size: 10.5px; font-weight: 500; } QPushButton:hover { background-color: #F0ECE1; color: #18181B; }")
            if svg:
                btn.setIcon(render_svg_icon(svg, 12, color="#FFFFFF" if active else "#52525B"))
                btn.setIconSize(QSize(12, 12))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, b=btn: self._select_pill(b))
            layout.addWidget(btn)
            self.pill_btns.append(btn)

        layout.addStretch(1)
        return container

    def _select_pill(self, active_btn: QPushButton) -> None:
        for b in self.pill_btns:
            if b == active_btn:
                b.setStyleSheet("QPushButton { background-color: #18181B; color: #FFFFFF; border-radius: 12px; padding: 4px 10px; font-size: 10.5px; font-weight: 600; border: none; }")
            else:
                b.setStyleSheet("QPushButton { background-color: #FAF9F5; color: #52525B; border: 1px solid #E6E2D6; border-radius: 12px; padding: 4px 8px; font-size: 10.5px; font-weight: 500; } QPushButton:hover { background-color: #F0ECE1; color: #18181B; }")

    def _build_quick_actions(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        t = QLabel("Quick actions", container)
        t.setStyleSheet("color: #18181B; font-size: 13.5px; font-weight: 700;")
        hdr.addWidget(t)
        hdr.addStretch(1)
        see_all = QPushButton("See all →", container)
        see_all.setStyleSheet("background: transparent; border: none; color: #71717A; font-size: 11px;")
        hdr.addWidget(see_all)
        layout.addLayout(hdr)

        # 2x2 Grid for spacious, unclipped tiles
        grid_col = QVBoxLayout()
        grid_col.setSpacing(6)

        actions = [
            ("Find a file", "Search across your PC", SVG_CLOUD_SEARCH, "find latest downloaded files"),
            ("Summarize a file", "Get key points & notes", SVG_FILE_TEXT, "summarize latest document"),
            ("Analyze image", "Read, OCR & explain", SVG_IMAGE, "analyze latest screenshot"),
            ("Organize files", "Sort & manage folders", SVG_FOLDER, "organize downloads folder"),
        ]

        def _make_action_card(name: str, sub: str, svg: str, cmd: str) -> QWidget:
            card = QPushButton(container)
            card.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    border: 1px solid #ECE7DC;
                    border-radius: 12px;
                    padding: 8px 10px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #FAF9F5;
                    border-color: #D2CDC0;
                }
            """)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(4, 4, 4, 4)
            c_layout.setSpacing(8)

            i_lbl = QLabel(card)
            i_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            i_lbl.setPixmap(render_svg_pixmap(svg, 18, 18, color="#18181B"))
            i_lbl.setFixedSize(22, 22)
            c_layout.addWidget(i_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)

            txt_col = QVBoxLayout()
            txt_col.setContentsMargins(0, 0, 0, 0)
            txt_col.setSpacing(1)

            n_lbl = QLabel(name, card)
            n_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            n_lbl.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 700; border: none; background: transparent;")
            txt_col.addWidget(n_lbl)

            s_lbl = QLabel(sub, card)
            s_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            s_lbl.setStyleSheet("color: #71717A; font-size: 9.5px; border: none; background: transparent;")
            txt_col.addWidget(s_lbl)
            c_layout.addLayout(txt_col, stretch=1)

            card.clicked.connect(lambda checked=False, c=cmd: self.command_submitted.emit(c))
            return card

        r1 = QHBoxLayout()
        r1.setSpacing(6)
        r1.addWidget(_make_action_card(*actions[0]))
        r1.addWidget(_make_action_card(*actions[1]))
        grid_col.addLayout(r1)

        r2 = QHBoxLayout()
        r2.setSpacing(6)
        r2.addWidget(_make_action_card(*actions[2]))
        r2.addWidget(_make_action_card(*actions[3]))
        grid_col.addLayout(r2)

        layout.addLayout(grid_col)
        return container

    def _build_recent_files(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        t = QLabel("Recent files", container)
        t.setStyleSheet("color: #18181B; font-size: 13.5px; font-weight: 700;")
        hdr.addWidget(t)
        hdr.addStretch(1)
        see_all = QPushButton("See all →", container)
        see_all.setStyleSheet("background: transparent; border: none; color: #71717A; font-size: 11px;")
        hdr.addWidget(see_all)
        layout.addLayout(hdr)

        files = [
            ("Project_Proposal.pdf", "Documents · 2 mins ago", "#EF4444", "PDF"),
            ("Meeting_Notes.docx", "Documents · 1 hour ago", "#2563EB", "W"),
            ("Budget_2026.xlsx", "Documents · 3 hours ago", "#10B981", "X"),
            ("Thumbnail.png", "Images · 5 hours ago", "#8B5CF6", "IMG"),
            ("Intro_Video.mp4", "Videos · 1 day ago", "#6366F1", "VID"),
        ]

        for name, sub, color, badge_text in files:
            row = QFrame(container)
            row.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #E8E5DC; border-radius: 12px; } QFrame:hover { background-color: #FAF9F5; }")
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(10, 6, 8, 6)
            r_layout.setSpacing(10)

            badge = QLabel(badge_text, row)
            badge.setStyleSheet(f"background-color: {color}; color: #FFFFFF; font-size: 9px; font-weight: 700; border-radius: 6px; padding: 4px 6px;")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(26, 26)
            r_layout.addWidget(badge)

            txt_col = QVBoxLayout()
            txt_col.setSpacing(1)
            t_lbl = QLabel(name, row)
            t_lbl.setStyleSheet("color: #18181B; font-size: 11.5px; font-weight: 600; border: none; background: transparent;")
            txt_col.addWidget(t_lbl)

            s_lbl = QLabel(sub, row)
            s_lbl.setStyleSheet("color: #71717A; font-size: 9.5px; border: none; background: transparent;")
            txt_col.addWidget(s_lbl)
            r_layout.addLayout(txt_col, stretch=1)

            more_btn = QPushButton(row)
            more_btn.setIcon(render_svg_icon(SVG_MORE_HORIZONTAL, 14, color="#71717A"))
            more_btn.setFixedSize(22, 22)
            more_btn.setStyleSheet("background: transparent; border: none;")
            r_layout.addWidget(more_btn)

            row.mousePressEvent = lambda e, fn=name: self._handle_file_click(fn)
            layout.addWidget(row)

        return container

    def _handle_file_click(self, file_name: str) -> None:
        self.command_submitted.emit(f"open {file_name}")

    def _build_storage_overview(self) -> QWidget:
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: #FAF9F5; border: 1px solid #E6E1D4; border-radius: 16px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header Row: "Storage overview" + "Manage →"
        hdr = QHBoxLayout()
        t = QLabel("Storage overview", card)
        t.setStyleSheet("color: #18181B; font-size: 12.5px; font-weight: 700; border: none; background: transparent;")
        hdr.addWidget(t)

        hdr.addStretch(1)

        manage = QPushButton("Manage →", card)
        manage.setStyleSheet("background: transparent; border: none; color: #71717A; font-size: 10.5px;")
        manage.setCursor(Qt.CursorShape.PointingHandCursor)
        manage.clicked.connect(lambda: self.command_submitted.emit("open disk storage cleanup"))
        hdr.addWidget(manage)
        layout.addLayout(hdr)

        # Stats Row: "86.4 GB used of 476 GB" + "18%"
        stats_row = QHBoxLayout()
        used_lbl = QLabel("86.4 GB used of 476 GB", card)
        used_lbl.setStyleSheet("color: #71717A; font-size: 10px; border: none; background: transparent;")
        stats_row.addWidget(used_lbl)

        stats_row.addStretch(1)

        pct_lbl = QLabel("18%", card)
        pct_lbl.setStyleSheet("color: #18181B; font-size: 10.5px; font-weight: 700; border: none; background: transparent;")
        stats_row.addWidget(pct_lbl)
        layout.addLayout(stats_row)

        # Segmented Progress Bar
        bar = StorageProgressBar(card, percentage=0.18)
        layout.addWidget(bar)

        # 4 Category Metrics (Documents, Images, Videos, Other)
        cat_row = QHBoxLayout()
        cat_row.setSpacing(4)

        categories = [
            ("Documents", "31.2 GB", "#3B82F6"),
            ("Images", "18.7 GB", "#F59E0B"),
            ("Videos", "28.4 GB", "#EF4444"),
            ("Other", "8.1 GB", "#10B981"),
        ]

        for name, size_str, dot_color in categories:
            col = QVBoxLayout()
            col.setSpacing(2)

            d_row = QHBoxLayout()
            d_row.setSpacing(3)
            dot = QLabel("●", card)
            dot.setStyleSheet(f"color: {dot_color}; font-size: 8px; border: none; background: transparent;")
            d_row.addWidget(dot)

            nl = QLabel(name, card)
            nl.setStyleSheet("color: #71717A; font-size: 9px; border: none; background: transparent;")
            d_row.addWidget(nl)
            col.addLayout(d_row)

            sz = QLabel(size_str, card)
            sz.setStyleSheet("color: #18181B; font-size: 9.5px; font-weight: 600; border: none; background: transparent; padding-left: 9px;")
            col.addWidget(sz)

            cat_row.addLayout(col)

        layout.addLayout(cat_row)
        return card

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
        self.input_field.setPlaceholderText("Tell Handless what to do with your files...")
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
