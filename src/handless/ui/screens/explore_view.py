"""Explore Screen for Vyoma Handless.

Comprehensive Catalog & Launcher for:
- All (Curated showcase of top apps, tools, and automations)
- Apps (Direct 1-click Windows app launching)
- Productivity (Documents, spreadsheets, calendars, email, dictation)
- Content (YouTube, Screen Lens, OBS, OCR, media creation)
- System (Task manager, disk cleanup, settings, boss mode, diagnostics)
- Automation (Macro recording, meeting transcribing, workflows)
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from handless.ui.icons import (
    SVG_APPS_GRID,
    SVG_ARROW_UP,
    SVG_BRAND_CHROME,
    SVG_BRAND_DISCORD,
    SVG_BRAND_EDGE,
    SVG_BRAND_GMAIL,
    SVG_BRAND_NOTION,
    SVG_BRAND_SPOTIFY,
    SVG_BRAND_VSCODE,
    SVG_BRAND_WHATSAPP,
    SVG_BRAND_YOUTUBE,
    SVG_BRIEFCASE,
    SVG_CALENDAR,
    SVG_CAPTURE_SCREEN,
    SVG_CHART_TRENDS,
    SVG_CHECK_CIRCLE,
    SVG_CHEVRON_RIGHT,
    SVG_CODE_BRACKETS,
    SVG_FILE_TEXT,
    SVG_FOLDER,
    SVG_IMAGE,
    SVG_LIGHTNING,
    SVG_MAIL,
    SVG_MUSIC,
    SVG_PAPERCLIP,
    SVG_PLAY,
    SVG_PLUS,
    SVG_SEARCH,
    SVG_SETTINGS,
    SVG_SHIELD,
    SVG_STORAGE,
    SVG_TERMINAL,
    SVG_VIDEO_CAMERA,
    SVG_VOICE_WAVE,
    SVG_WINDOW,
    render_svg_icon,
    render_svg_pixmap,
)
from .illustrations import Hero3DIllustration

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Catalog for Explore Categories
# ---------------------------------------------------------------------------

CATALOG_DATA: Dict[str, List[Tuple[str, str, str, str, str]]] = {
    # (Title, Subtitle / Tag, SVG, Action Command, Badge)
    "Apps": [
        ("Google Chrome", "Browse, search & web apps", SVG_BRAND_CHROME, "open chrome", "Launch"),
        ("VS Code", "Code editor & extensions", SVG_BRAND_VSCODE, "open vscode", "Launch"),
        ("Notion", "Notes, docs & workspace", SVG_BRAND_NOTION, "open notion", "Launch"),
        ("Spotify", "Stream music & podcasts", SVG_BRAND_SPOTIFY, "open spotify", "Launch"),
        ("WhatsApp", "Messaging & voice calls", SVG_BRAND_WHATSAPP, "open whatsapp", "Launch"),
        ("Discord", "Communities & chat", SVG_BRAND_DISCORD, "open discord", "Launch"),
        ("Terminal", "PowerShell & Windows CLI", SVG_TERMINAL, "open terminal", "Launch"),
        ("File Explorer", "Files, folders & drives", SVG_FOLDER, "open downloads folder", "Launch"),
        ("Notepad", "Quick scratchpad & text", SVG_FILE_TEXT, "open notepad", "Launch"),
        ("Settings", "Windows system controls", SVG_SETTINGS, "open settings", "Launch"),
    ],
    "Productivity": [
        ("Create Document", "Draft docs, notes & reports", SVG_FILE_TEXT, "create new document", "Action"),
        ("Analyze Spreadsheet", "Inspect tables, numbers & CSV", SVG_CHART_TRENDS, "open excel", "Action"),
        ("Plan My Day", "Check calendar & prepare agenda", SVG_CALENDAR, "prepare daily schedule", "Workflow"),
        ("Summarize Emails", "Review unread inbox & actions", SVG_MAIL, "summarize unread emails", "Workflow"),
        ("Meeting Transcriber", "Record & live-transcribe calls", SVG_VIDEO_CAMERA, "open meeting transcriber", "Tool"),
        ("Wispr Dictation", "Talk to type in any active app", SVG_VOICE_WAVE, "toggle dictation", "Voice"),
        ("Focus Work Mode", "Silence distractions & center apps", SVG_SHIELD, "enable focus mode", "System"),
    ],
    "Content": [
        ("Search YouTube", "Find, play & summarize videos", SVG_BRAND_YOUTUBE, "open youtube", "Action"),
        ("Universal Screen Lens", "Instant visual query on screen", SVG_CAPTURE_SCREEN, "open screen lens", "Vision"),
        ("Analyze Screenshot", "OCR text & inspect visuals", SVG_IMAGE, "analyze current screenshot", "Vision"),
        ("Record Screen / OBS", "Capture desktop & gameplay", SVG_PLAY, "open obs", "Tool"),
        ("Social Post Writer", "Draft threads, tweets & posts", SVG_FILE_TEXT, "create social content", "AI"),
        ("Audio Extractor", "Transcribe audio from system", SVG_MUSIC, "extract audio notes", "Tool"),
    ],
    "System": [
        ("Task Manager", "Inspect CPU, RAM & processes", SVG_WINDOW, "open task manager", "System"),
        ("Disk Storage Cleanup", "Free up space & temp files", SVG_STORAGE, "open disk storage cleanup", "Utility"),
        ("Boss Mode / Privacy", "Instant hide & mute everything", SVG_SHIELD, "activate boss mode", "Safety"),
        ("PC Health & Power", "Optimize battery & performance", SVG_LIGHTNING, "optimize power settings", "Utility"),
        ("Network Diagnostics", "Ping, DNS & connection test", SVG_TERMINAL, "check network connection", "Diagnostics"),
        ("Handless Settings", "Hotkeys, models & voice rules", SVG_SETTINGS, "open settings", "Config"),
    ],
    "Automation": [
        ("Watch Me & Automate", "Record workflow & replicate", SVG_LIGHTNING, "start macro recording", "Macro"),
        ("Meeting Transcriber", "Speaker-labeled call summaries", SVG_VIDEO_CAMERA, "open meeting transcriber", "AI"),
        ("Daily Briefing", "Calendar, weather & priorities", SVG_CALENDAR, "generate daily briefing", "Daily"),
        ("Organize Downloads", "Sort messy downloads by filetype", SVG_FOLDER, "organize downloads folder", "Utility"),
        ("Dev Workspace Setup", "Open Chrome, VS Code & Terminal", SVG_CODE_BRACKETS, "setup dev workspace", "Macro"),
    ],
}


class PromoBannerCard(QWidget):
    """Hero Promo Card: 'One command. Everything handled.' with 3D metallic emblem."""
    explore_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("promoBannerCard")
        self.setStyleSheet("""
            QWidget#promoBannerCard {
                background-color: #F6F4ED;
                border: 1px solid #E6E1D4;
                border-radius: 18px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 8, 12)
        layout.setSpacing(10)

        # Left Text Column
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(4)

        tag = QLabel("GET MORE DONE", self)
        tag.setStyleSheet("color: #71717A; font-size: 9px; font-weight: 700; letter-spacing: 0.8px;")
        text_col.addWidget(tag)

        title = QLabel(
            '<div style="font-size: 17px; font-weight: 700; color: #18181B; line-height: 1.15; font-family: \'Playfair Display\', \'Georgia\', serif;">'
            'One command.<br>Everything <i>handled.</i>'
            '</div>',
            self,
        )
        title.setTextFormat(Qt.TextFormat.RichText)
        text_col.addWidget(title)

        sub = QLabel("Explore powerful tools, automations\nand ready-to-use actions.", self)
        sub.setStyleSheet("color: #71717A; font-size: 10px; line-height: 1.35;")
        text_col.addWidget(sub)

        # CTA Button
        btn = QPushButton("Explore all →", self)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #18181B;
                border: none;
                border-radius: 14px;
                padding: 5px 12px;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #27272A;
            }
        """)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.explore_clicked)
        text_col.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addLayout(text_col, stretch=1)

        # Right 3D Emblem
        emblem = Hero3DIllustration(self, width=95, height=90)
        layout.addWidget(emblem, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(QColor(246, 244, 237))
        painter.setPen(QPen(QColor(230, 225, 212), 1.2))
        painter.drawRoundedRect(rect, 18, 18)


class ExploreScreenView(QWidget):
    """Complete Explore Screen with dynamic category filtering and real action execution."""
    command_submitted = Signal(str)
    voice_toggled = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("exploreScreenView")
        self.active_category: str = "All"

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(14, 10, 14, 10)
        outer_layout.setSpacing(10)

        # Scroll Area for all sections
        self.scroll = QScrollArea(self)
        self.scroll.setObjectName("chatScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background-color: transparent; border: none;")
        if self.scroll.viewport():
            self.scroll.viewport().setStyleSheet("background-color: transparent;")

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: transparent;")
        self.main_layout = QVBoxLayout(self.content_widget)
        self.main_layout.setContentsMargins(0, 2, 0, 8)
        self.main_layout.setSpacing(14)

        # 1. Header (Explore + Subtitle + Search Bar)
        header_widget = self._build_header()
        self.main_layout.addWidget(header_widget)

        # 2. Promo Banner Card
        self.promo = PromoBannerCard()
        self.promo.explore_clicked.connect(lambda: self._set_category_by_name("All"))

        # 3. Category Filter Pills
        pills_row = self._build_filter_pills()
        self.main_layout.addWidget(pills_row)

        # 4. Category Stacked Widget (Official zero-flicker, zero-ghosting multi-page switcher)
        self.category_stack = QStackedWidget(self.content_widget)
        self.category_stack.setStyleSheet("background-color: transparent;")

        # Page 0: "All"
        self.page_all = QWidget()
        all_layout = QVBoxLayout(self.page_all)
        all_layout.setContentsMargins(0, 0, 0, 0)
        all_layout.setSpacing(14)
        all_layout.addWidget(self.promo)
        all_layout.addWidget(self._build_featured_section())
        all_layout.addWidget(self._build_popular_tools_section())
        all_layout.addWidget(self._build_automations_section())
        self.category_stack.addWidget(self.page_all)

        # Page 1: "Apps"
        self.page_apps = self._build_category_grid_view("Apps", CATALOG_DATA["Apps"])
        self.category_stack.addWidget(self.page_apps)

        # Page 2: "Productivity"
        self.page_productivity = self._build_category_grid_view("Productivity", CATALOG_DATA["Productivity"])
        self.category_stack.addWidget(self.page_productivity)

        # Page 3: "Content"
        self.page_content = self._build_category_grid_view("Content", CATALOG_DATA["Content"])
        self.category_stack.addWidget(self.page_content)

        # Page 4: "System"
        self.page_system = self._build_category_grid_view("System", CATALOG_DATA["System"])
        self.category_stack.addWidget(self.page_system)

        # Page 5: "Automation"
        self.page_automation = self._build_category_grid_view("Automation", CATALOG_DATA["Automation"])
        self.category_stack.addWidget(self.page_automation)

        # Page 6: "Search"
        self.page_search = QWidget()
        self.search_layout = QVBoxLayout(self.page_search)
        self.search_layout.setContentsMargins(0, 0, 0, 0)
        self.search_layout.setSpacing(8)
        self.category_stack.addWidget(self.page_search)

        self.main_layout.addWidget(self.category_stack)

        # Aliases for backwards compatibility
        self.dynamic_container = self.category_stack
        self.dynamic_layout = all_layout

        self.main_layout.addStretch(1)
        self.scroll.setWidget(self.content_widget)
        outer_layout.addWidget(self.scroll, stretch=1)

        # 5. Synchronized Bottom Prompt Bar
        bottom_bar = self._build_bottom_bar()
        outer_layout.addWidget(bottom_bar)

    def _build_header(self) -> QWidget:
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title = QLabel("Explore", header)
        title.setStyleSheet("color: #18181B; font-size: 22px; font-weight: 700; font-family: 'Playfair Display', 'Georgia', serif;")
        title_col.addWidget(title)

        sub = QLabel("Discover what Handless can do for you.", header)
        sub.setStyleSheet("color: #71717A; font-size: 11px;")
        title_col.addWidget(sub)
        h_layout.addLayout(title_col, stretch=1)

        # Mini Search Bar
        search_pill = QFrame(header)
        search_pill.setStyleSheet("QFrame { background-color: #FAF9F5; border: 1px solid #E5E1D6; border-radius: 14px; }")
        sp_layout = QHBoxLayout(search_pill)
        sp_layout.setContentsMargins(8, 2, 8, 2)
        sp_layout.setSpacing(6)

        lens = QLabel(search_pill)
        lens.setPixmap(render_svg_pixmap(SVG_SEARCH, 12, 12, color="#71717A"))
        sp_layout.addWidget(lens)

        self.explore_search = QLineEdit(search_pill)
        self.explore_search.setPlaceholderText("Search tools...")
        self.explore_search.setStyleSheet("border: none; background: transparent; color: #18181B; font-size: 10.5px;")
        self.explore_search.setFixedWidth(118)
        self.explore_search.textChanged.connect(self._handle_live_search)
        self.explore_search.returnPressed.connect(lambda: self._handle_search(self.explore_search.text()))
        sp_layout.addWidget(self.explore_search)
        h_layout.addWidget(search_pill)

        return header

    def _handle_live_search(self, query: str) -> None:
        q = query.strip().lower()
        if not q:
            self._render_category_content(self.active_category)
            return
        self._render_search_results(q)

    def _handle_search(self, query: str) -> None:
        if query:
            self.command_submitted.emit(query)

    def _build_filter_pills(self) -> QWidget:
        # Wrap pills in a container that fits neatly
        pills_container = QWidget()
        p_layout = QHBoxLayout(pills_container)
        p_layout.setContentsMargins(0, 0, 0, 0)
        p_layout.setSpacing(5)

        categories = [
            ("All", None, True),
            ("Apps", SVG_APPS_GRID, False),
            ("Productivity", SVG_CALENDAR, False),
            ("Content", SVG_IMAGE, False),
            ("System", SVG_SETTINGS, False),
            ("Automation", SVG_LIGHTNING, False),
        ]

        self.filter_buttons = []
        for name, svg, active in categories:
            btn = QPushButton(name, pills_container)
            btn.setProperty("category_name", name)
            if active:
                btn.setStyleSheet("QPushButton { background-color: #18181B; color: #FFFFFF; border-radius: 12px; padding: 4px 10px; font-size: 10.5px; font-weight: 600; border: none; }")
            else:
                btn.setStyleSheet("QPushButton { background-color: #FAF9F5; color: #52525B; border: 1px solid #E6E2D6; border-radius: 12px; padding: 4px 8px; font-size: 10.5px; font-weight: 500; } QPushButton:hover { background-color: #F0ECE1; color: #18181B; }")
            if svg:
                btn.setIcon(render_svg_icon(svg, 12, color="#FFFFFF" if active else "#52525B"))
                btn.setIconSize(QSize(12, 12))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, b=btn: self._set_active_filter(b))
            p_layout.addWidget(btn)
            self.filter_buttons.append(btn)

        p_layout.addStretch(1)
        return pills_container

    def _set_category_by_name(self, name: str) -> None:
        for btn in self.filter_buttons:
            if btn.property("category_name") == name or btn.text().strip() == name:
                self._set_active_filter(btn)
                break

    def _set_active_filter(self, selected_btn: QPushButton) -> None:
        cat_name = selected_btn.property("category_name") or selected_btn.text().strip()
        self.active_category = cat_name

        for btn in self.filter_buttons:
            is_active = (btn == selected_btn)
            svg = None
            for name, s, _ in [
                ("All", None, True),
                ("Apps", SVG_APPS_GRID, False),
                ("Productivity", SVG_CALENDAR, False),
                ("Content", SVG_IMAGE, False),
                ("System", SVG_SETTINGS, False),
                ("Automation", SVG_LIGHTNING, False),
            ]:
                if btn.property("category_name") == name:
                    svg = s
                    break

            if is_active:
                btn.setStyleSheet("QPushButton { background-color: #18181B; color: #FFFFFF; border-radius: 12px; padding: 4px 10px; font-size: 10.5px; font-weight: 600; border: none; }")
                if svg:
                    btn.setIcon(render_svg_icon(svg, 12, color="#FFFFFF"))
            else:
                btn.setStyleSheet("QPushButton { background-color: #FAF9F5; color: #52525B; border: 1px solid #E6E2D6; border-radius: 12px; padding: 4px 8px; font-size: 10.5px; font-weight: 500; } QPushButton:hover { background-color: #F0ECE1; color: #18181B; }")
                if svg:
                    btn.setIcon(render_svg_icon(svg, 12, color="#52525B"))

        # Switch content view dynamically
        self._render_category_content(cat_name)

    def _render_category_content(self, category: str) -> None:
        if category == "All":
            self.promo.show()
            self.category_stack.setCurrentWidget(self.page_all)
        else:
            self.promo.hide()
            if category == "Apps":
                self.category_stack.setCurrentWidget(self.page_apps)
            elif category == "Productivity":
                self.category_stack.setCurrentWidget(self.page_productivity)
            elif category == "Content":
                self.category_stack.setCurrentWidget(self.page_content)
            elif category == "System":
                self.category_stack.setCurrentWidget(self.page_system)
            elif category == "Automation":
                self.category_stack.setCurrentWidget(self.page_automation)

    def _render_search_results(self, query: str) -> None:
        while self.search_layout.count() > 0:
            item = self.search_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()

        matches: List[Tuple[str, str, str, str, str]] = []
        for cat, items in CATALOG_DATA.items():
            for title, desc, svg, cmd, badge in items:
                if query in title.lower() or query in desc.lower() or query in cmd.lower():
                    matches.append((title, f"[{cat}] {desc}", svg, cmd, badge))

        hdr = QLabel(f'Search results for "{query}" ({len(matches)} found)', self.page_search)
        hdr.setStyleSheet("color: #18181B; font-size: 13px; font-weight: 700;")
        self.search_layout.addWidget(hdr)

        if not matches:
            empty = QLabel("No tools or apps matching your search. Type Enter to ask AI.", self.page_search)
            empty.setStyleSheet("color: #71717A; font-size: 11px; padding: 12px; font-style: italic;")
            self.search_layout.addWidget(empty)
        else:
            grid = self._create_card_grid(matches)
            self.search_layout.addWidget(grid)

        self.category_stack.setCurrentWidget(self.page_search)

    def _build_category_grid_view(self, category_name: str, items: List[Tuple[str, str, str, str, str]]) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Header with item count
        hdr = QHBoxLayout()
        title_lbl = QLabel(f"{category_name} ({len(items)})", container)
        title_lbl.setStyleSheet("color: #18181B; font-size: 14px; font-weight: 700;")
        hdr.addWidget(title_lbl)
        hdr.addStretch(1)

        back_btn = QPushButton("← Back to All", container)
        back_btn.setStyleSheet("color: #71717A; font-size: 11px; background: transparent; border: none;")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(lambda: self._set_category_by_name("All"))
        hdr.addWidget(back_btn)
        layout.addLayout(hdr)

        # 2-column Grid of Cards
        grid = self._create_card_grid(items)
        layout.addWidget(grid)

        return container

    def _create_card_grid(self, items: List[Tuple[str, str, str, str, str]]) -> QWidget:
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)

        # Single column: title + badge + description need the full sidebar width
        for idx, (title, desc, svg, cmd, badge) in enumerate(items):
            row = idx
            col = 0
            card = self._make_catalog_card(title, desc, svg, cmd, badge)
            grid.addWidget(card, row, col)

        return grid_widget

    def _make_catalog_card(self, title: str, desc: str, svg: str, cmd: str, badge: str) -> QWidget:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #ECE7DC;
                border-radius: 14px;
            }
            QFrame:hover {
                background-color: #FAF9F5;
                border-color: #D2CDC0;
            }
        """)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        c_layout = QHBoxLayout(card)
        c_layout.setContentsMargins(10, 8, 8, 8)
        c_layout.setSpacing(8)

        # Icon
        icon_lbl = QLabel(card)
        icon_lbl.setPixmap(render_svg_pixmap(svg, 20, 20, color="#18181B"))
        icon_lbl.setFixedSize(24, 24)
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        c_layout.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Details
        txt_col = QVBoxLayout()
        txt_col.setContentsMargins(0, 0, 0, 0)
        txt_col.setSpacing(2)

        t_row = QHBoxLayout()
        t_row.setSpacing(4)
        t_lbl = QLabel(title, card)
        t_lbl.setStyleSheet("color: #18181B; font-size: 11.5px; font-weight: 700; border: none; background: transparent;")
        t_row.addWidget(t_lbl)
        t_row.addStretch(1)

        badge_lbl = QLabel(badge, card)
        badge_lbl.setStyleSheet("color: #71717A; background-color: #F4F3EE; font-size: 8.5px; font-weight: 600; border-radius: 4px; padding: 1px 4px;")
        t_row.addWidget(badge_lbl)
        txt_col.addLayout(t_row)

        d_lbl = QLabel(desc, card)
        d_lbl.setStyleSheet("color: #71717A; font-size: 9px; line-height: 1.25; border: none; background: transparent;")
        d_lbl.setWordWrap(True)
        txt_col.addWidget(d_lbl)
        c_layout.addLayout(txt_col, stretch=1)

        card.mousePressEvent = lambda e, c=cmd: self.command_submitted.emit(c)
        return card

    def _build_featured_section(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        t = QLabel("Featured", container)
        t.setStyleSheet("color: #18181B; font-size: 13.5px; font-weight: 700;")
        hdr.addWidget(t)
        hdr.addStretch(1)
        see_all = QPushButton("See all →", container)
        see_all.setStyleSheet("background: transparent; border: none; color: #71717A; font-size: 11px;")
        see_all.setCursor(Qt.CursorShape.PointingHandCursor)
        see_all.clicked.connect(lambda: self._set_category_by_name("Apps"))
        hdr.addWidget(see_all)
        layout.addLayout(hdr)

        # 2x2 Grid
        grid_col = QVBoxLayout()
        grid_col.setSpacing(6)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.addWidget(self._make_featured_card("Open Chrome", "Browse, search, and\nsummarize any page", SVG_BRAND_CHROME, "open chrome"))
        row1.addWidget(self._make_featured_card("Open YouTube", "Search, play, and\nmanage videos", SVG_BRAND_YOUTUBE, "open youtube"))
        grid_col.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row2.addWidget(self._make_featured_card("Capture Screen", "Take screenshots and\nanalyze content", SVG_CAPTURE_SCREEN, "take a screenshot"))
        row2.addWidget(self._make_featured_card("Summarize", "Summarize text, articles\nand documents", SVG_FILE_TEXT, "summarize active window"))
        grid_col.addLayout(row2)

        layout.addLayout(grid_col)
        return container

    def _make_featured_card(self, title: str, desc: str, svg: str, cmd: str) -> QWidget:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #ECE7DC;
                border-radius: 14px;
            }
            QFrame:hover {
                background-color: #FAF9F5;
                border-color: #D2CDC0;
            }
        """)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        c_layout = QHBoxLayout(card)
        c_layout.setContentsMargins(10, 8, 8, 8)
        c_layout.setSpacing(8)

        icon_lbl = QLabel(card)
        icon_lbl.setPixmap(render_svg_pixmap(svg, 20, 20, color="#18181B"))
        icon_lbl.setFixedSize(22, 22)
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        c_layout.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(1)
        t_lbl = QLabel(title, card)
        t_lbl.setStyleSheet("color: #18181B; font-size: 11.5px; font-weight: 700; border: none; background: transparent;")
        txt_col.addWidget(t_lbl)

        d_lbl = QLabel(desc, card)
        d_lbl.setStyleSheet("color: #71717A; font-size: 9.5px; line-height: 1.25; border: none; background: transparent;")
        txt_col.addWidget(d_lbl)
        c_layout.addLayout(txt_col, stretch=1)

        chev = QLabel(card)
        chev.setPixmap(render_svg_pixmap(SVG_CHEVRON_RIGHT, 12, 12, color="#A1A1AA"))
        chev.setStyleSheet("border: none; background: transparent;")
        c_layout.addWidget(chev)

        card.mousePressEvent = lambda e, c=cmd: self.command_submitted.emit(c)
        return card

    def _build_popular_tools_section(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        t = QLabel("Popular tools", container)
        t.setStyleSheet("color: #18181B; font-size: 13.5px; font-weight: 700;")
        hdr.addWidget(t)
        hdr.addStretch(1)
        see_all = QPushButton("See all →", container)
        see_all.setStyleSheet("background: transparent; border: none; color: #71717A; font-size: 11px;")
        see_all.setCursor(Qt.CursorShape.PointingHandCursor)
        see_all.clicked.connect(lambda: self._set_category_by_name("Productivity"))
        hdr.addWidget(see_all)
        layout.addLayout(hdr)

        # 6 tiles in a 3x2 grid so labels never clip at sidebar width
        row = QGridLayout()
        row.setSpacing(5)

        tools = [
            ("Transcribe call", SVG_VIDEO_CAMERA, "open meeting transcriber"),
            ("Open any app", SVG_APPS_GRID, "launch application"),
            ("Find files", SVG_FOLDER, "open downloads folder"),
            ("Create document", SVG_FILE_TEXT, "create new document"),
            ("Analyze image", SVG_IMAGE, "analyze current screenshot"),
            ("Manage tabs", SVG_WINDOW, "switch to next tab"),
        ]

        for name, svg, cmd in tools:
            tile = QPushButton(container)
            tile.setMinimumHeight(58)
            tile.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    border: 1px solid #ECE7DC;
                    border-radius: 11px;
                    padding: 8px 3px;
                }
                QPushButton:hover {
                    background-color: #FAF9F5;
                    border-color: #D2CDC0;
                }
            """)
            tile.setCursor(Qt.CursorShape.PointingHandCursor)
            t_layout = QVBoxLayout(tile)
            t_layout.setContentsMargins(2, 4, 2, 4)
            t_layout.setSpacing(4)
            t_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            i_lbl = QLabel(tile)
            i_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            i_lbl.setPixmap(render_svg_pixmap(svg, 16, 16, color="#18181B"))
            i_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_layout.addWidget(i_lbl)

            n_lbl = QLabel(name, tile)
            n_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            n_lbl.setStyleSheet("color: #18181B; font-size: 9.5px; font-weight: 600; text-align: center; border: none; background: transparent;")
            n_lbl.setWordWrap(True)
            n_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_layout.addWidget(n_lbl)

            tile.clicked.connect(lambda checked=False, c=cmd: self.command_submitted.emit(c))
            idx = row.count()
            row.addWidget(tile, idx // 3, idx % 3)

        layout.addLayout(row)
        return container

    def _build_automations_section(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        t = QLabel("Automations", container)
        t.setStyleSheet("color: #18181B; font-size: 13.5px; font-weight: 700;")
        hdr.addWidget(t)
        hdr.addStretch(1)
        see_all = QPushButton("See all →", container)
        see_all.setStyleSheet("background: transparent; border: none; color: #71717A; font-size: 11px;")
        see_all.setCursor(Qt.CursorShape.PointingHandCursor)
        see_all.clicked.connect(lambda: self._set_category_by_name("Automation"))
        hdr.addWidget(see_all)
        layout.addLayout(hdr)

        # 2x2 Grid with + buttons
        col = QVBoxLayout()
        col.setSpacing(6)

        r1 = QHBoxLayout()
        r1.setSpacing(6)
        r1.addWidget(self._make_auto_card("Plan my day", "Organize tasks, open apps\nand set reminders", SVG_CALENDAR, "prepare daily schedule"))
        r1.addWidget(self._make_auto_card("Research anything", "Search, read and give\nkey insights", SVG_SEARCH, "research latest topics"))
        col.addLayout(r1)

        r2 = QHBoxLayout()
        r2.setSpacing(6)
        r2.addWidget(self._make_auto_card("Create content", "Write, design and\npublish faster", SVG_PLAY, "open content tools"))
        r2.addWidget(self._make_auto_card("System tasks", "Manage settings, files\nand optimize PC", SVG_SETTINGS, "open disk storage cleanup"))
        col.addLayout(r2)

        layout.addLayout(col)
        return container

    def _make_auto_card(self, title: str, desc: str, svg: str, cmd: str) -> QWidget:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #ECE7DC;
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
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        c_layout.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(1)
        t_lbl = QLabel(title, card)
        t_lbl.setStyleSheet("color: #18181B; font-size: 11.5px; font-weight: 700; border: none; background: transparent;")
        txt_col.addWidget(t_lbl)

        d_lbl = QLabel(desc, card)
        d_lbl.setStyleSheet("color: #71717A; font-size: 9.5px; line-height: 1.25; border: none; background: transparent;")
        txt_col.addWidget(d_lbl)
        c_layout.addLayout(txt_col, stretch=1)

        plus_btn = QPushButton(card)
        plus_btn.setIcon(render_svg_icon(SVG_PLUS, 12, color="#18181B"))
        plus_btn.setFixedSize(22, 22)
        plus_btn.setStyleSheet("QPushButton { background-color: #FAF9F5; border: 1px solid #E5E1D6; border-radius: 11px; } QPushButton:hover { background-color: #18181B; color: #FFFFFF; }")
        plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        plus_btn.clicked.connect(lambda: self.command_submitted.emit(cmd))
        c_layout.addWidget(plus_btn)

        card.mousePressEvent = lambda e, c=cmd: self.command_submitted.emit(c)
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
