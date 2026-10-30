"""Chat Screen for Vyoma Handless.

Features:
- Header: "Chat" with "[+] New chat", "🕶️ Incognito" toggle, "🕘 History" drawer toggle, and "···" menu.
- Grok Roast Persona chat stream with emoji-rich dialogue and savage wit.
- History Drawer: slide-out / toggleable panel listing past chat sessions with 1-click restore.
- Incognito Mode: ephemeral chatting that is never saved to disk with visible status banner.
- In-Chat Handless Self-Configuration Card:
    * Diff preview: Current Value -> Proposed Value
    * 1-Click "Allow & Apply" button that reconfigures Handless live.
- MultiStepPlanCard for desktop execution status.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from handless.intelligence.grok_persona import ConfigProposal
from handless.ui.icons import (
    SVG_ARROW_UP,
    SVG_BRAND_CHROME,
    SVG_CHECK,
    SVG_CHECK_CIRCLE,
    SVG_CLOCK,
    SVG_CLOSE,
    SVG_DOT_PENDING,
    SVG_DOT_RING,
    SVG_HANDLESS_MARK,
    SVG_INCOGNITO,
    SVG_LIGHTNING,
    SVG_MORE_HORIZONTAL,
    SVG_PAPERCLIP,
    SVG_PLUS,
    SVG_REFRESH,
    SVG_SETTINGS,
    SVG_USER,
    SVG_VOICE_WAVE,
    render_svg_icon,
    render_svg_pixmap,
)

logger = logging.getLogger(__name__)

CHAT_SESSIONS_FILE = Path.home() / ".vyoma-handless" / "chat_sessions.json"


# ---------------------------------------------------------------------------
# Multi-Step Plan Card
# ---------------------------------------------------------------------------

class MultiStepPlanCard(QWidget):
    """Live interactive multi-step execution plan card with stepper & progress tracker."""
    view_activity_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("multiStepPlanCard")
        self.setStyleSheet("""
            QWidget#multiStepPlanCard {
                background-color: #FFFFFF;
                border: 1px solid #ECE7DC;
                border-radius: 18px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # 1. Stepper Row (Step 1 -> Line -> Step 2 -> Line -> Step 3)
        stepper_row = QHBoxLayout()
        stepper_row.setContentsMargins(0, 0, 0, 0)
        stepper_row.setSpacing(6)

        # Step 1: Completed
        col1 = QVBoxLayout()
        col1.setSpacing(3)
        col1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot1 = QLabel(self)
        dot1.setPixmap(render_svg_pixmap(SVG_CHECK_CIRCLE, 18, 18, color="#10B981"))
        dot1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col1.addWidget(dot1)

        t1 = QLabel("Opening Chrome", self)
        t1.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 600;")
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col1.addWidget(t1)

        s1 = QLabel("Completed", self)
        s1.setStyleSheet("color: #71717A; font-size: 9.5px;")
        s1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col1.addWidget(s1)
        stepper_row.addLayout(col1)

        # Connecting solid line
        line1 = QFrame(self)
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("color: #18181B; background-color: #18181B; min-height: 2px; max-height: 2px;")
        stepper_row.addWidget(line1, stretch=1)

        # Step 2: In Progress
        col2 = QVBoxLayout()
        col2.setSpacing(3)
        col2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot2 = QLabel(self)
        dot2.setPixmap(render_svg_pixmap(SVG_DOT_RING, 18, 18, color="#18181B"))
        dot2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col2.addWidget(dot2)

        t2 = QLabel("Searching the web", self)
        t2.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 600;")
        t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col2.addWidget(t2)

        s2 = QLabel("In progress", self)
        s2.setStyleSheet("color: #71717A; font-size: 9.5px;")
        s2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col2.addWidget(s2)
        stepper_row.addLayout(col2)

        # Connecting dotted line
        line2 = QFrame(self)
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("color: #D4D4D8; background-color: #D4D4D8; min-height: 1.5px; max-height: 1.5px;")
        stepper_row.addWidget(line2, stretch=1)

        # Step 3: Pending
        col3 = QVBoxLayout()
        col3.setSpacing(3)
        col3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot3 = QLabel(self)
        dot3.setPixmap(render_svg_pixmap(SVG_DOT_PENDING, 18, 18, color="#A1A1AA"))
        dot3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col3.addWidget(dot3)

        t3 = QLabel("Summarizing results", self)
        t3.setStyleSheet("color: #71717A; font-size: 11px; font-weight: 600;")
        t3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col3.addWidget(t3)

        s3 = QLabel("Pending", self)
        s3.setStyleSheet("color: #A1A1AA; font-size: 9.5px;")
        s3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col3.addWidget(s3)
        stepper_row.addLayout(col3)

        layout.addLayout(stepper_row)

        # 2. Sub-Task Card
        task_card = QFrame(self)
        task_card.setStyleSheet("QFrame { background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 12px; }")
        tc_layout = QHBoxLayout(task_card)
        tc_layout.setContentsMargins(12, 10, 12, 10)
        tc_layout.setSpacing(10)

        icon_lbl = QLabel(task_card)
        icon_lbl.setPixmap(render_svg_pixmap(SVG_BRAND_CHROME, 22, 22, color="#18181B"))
        icon_lbl.setFixedSize(24, 24)
        tc_layout.addWidget(icon_lbl)

        det_col = QVBoxLayout()
        det_col.setContentsMargins(0, 0, 0, 0)
        det_col.setSpacing(2)

        tc_title = QLabel("Browser task", task_card)
        tc_title.setStyleSheet("color: #18181B; font-size: 12px; font-weight: 700; border: none; background: transparent;")
        det_col.addWidget(tc_title)

        tc_sub = QLabel("Opening Chrome and searching for latest design trends...", task_card)
        tc_sub.setStyleSheet("color: #71717A; font-size: 10.5px; border: none; background: transparent;")
        tc_sub.setWordWrap(True)
        det_col.addWidget(tc_sub)
        tc_layout.addLayout(det_col, stretch=1)

        spin_col = QVBoxLayout()
        spin_col.setSpacing(2)
        spin_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        spin_ring = QLabel("◌", task_card)
        spin_ring.setStyleSheet("color: #71717A; font-size: 14px; font-weight: bold; border: none; background: transparent;")
        spin_ring.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin_col.addWidget(spin_ring)

        spin_txt = QLabel("In progress", task_card)
        spin_txt.setStyleSheet("color: #71717A; font-size: 9.5px; border: none; background: transparent;")
        spin_col.addWidget(spin_txt)
        tc_layout.addLayout(spin_col)

        layout.addWidget(task_card)

        link_btn = QPushButton("View activity →", self)
        link_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #18181B;
                font-size: 11.5px;
                font-weight: 600;
                text-align: left;
                padding: 2px 0px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        link_btn.clicked.connect(self.view_activity_clicked)
        layout.addWidget(link_btn)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(234, 230, 222), 1.2))
        painter.drawRoundedRect(rect, 18, 18)


# ---------------------------------------------------------------------------
# Interactive "Preview & Allow" Configuration Proposal Card
# ---------------------------------------------------------------------------

class HandlessConfigActionCard(QWidget):
    """In-Chat 1-Click Allow/Apply card for live Handless self-reconfiguration."""
    allow_clicked = Signal(str, str)  # (setting_key, proposed_value)
    dismiss_clicked = Signal()

    def __init__(self, proposal: ConfigProposal, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.proposal = proposal
        self.setObjectName("configActionCard")
        self.setStyleSheet("""
            QWidget#configActionCard {
                background-color: #FAF9F5;
                border: 1.5px solid #E6E1D4;
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Header: Icon + Title + Category Tag
        hdr = QHBoxLayout()
        hdr.setSpacing(6)

        icon_lbl = QLabel(self)
        icon_lbl.setPixmap(render_svg_pixmap(SVG_SETTINGS, 16, 16, color="#18181B"))
        hdr.addWidget(icon_lbl)

        title = QLabel(f"Configure Handless: {proposal.setting_label}", self)
        title.setStyleSheet("color: #18181B; font-size: 12px; font-weight: 700; border: none; background: transparent;")
        hdr.addWidget(title)

        hdr.addStretch(1)

        cat_badge = QLabel("Self-Config", self)
        cat_badge.setStyleSheet("color: #047857; background-color: #D1FAE5; font-size: 9px; font-weight: 700; border-radius: 6px; padding: 2px 6px;")
        hdr.addWidget(cat_badge)
        layout.addLayout(hdr)

        # Roast & Summary Note
        note = QLabel(f"<i>{proposal.roast_comment}</i>", self)
        note.setStyleSheet("color: #52525B; font-size: 11px; line-height: 1.35; border: none; background: transparent;")
        note.setWordWrap(True)
        layout.addWidget(note)

        # Diff Preview Box
        diff_box = QFrame(self)
        diff_box.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #ECE7DC; border-radius: 10px; }")
        db_layout = QHBoxLayout(diff_box)
        db_layout.setContentsMargins(10, 8, 10, 8)
        db_layout.setSpacing(8)

        # Current Value
        curr_col = QVBoxLayout()
        curr_col.setSpacing(1)
        curr_tag = QLabel("CURRENT", diff_box)
        curr_tag.setStyleSheet("color: #71717A; font-size: 8.5px; font-weight: 700;")
        curr_col.addWidget(curr_tag)

        curr_val = QLabel(proposal.current_value, diff_box)
        curr_val.setStyleSheet("color: #71717A; font-size: 11px; font-weight: 600; text-decoration: line-through;")
        curr_col.addWidget(curr_val)
        db_layout.addLayout(curr_col)

        # Arrow
        arrow = QLabel("→", diff_box)
        arrow.setStyleSheet("color: #18181B; font-size: 14px; font-weight: 700;")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        db_layout.addWidget(arrow)

        # Proposed Value
        prop_col = QVBoxLayout()
        prop_col.setSpacing(1)
        prop_tag = QLabel("PROPOSED", diff_box)
        prop_tag.setStyleSheet("color: #047857; font-size: 8.5px; font-weight: 700;")
        prop_col.addWidget(prop_tag)

        prop_val = QLabel(proposal.proposed_value, diff_box)
        prop_val.setStyleSheet("color: #047857; font-size: 12px; font-weight: 800;")
        prop_col.addWidget(prop_val)
        db_layout.addLayout(prop_col)

        layout.addWidget(diff_box)

        # Buttons Row: Allow & Apply vs Dismiss
        self.btn_row = QWidget(self)
        br_layout = QHBoxLayout(self.btn_row)
        br_layout.setContentsMargins(0, 0, 0, 0)
        br_layout.setSpacing(8)

        self.allow_btn = QPushButton("Allow & Apply ✓", self.btn_row)
        self.allow_btn.setStyleSheet("""
            QPushButton {
                background-color: #18181B;
                color: #FFFFFF;
                border-radius: 10px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 700;
                border: none;
            }
            QPushButton:hover {
                background-color: #27272A;
            }
        """)
        self.allow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.allow_btn.clicked.connect(self._on_allow_clicked)
        br_layout.addWidget(self.allow_btn)

        self.dismiss_btn = QPushButton("Dismiss", self.btn_row)
        self.dismiss_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #71717A;
                border: 1px solid #ECE7DC;
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #F4F3EE;
                color: #18181B;
            }
        """)
        self.dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dismiss_btn.clicked.connect(self._on_dismiss_clicked)
        br_layout.addWidget(self.dismiss_btn)

        br_layout.addStretch(1)
        layout.addWidget(self.btn_row)

        # Status Label (Hidden initially)
        self.applied_lbl = QLabel(self)
        self.applied_lbl.setVisible(False)
        self.applied_lbl.setStyleSheet("color: #047857; font-size: 11px; font-weight: 700; border: none; background: transparent;")
        layout.addWidget(self.applied_lbl)

    def _on_allow_clicked(self) -> None:
        self.btn_row.setVisible(False)
        self.applied_lbl.setText(f"✓ Setting applied successfully: {self.proposal.proposed_value}")
        self.applied_lbl.setVisible(True)
        self.allow_clicked.emit(self.proposal.setting_key, self.proposal.proposed_value)

    def _on_dismiss_clicked(self) -> None:
        self.btn_row.setVisible(False)
        self.applied_lbl.setText("Proposal dismissed.")
        self.applied_lbl.setStyleSheet("color: #71717A; font-size: 11px; font-style: italic; border: none;")
        self.applied_lbl.setVisible(True)
        self.dismiss_clicked.emit()


# ---------------------------------------------------------------------------
# Chat History Drawer Widget
# ---------------------------------------------------------------------------

class ChatHistoryDrawer(QFrame):
    """Slide-out / toggleable drawer listing previous chat conversations."""
    session_selected = Signal(str)  # session_id
    new_chat_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("chatHistoryDrawer")
        self.setStyleSheet("""
            QFrame#chatHistoryDrawer {
                background-color: #FAF9F5;
                border-right: 1px solid #ECE7DC;
            }
        """)
        self.setFixedWidth(210)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header
        hdr = QHBoxLayout()
        t = QLabel("Chat History", self)
        t.setStyleSheet("color: #18181B; font-size: 12px; font-weight: 700; border: none;")
        hdr.addWidget(t)
        hdr.addStretch(1)

        new_btn = QPushButton("+ New", self)
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #18181B;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #27272A;
            }
        """)
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.clicked.connect(self.new_chat_clicked)
        hdr.addWidget(new_btn)
        layout.addLayout(hdr)

        # Scroll area for chat items
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(4)
        self.list_layout.addStretch(1)

        scroll.setWidget(self.list_container)
        layout.addWidget(scroll, stretch=1)

    def load_sessions(self, sessions: List[Dict[str, Any]], active_id: str) -> None:
        # Clear list
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for s in sessions:
            sid = s.get("id", "")
            title = s.get("title", "Untitled Chat")
            time_str = s.get("time_str", "")

            btn = QPushButton(self.list_container)
            is_active = (sid == active_id)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'#EDEAE1' if is_active else 'transparent'};
                    border: 1px solid {'#D4D0C5' if is_active else 'transparent'};
                    border-radius: 8px;
                    padding: 6px 8px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: #F0ECE1;
                }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            b_layout = QVBoxLayout(btn)
            b_layout.setContentsMargins(0, 0, 0, 0)
            b_layout.setSpacing(1)

            t_lbl = QLabel(title[:26] + ("..." if len(title) > 26 else ""), btn)
            t_lbl.setStyleSheet(f"color: #18181B; font-size: 11px; font-weight: {'700' if is_active else '500'}; border: none;")
            b_layout.addWidget(t_lbl)

            if time_str:
                d_lbl = QLabel(time_str, btn)
                d_lbl.setStyleSheet("color: #71717A; font-size: 9px; border: none;")
                b_layout.addWidget(d_lbl)

            btn.clicked.connect(lambda checked=False, target_id=sid: self.session_selected.emit(target_id))
            self.list_layout.insertWidget(self.list_layout.count() - 1, btn)


# ---------------------------------------------------------------------------
# Main Chat Screen View
# ---------------------------------------------------------------------------

class ChatScreenView(QWidget):
    """Complete Conversational Chat View for Vyoma Handless."""
    command_submitted = Signal(str)
    voice_toggled = Signal()
    new_chat_requested = Signal()
    config_change_applied = Signal(str, str)  # (setting_key, proposed_value)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("chatScreenView")
        self.incognito_mode: bool = False
        self.current_session_id: str = str(uuid.uuid4())
        self.sessions_cache: List[Dict[str, Any]] = self._load_sessions_from_disk()

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(14, 10, 14, 10)
        outer_layout.setSpacing(10)

        # 1. Header Bar: "Chat", "[+] New chat", "🕶️ Incognito", "🕘 History", "···"
        header = QHBoxLayout()
        header.setContentsMargins(2, 2, 2, 4)
        header.setSpacing(6)

        title = QLabel("Chat", self)
        title.setStyleSheet("color: #18181B; font-size: 18px; font-weight: 800; font-family: 'Playfair Display', 'Georgia', serif;")
        header.addWidget(title)

        header.addStretch(1)

        # Incognito Toggle Button
        self.incognito_btn = QPushButton("🕶️ Incognito", self)
        self.incognito_btn.setStyleSheet("""
            QPushButton {
                background-color: #FAF9F5;
                border: 1px solid #ECE7DC;
                border-radius: 12px;
                padding: 4px 8px;
                color: #52525B;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #F0ECE1;
                color: #18181B;
            }
        """)
        self.incognito_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.incognito_btn.clicked.connect(self._toggle_incognito)
        header.addWidget(self.incognito_btn)

        # History Drawer Toggle Button
        self.history_drawer_btn = QPushButton("🕘 History", self)
        self.history_drawer_btn.setStyleSheet("""
            QPushButton {
                background-color: #FAF9F5;
                border: 1px solid #ECE7DC;
                border-radius: 12px;
                padding: 4px 8px;
                color: #52525B;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #F0ECE1;
                color: #18181B;
            }
        """)
        self.history_drawer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_drawer_btn.clicked.connect(self._toggle_history_drawer)
        header.addWidget(self.history_drawer_btn)

        # New Chat Button
        new_btn = QPushButton("[+] New chat", self)
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #FAF9F5;
                border: 1px solid #E5E1D6;
                border-radius: 12px;
                padding: 4px 10px;
                color: #18181B;
                font-size: 11.5px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #F0ECE1;
                border-color: #D2CDC0;
            }
        """)
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.clicked.connect(self._handle_new_chat)
        header.addWidget(new_btn)

        # Menu Button
        menu_btn = QPushButton(self)
        menu_btn.setIcon(render_svg_icon(SVG_MORE_HORIZONTAL, 16, color="#52525B", hover_color="#18181B"))
        menu_btn.setIconSize(QSize(16, 16))
        menu_btn.setFixedSize(28, 28)
        menu_btn.setStyleSheet("background: transparent; border: none; border-radius: 6px;")
        menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        menu_btn.clicked.connect(self._open_chat_menu)
        header.addWidget(menu_btn)

        outer_layout.addLayout(header)

        # Incognito Warning Banner (Hidden by default)
        self.incognito_banner = QFrame(self)
        self.incognito_banner.setVisible(False)
        self.incognito_banner.setStyleSheet("QFrame { background-color: #18181B; border-radius: 8px; }")
        ib_layout = QHBoxLayout(self.incognito_banner)
        ib_layout.setContentsMargins(10, 5, 10, 5)
        ib_lbl = QLabel("🕶️ Incognito Active — Chats are ephemeral & never saved to disk", self.incognito_banner)
        ib_lbl.setStyleSheet("color: #FFFFFF; font-size: 10px; font-weight: 600;")
        ib_layout.addWidget(ib_lbl)
        outer_layout.addWidget(self.incognito_banner)

        # 2. Main Content Split / Container (Chat on right, History Drawer on left)
        self.center_container = QWidget(self)
        cc_layout = QHBoxLayout(self.center_container)
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.setSpacing(0)

        # History Drawer (Hidden initially)
        self.history_drawer = ChatHistoryDrawer(self.center_container)
        self.history_drawer.setVisible(False)
        self.history_drawer.session_selected.connect(self._load_session_by_id)
        self.history_drawer.new_chat_clicked.connect(self._handle_new_chat)
        cc_layout.addWidget(self.history_drawer)

        # Chat Stream Scroll Area
        self.scroll_area = QScrollArea(self.center_container)
        self.scroll_area.setObjectName("chatScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background-color: transparent; border: none;")
        if self.scroll_area.viewport():
            self.scroll_area.viewport().setStyleSheet("background-color: transparent;")

        self.chat_content = QWidget()
        self.chat_content.setStyleSheet("background-color: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(4, 6, 4, 6)
        self.chat_layout.setSpacing(12)

        # Center Intro Greeting
        self.intro_box = self._build_intro_box()
        self.chat_layout.addWidget(self.intro_box)
        self.chat_layout.addStretch(1)

        # Default Example Messages
        self._add_example_flow()

        self.scroll_area.setWidget(self.chat_content)
        cc_layout.addWidget(self.scroll_area, stretch=1)
        outer_layout.addWidget(self.center_container, stretch=1)

        # 3. Synchronized Bottom Prompt Input Bar
        input_container = QWidget(self)
        input_container.setObjectName("promptContainerCard")
        input_container.setStyleSheet("""
            QWidget#promptContainerCard {
                background-color: #F5F4EE;
                border: 1px solid #E7E4DA;
                border-radius: 18px;
                padding: 6px;
            }
        """)
        ic_layout = QHBoxLayout(input_container)
        ic_layout.setContentsMargins(8, 4, 6, 4)
        ic_layout.setSpacing(8)

        # Sound wave button
        wave_btn = QPushButton(input_container)
        wave_btn.setIcon(render_svg_icon(SVG_VOICE_WAVE, 16, color="#71717A", hover_color="#18181B"))
        wave_btn.setIconSize(QSize(16, 16))
        wave_btn.setFixedSize(24, 24)
        wave_btn.setStyleSheet("background: transparent; border: none;")
        wave_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        wave_btn.clicked.connect(self.voice_toggled)
        ic_layout.addWidget(wave_btn)

        # Divider
        sep = QWidget(input_container)
        sep.setFixedSize(1, 16)
        sep.setStyleSheet("background-color: #E2DFD6;")
        ic_layout.addWidget(sep)

        # Input field
        self.input_field = QLineEdit(input_container)
        self.input_field.setPlaceholderText("Tell Handless what to do...")
        self.input_field.setStyleSheet("background: transparent; border: none; color: #18181B; font-size: 12.5px;")
        self.input_field.returnPressed.connect(self._handle_enter)
        ic_layout.addWidget(self.input_field, stretch=1)

        # Paperclip
        attach_btn = QPushButton(input_container)
        attach_btn.setIcon(render_svg_icon(SVG_PAPERCLIP, 16, color="#71717A", hover_color="#18181B"))
        attach_btn.setFixedSize(28, 28)
        attach_btn.setStyleSheet("background: transparent; border: none; border-radius: 12px;")
        attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ic_layout.addWidget(attach_btn)

        # Black circular send button with white up arrow
        send_btn = QPushButton(input_container)
        send_btn.setIcon(render_svg_icon(SVG_ARROW_UP, 16, color="#FFFFFF"))
        send_btn.setFixedSize(32, 32)
        send_btn.setStyleSheet("background-color: #18181B; border-radius: 16px; border: none;")
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.clicked.connect(self._handle_enter)
        ic_layout.addWidget(send_btn)

        outer_layout.addWidget(input_container)

    def _toggle_incognito(self) -> None:
        self.incognito_mode = not self.incognito_mode
        if self.incognito_mode:
            self.incognito_btn.setStyleSheet("QPushButton { background-color: #18181B; color: #FFFFFF; border-radius: 12px; padding: 4px 8px; font-size: 11px; font-weight: 700; border: none; }")
            self.incognito_banner.setVisible(True)
        else:
            self.incognito_btn.setStyleSheet("QPushButton { background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 12px; padding: 4px 8px; color: #52525B; font-size: 11px; font-weight: 600; }")
            self.incognito_banner.setVisible(False)

    def _toggle_history_drawer(self) -> None:
        is_visible = not self.history_drawer.isVisible()
        if is_visible:
            self.history_drawer.load_sessions(self.sessions_cache, self.current_session_id)
        self.history_drawer.setVisible(is_visible)

    def _build_intro_box(self) -> QWidget:
        intro = QWidget(self.chat_content)
        i_layout = QVBoxLayout(intro)
        i_layout.setContentsMargins(10, 10, 10, 14)
        i_layout.setSpacing(6)
        i_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        badge = QLabel(intro)
        badge.setPixmap(render_svg_pixmap(SVG_HANDLESS_MARK, 24, 24, color="#18181B"))
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        i_layout.addWidget(badge)

        headline = QLabel("What can I take care of?", intro)
        headline.setStyleSheet("color: #18181B; font-size: 20px; font-weight: 700; font-family: 'Playfair Display', 'Georgia', serif;")
        headline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        i_layout.addWidget(headline)

        sub = QLabel("Just tell me what you want to do,\nI'll handle the rest.", intro)
        sub.setStyleSheet("color: #71717A; font-size: 11.5px; line-height: 1.4;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        i_layout.addWidget(sub)

        return intro

    def _add_example_flow(self) -> None:
        """Add realistic example message flow and live execution card matching screenshot."""
        self.add_user_message("Open Chrome and find the latest design trends", "4:58 PM")
        self.add_assistant_message("I can do that. I'll open Chrome and look for current design trends.", "4:58 PM")

        self.plan_card = MultiStepPlanCard(self.chat_content)
        self.plan_card.view_activity_clicked.connect(lambda: self.command_submitted.emit("show activity log"))
        self._insert_before_stretch(self.plan_card)

    def add_user_message(self, text: str, time_str: str = "Just now") -> None:
        row = QWidget(self.chat_content)
        r_layout = QHBoxLayout(row)
        r_layout.setContentsMargins(0, 2, 0, 2)
        r_layout.setSpacing(8)
        r_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        bubble_col = QVBoxLayout()
        bubble_col.setContentsMargins(0, 0, 0, 0)
        bubble_col.setSpacing(2)
        bubble_col.setAlignment(Qt.AlignmentFlag.AlignRight)

        bubble = QFrame(row)
        bubble.setStyleSheet("background-color: #F4F3EE; border: 1px solid #ECE7DC; border-radius: 14px;")
        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(12, 10, 12, 10)
        lbl = QLabel(text, bubble)
        lbl.setStyleSheet("color: #18181B; font-size: 12px; border: none; background: transparent;")
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        b_layout.addWidget(lbl)
        bubble_col.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignRight)

        time_lbl = QLabel(time_str, row)
        time_lbl.setStyleSheet("color: #A1A1AA; font-size: 9.5px;")
        bubble_col.addWidget(time_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        r_layout.addLayout(bubble_col)

        avatar = QLabel(row)
        avatar.setPixmap(render_svg_pixmap(SVG_USER, 14, 14, color="#FFFFFF"))
        avatar.setStyleSheet("background-color: #18181B; border-radius: 14px; padding: 7px;")
        avatar.setFixedSize(28, 28)
        r_layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignTop)

        self._insert_before_stretch(row)
        self._scroll_to_bottom()
        self._record_message_to_session("user", text)

    def add_assistant_message(self, text: str, time_str: str = "Just now") -> None:
        row = QWidget(self.chat_content)
        r_layout = QHBoxLayout(row)
        r_layout.setContentsMargins(0, 2, 0, 2)
        r_layout.setSpacing(8)
        r_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        avatar = QLabel(row)
        avatar.setPixmap(render_svg_pixmap(SVG_HANDLESS_MARK, 14, 14, color="#18181B"))
        avatar.setStyleSheet("background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 14px; padding: 7px;")
        avatar.setFixedSize(28, 28)
        r_layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignTop)

        bubble_col = QVBoxLayout()
        bubble_col.setContentsMargins(0, 0, 0, 0)
        bubble_col.setSpacing(2)

        bubble = QFrame(row)
        bubble.setStyleSheet("background-color: #FAF9F5; border: 1px solid #ECE7DC; border-radius: 14px;")
        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(12, 10, 12, 10)
        lbl = QLabel(text, bubble)
        lbl.setStyleSheet("color: #18181B; font-size: 12px; line-height: 1.4; border: none; background: transparent;")
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        b_layout.addWidget(lbl)
        bubble_col.addWidget(bubble)

        time_lbl = QLabel(time_str, row)
        time_lbl.setStyleSheet("color: #A1A1AA; font-size: 9.5px;")
        bubble_col.addWidget(time_lbl)
        r_layout.addLayout(bubble_col)

        self._insert_before_stretch(row)
        self._scroll_to_bottom()
        self._record_message_to_session("assistant", text)

    def add_config_proposal_card(self, proposal: ConfigProposal) -> HandlessConfigActionCard:
        """Render an interactive Preview & Allow card for in-chat self-configuration."""
        card = HandlessConfigActionCard(proposal, self.chat_content)
        card.allow_clicked.connect(lambda k, v: self.config_change_applied.emit(k, v))
        self._insert_before_stretch(card)
        self._scroll_to_bottom()
        return card

    def _insert_before_stretch(self, widget: QWidget) -> None:
        count = self.chat_layout.count()
        index = max(0, count - 1)
        self.chat_layout.insertWidget(index, widget)

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def _handle_enter(self) -> None:
        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.add_user_message(text)
            self.command_submitted.emit(text)

    def _handle_new_chat(self) -> None:
        while self.chat_layout.count() > 2:
            item = self.chat_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        self.current_session_id = str(uuid.uuid4())
        self.new_chat_requested.emit()

    def _open_chat_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background: #FFFFFF; border: 1px solid #ECE8DE; border-radius: 8px; padding: 6px; }")
        menu.addAction("Clear chat", self._handle_new_chat)
        menu.addAction("Export transcript", lambda: self.command_submitted.emit("export transcript"))
        menu.addAction("Incognito mode", self._toggle_incognito)
        menu.exec(QCursor.pos())

    # -----------------------------------------------------------------------
    # Persistent Session Management
    # -----------------------------------------------------------------------

    def _load_sessions_from_disk(self) -> List[Dict[str, Any]]:
        if not CHAT_SESSIONS_FILE.exists():
            return []
        try:
            with open(CHAT_SESSIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_sessions_to_disk(self) -> None:
        if self.incognito_mode:
            return
        CHAT_SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(CHAT_SESSIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.sessions_cache[:30], f, indent=2)
        except Exception as exc:
            logger.warning("Could not persist chat sessions: %s", exc)

    def _record_message_to_session(self, role: str, text: str) -> None:
        if self.incognito_mode:
            return

        session = next((s for s in self.sessions_cache if s.get("id") == self.current_session_id), None)
        if not session:
            session = {
                "id": self.current_session_id,
                "title": text[:30] if role == "user" else "Handless Session",
                "time_str": datetime.now().strftime("%b %d, %H:%M"),
                "messages": [],
            }
            self.sessions_cache.insert(0, session)
        elif session.get("title") == "Handless Session" and role == "user":
            session["title"] = text[:30]

        session["messages"].append({"role": role, "text": text, "time": datetime.now().strftime("%I:%M %p")})
        self._save_sessions_to_disk()

    def _load_session_by_id(self, session_id: str) -> None:
        session = next((s for s in self.sessions_cache if s.get("id") == session_id), None)
        if not session:
            return

        # Clear current stream except intro
        while self.chat_layout.count() > 2:
            item = self.chat_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        self.current_session_id = session_id
        for msg in session.get("messages", []):
            role = msg.get("role")
            text = msg.get("text", "")
            time_str = msg.get("time", "Earlier")
            if role == "user":
                self.add_user_message(text, time_str)
            else:
                self.add_assistant_message(text, time_str)

        if self.history_drawer.isVisible():
            self.history_drawer.load_sessions(self.sessions_cache, self.current_session_id)
