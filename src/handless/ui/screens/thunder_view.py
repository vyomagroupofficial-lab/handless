"""Thunder (Automations) Screen for Vyoma Handless.

Matches the Thunder screen design:
- Header: "Thunder" + "BETA" pill + 3D metallic lightning bolt sculpture
- Tab filters: Discover, My Automations, Templates, Schedules
- Promo Banner: "Automate anything, with a simple prompt." + "Create automation +"
- Popular Automations (2x3 Grid with + buttons)
- Templates (5 Horizontal Tiles): Study Helper, Content Creator, Office Work, Developer, Personal
- Recent Automations (Execution Feed with live toggles and play buttons):
    * Daily email summary (toggle ON)
    * Research latest tech news (play button)
    * Organize Downloads folder (play button)
- Bottom Synchronized Prompt Bar: "Tell Handless what to automate..."
"""

from __future__ import annotations

import logging
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
    SVG_BRAND_GMAIL,
    SVG_BRAND_YOUTUBE,
    SVG_BRIEFCASE,
    SVG_CALENDAR,
    SVG_CHART_TRENDS,
    SVG_CODE_BRACKETS,
    SVG_FILE_TEXT,
    SVG_FOLDER,
    SVG_GRADUATION_CAP,
    SVG_LIGHTNING,
    SVG_MAIL,
    SVG_MORE_HORIZONTAL,
    SVG_PAPERCLIP,
    SVG_PLAY_OUTLINE,
    SVG_PLUS,
    SVG_SETTINGS,
    SVG_USER,
    SVG_VIDEO_CAMERA,
    SVG_VOICE_WAVE,
    render_svg_icon,
    render_svg_pixmap,
)
from .illustrations import Thunder3DIllustration

logger = logging.getLogger(__name__)


class ModernMiniToggle(QWidget):
    """Small green toggle switch for scheduled automations."""
    toggled = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None, checked: bool = True) -> None:
        super().__init__(parent)
        self.setFixedSize(32, 18)
        self._checked = checked
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, checked: bool) -> None:
        if self._checked != checked:
            self._checked = checked
            self.update()
            self.toggled.emit(self._checked)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.update()
            self.toggled.emit(self._checked)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = h / 2.0

        bg_color = QColor(16, 185, 129) if self._checked else QColor(228, 228, 231)
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, w, h, radius, radius)

        thumb_d = h - 4
        thumb_x = (w - thumb_d - 2) if self._checked else 2
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(thumb_x, 2, thumb_d, thumb_d)


class ThunderScreenView(QWidget):
    """Complete Thunder (Automations) Screen for Vyoma Handless."""
    command_submitted = Signal(str)
    voice_toggled = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("thunderScreenView")

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

        # 1. Header (Thunder + BETA + 3D Lightning Emblem)
        header_widget = self._build_header()
        c_layout.addWidget(header_widget)

        # 2. Tabs Row (Discover, My Automations, Templates, Schedules)
        tabs_row = self._build_tabs_row()
        c_layout.addWidget(tabs_row)

        # 3. Promo Banner Card
        promo_card = self._build_promo_card()
        c_layout.addWidget(promo_card)

        # 4. Popular Automations (2x3 Grid with + buttons)
        auto_grid = self._build_popular_automations()
        c_layout.addWidget(auto_grid)

        # 5. Templates (5 Quick Tiles)
        templates_widget = self._build_templates_section()
        c_layout.addWidget(templates_widget)

        # 6. Recent Automations (List with live toggles & play buttons)
        recent_widget = self._build_recent_automations()
        c_layout.addWidget(recent_widget)

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

        # Title + BETA badge
        t_row = QHBoxLayout()
        t_row.setSpacing(6)
        title = QLabel("Thunder", header)
        title.setStyleSheet("color: #18181B; font-size: 22px; font-weight: 700; font-family: 'Playfair Display', 'Georgia', serif;")
        t_row.addWidget(title)

        beta_badge = QLabel("BETA", header)
        beta_badge.setStyleSheet("background-color: #27272A; color: #FFFFFF; font-size: 9px; font-weight: 700; border-radius: 6px; padding: 2px 6px;")
        t_row.addWidget(beta_badge)
        t_row.addStretch(1)
        title_col.addLayout(t_row)

        sub = QLabel("Automations that work for you.", header)
        sub.setStyleSheet("color: #71717A; font-size: 11px; font-weight: 500;")
        title_col.addWidget(sub)

        desc = QLabel("Create powerful automations and let Handless\nhandle repetitive tasks — no hands needed.", header)
        desc.setStyleSheet("color: #71717A; font-size: 10px; line-height: 1.35;")
        title_col.addWidget(desc)

        h_layout.addLayout(title_col, stretch=1)

        # 3D Lightning Sculpture
        lightning_3d = Thunder3DIllustration(header, width=95, height=90)
        h_layout.addWidget(lightning_3d, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        return header

    def _build_tabs_row(self) -> QWidget:
        tabs_container = QWidget()
        layout = QHBoxLayout(tabs_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        tabs = ["Discover", "My Automations", "Templates", "Schedules"]
        self.tab_buttons = []
        for i, name in enumerate(tabs):
            btn = QPushButton(name, tabs_container)
            if i == 0:
                btn.setStyleSheet("QPushButton { background-color: #18181B; color: #FFFFFF; border-radius: 12px; padding: 5px 12px; font-size: 11px; font-weight: 600; border: none; }")
            else:
                btn.setStyleSheet("QPushButton { background-color: #FAF9F5; color: #52525B; border: 1px solid #E6E2D6; border-radius: 12px; padding: 5px 10px; font-size: 11px; font-weight: 500; } QPushButton:hover { background-color: #F0ECE1; color: #18181B; }")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, b=btn: self._select_tab(b))
            layout.addWidget(btn)
            self.tab_buttons.append(btn)

        layout.addStretch(1)
        return tabs_container

    def _select_tab(self, active_btn: QPushButton) -> None:
        for b in self.tab_buttons:
            if b == active_btn:
                b.setStyleSheet("QPushButton { background-color: #18181B; color: #FFFFFF; border-radius: 12px; padding: 5px 12px; font-size: 11px; font-weight: 600; border: none; }")
            else:
                b.setStyleSheet("QPushButton { background-color: #FAF9F5; color: #52525B; border: 1px solid #E6E2D6; border-radius: 12px; padding: 5px 10px; font-size: 11px; font-weight: 500; } QPushButton:hover { background-color: #F0ECE1; color: #18181B; }")

    def _build_promo_card(self) -> QWidget:
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: #FAF9F5; border: 1px solid #E6E1D4; border-radius: 18px; }")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 12, 12, 12)
        layout.setSpacing(10)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(4)

        tag = QLabel("TURN IDEAS INTO ACTIONS", card)
        tag.setStyleSheet("color: #71717A; font-size: 8.5px; font-weight: 700; letter-spacing: 0.8px;")
        text_col.addWidget(tag)

        title = QLabel(
            '<div style="font-size: 15px; font-weight: 700; color: #18181B; line-height: 1.15; font-family: \'Playfair Display\', \'Georgia\', serif;">'
            'Automate anything,<br>with a simple prompt.'
            '</div>',
            card,
        )
        title.setTextFormat(Qt.TextFormat.RichText)
        text_col.addWidget(title)

        sub = QLabel('e.g. "Check my emails every morning and\nsummarize important ones."', card)
        sub.setStyleSheet("color: #71717A; font-size: 9.5px; line-height: 1.3;")
        text_col.addWidget(sub)

        btn = QPushButton("Create automation +", card)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #18181B;
                border: none;
                border-radius: 13px;
                padding: 5px 12px;
                color: #FFFFFF;
                font-size: 10.5px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #27272A;
            }
        """)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self.command_submitted.emit("create new automation workflow"))
        text_col.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addLayout(text_col, stretch=1)

        # Micro App Workflow Graphic (Gmail, Chrome, YouTube, Notion sheet)
        wf_box = QFrame(card)
        wf_box.setStyleSheet("background: #FFFFFF; border: 1px solid #ECE7DC; border-radius: 12px; padding: 6px;")
        wf_box.setFixedSize(70, 70)
        wb_layout = QVBoxLayout(wf_box)
        wb_layout.setContentsMargins(4, 4, 4, 4)
        wb_layout.setSpacing(3)
        wb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        g_icon = QLabel(wf_box)
        g_icon.setPixmap(render_svg_pixmap(SVG_BRAND_GMAIL, 14, 14, color="#EA4335"))
        wb_layout.addWidget(g_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        lines = QLabel("—  —  —", wf_box)
        lines.setStyleSheet("color: #A1A1AA; font-size: 8px;")
        lines.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wb_layout.addWidget(lines)

        bolt = QLabel(wf_box)
        bolt.setPixmap(render_svg_pixmap(SVG_LIGHTNING, 14, 14, color="#18181B"))
        wb_layout.addWidget(bolt, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(wf_box)
        return card

    def _build_popular_automations(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        t = QLabel("Popular automations", container)
        t.setStyleSheet("color: #18181B; font-size: 13.5px; font-weight: 700;")
        hdr.addWidget(t)
        hdr.addStretch(1)
        see_all = QPushButton("See all →", container)
        see_all.setStyleSheet("background: transparent; border: none; color: #71717A; font-size: 11px;")
        hdr.addWidget(see_all)
        layout.addLayout(hdr)

        # 2x3 Grid
        col = QVBoxLayout()
        col.setSpacing(6)

        r1 = QHBoxLayout()
        r1.setSpacing(6)
        r1.addWidget(self._make_auto_card("Daily email summary", "Summarize important\nemails and show key points", SVG_MAIL, "summarize unread emails"))
        r1.addWidget(self._make_auto_card("Plan my day", "Check calendar and\nprepare a to-do list", SVG_CALENDAR, "prepare daily schedule"))
        col.addLayout(r1)

        r2 = QHBoxLayout()
        r2.setSpacing(6)
        r2.addWidget(self._make_auto_card("YouTube research", "Search, analyze and\nsummarize videos", SVG_BRAND_YOUTUBE, "search youtube and summarize"))
        r2.addWidget(self._make_auto_card("Create document", "Write, format and\nsave a document", SVG_FILE_TEXT, "create new summary document"))
        col.addLayout(r2)

        r3 = QHBoxLayout()
        r3.setSpacing(6)
        r3.addWidget(self._make_auto_card("Track trends", "Research latest news\non any topic", SVG_CHART_TRENDS, "track tech news trends"))
        r3.addWidget(self._make_auto_card("System tasks", "Manage files, settings\nand clean up your PC", SVG_SETTINGS, "clean up system files"))
        col.addLayout(r3)

        layout.addLayout(col)
        return container

    def _make_auto_card(self, title: str, desc: str, svg: str, cmd: str) -> QWidget:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E8E5DC;
                border-radius: 14px;
            }
            QFrame:hover {
                background-color: #FAF9F5;
                border-color: #D2CDC0;
            }
        """)
        c_layout = QHBoxLayout(card)
        c_layout.setContentsMargins(10, 8, 8, 8)
        c_layout.setSpacing(8)

        icon_lbl = QLabel(card)
        icon_lbl.setPixmap(render_svg_pixmap(svg, 18, 18, color="#18181B"))
        icon_lbl.setFixedSize(20, 20)
        c_layout.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(1)
        t_lbl = QLabel(title, card)
        t_lbl.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 700; border: none; background: transparent;")
        txt_col.addWidget(t_lbl)

        d_lbl = QLabel(desc, card)
        d_lbl.setStyleSheet("color: #71717A; font-size: 9px; line-height: 1.25; border: none; background: transparent;")
        txt_col.addWidget(d_lbl)
        c_layout.addLayout(txt_col, stretch=1)

        plus_btn = QPushButton(card)
        plus_btn.setIcon(render_svg_icon(SVG_PLUS, 12, color="#18181B"))
        plus_btn.setFixedSize(22, 22)
        plus_btn.setStyleSheet("QPushButton { background-color: #FAF9F5; border: 1px solid #E5E1D6; border-radius: 11px; } QPushButton:hover { background-color: #18181B; color: #FFFFFF; }")
        plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        plus_btn.clicked.connect(lambda: self.command_submitted.emit(cmd))
        c_layout.addWidget(plus_btn)

        return card

    def _build_templates_section(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        t = QLabel("Templates", container)
        t.setStyleSheet("color: #18181B; font-size: 13.5px; font-weight: 700;")
        hdr.addWidget(t)
        hdr.addStretch(1)
        see_all = QPushButton("See all →", container)
        see_all.setStyleSheet("background: transparent; border: none; color: #71717A; font-size: 11px;")
        hdr.addWidget(see_all)
        layout.addLayout(hdr)

        # Smooth horizontal scrollable container so template cards never get squished
        t_scroll = QScrollArea(container)
        t_scroll.setWidgetResizable(True)
        t_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        t_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        t_scroll.setFixedHeight(72)
        t_scroll.setStyleSheet("background: transparent; border: none;")

        t_content = QWidget()
        t_content.setStyleSheet("background: transparent;")
        row = QHBoxLayout(t_content)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        templates = [
            ("Study Helper", "Notes & summaries", SVG_GRADUATION_CAP, "open study helper"),
            ("Content Creator", "Ideas & scripts", SVG_VIDEO_CAMERA, "open content creator"),
            ("Office Work", "Emails & docs", SVG_BRIEFCASE, "open office work workflow"),
            ("Developer", "Code & automations", SVG_CODE_BRACKETS, "open developer workflow"),
            ("Personal", "Daily tasks & reminders", SVG_USER, "open personal tasks"),
        ]

        for name, sub, svg, cmd in templates:
            tile = QPushButton(t_content)
            tile.setFixedWidth(108)
            tile.setFixedHeight(68)
            tile.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    border: 1px solid #ECE7DC;
                    border-radius: 12px;
                    padding: 6px 6px;
                }
                QPushButton:hover {
                    background-color: #FAF9F5;
                    border-color: #D2CDC0;
                }
            """)
            tile.setCursor(Qt.CursorShape.PointingHandCursor)
            t_layout = QVBoxLayout(tile)
            t_layout.setContentsMargins(2, 4, 2, 4)
            t_layout.setSpacing(2)
            t_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            i_lbl = QLabel(tile)
            i_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            i_lbl.setPixmap(render_svg_pixmap(svg, 16, 16, color="#18181B"))
            i_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_layout.addWidget(i_lbl)

            n_lbl = QLabel(name, tile)
            n_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            n_lbl.setStyleSheet("color: #18181B; font-size: 10px; font-weight: 700; text-align: center; border: none; background: transparent;")
            n_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_layout.addWidget(n_lbl)

            s_lbl = QLabel(sub, tile)
            s_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            s_lbl.setStyleSheet("color: #71717A; font-size: 8.5px; text-align: center; border: none; background: transparent;")
            s_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_layout.addWidget(s_lbl)

            tile.clicked.connect(lambda checked=False, c=cmd: self.command_submitted.emit(c))
            row.addWidget(tile)

        row.addStretch(1)
        t_scroll.setWidget(t_content)
        layout.addWidget(t_scroll)
        return container

    def _build_recent_automations(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        t = QLabel("Recent automations", container)
        t.setStyleSheet("color: #18181B; font-size: 13.5px; font-weight: 700;")
        hdr.addWidget(t)
        hdr.addStretch(1)
        see_all = QPushButton("See all →", container)
        see_all.setStyleSheet("background: transparent; border: none; color: #71717A; font-size: 11px;")
        hdr.addWidget(see_all)
        layout.addLayout(hdr)

        # 3 Rows matching screenshot
        layout.addWidget(self._make_recent_auto_row("Daily email summary", "Runs every day at 9:00 AM", SVG_BRAND_GMAIL, has_toggle=True))
        layout.addWidget(self._make_recent_auto_row("Research latest tech news", "Last run 2 hours ago", SVG_BRAND_YOUTUBE, has_play=True, cmd="research latest tech news"))
        layout.addWidget(self._make_recent_auto_row("Organize Downloads folder", "Last run 1 day ago", SVG_FOLDER, has_play=True, cmd="organize downloads folder"))

        return container

    def _make_recent_auto_row(self, title: str, subtitle: str, svg: str, has_toggle: bool = False, has_play: bool = False, cmd: str = "") -> QWidget:
        row = QFrame()
        row.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #E8E5DC; border-radius: 12px; } QFrame:hover { background-color: #FAF9F5; }")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 7, 8, 7)
        layout.setSpacing(10)

        icon_lbl = QLabel(row)
        icon_lbl.setPixmap(render_svg_pixmap(svg, 18, 18, color="#18181B"))
        layout.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(1)
        t_lbl = QLabel(title, row)
        t_lbl.setStyleSheet("color: #18181B; font-size: 11.5px; font-weight: 600; border: none; background: transparent;")
        txt_col.addWidget(t_lbl)

        s_lbl = QLabel(subtitle, row)
        s_lbl.setStyleSheet("color: #71717A; font-size: 9.5px; border: none; background: transparent;")
        txt_col.addWidget(s_lbl)
        layout.addLayout(txt_col, stretch=1)

        if has_toggle:
            toggle = ModernMiniToggle(row, checked=True)
            layout.addWidget(toggle)

        if has_play:
            play_btn = QPushButton(row)
            play_btn.setIcon(render_svg_icon(SVG_PLAY_OUTLINE, 12, color="#18181B"))
            play_btn.setFixedSize(22, 22)
            play_btn.setStyleSheet("QPushButton { background-color: #FAF9F5; border: 1px solid #E6E2D6; border-radius: 11px; } QPushButton:hover { background-color: #18181B; color: #FFFFFF; }")
            play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            play_btn.clicked.connect(lambda: self.command_submitted.emit(cmd))
            layout.addWidget(play_btn)

        more_btn = QPushButton(row)
        more_btn.setIcon(render_svg_icon(SVG_MORE_HORIZONTAL, 14, color="#71717A"))
        more_btn.setFixedSize(22, 22)
        more_btn.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(more_btn)

        return row

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
        self.input_field.setPlaceholderText("Tell Handless what to automate...")
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
