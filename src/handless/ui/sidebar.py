"""Modern AI Copilot Sidebar for Vyoma Handless.

A bespoke, luxury cream & paper desktop copilot sidebar matching the modern
handless™ reference design:
- Left vertical navigation rail (Home, Chat, Apps, Lightning, Folder, Clock, Avatar)
- Top brand header: "handless™ by Vyoma Group" + "● Ready ⌵" status pill
- Hero Section: "Your desktop, without hands." with elegant italic script & 3D metallic emblem
- Unified rounded interaction card with:
    * Search & prompt input bar (equalizer icon, paperclip, upward arrow send button)
    * 4 Quick Action cards (Open Chrome, Open YouTube, Capture Screen, Search Web)
- Recent activity feed with dynamic live history and re-run chevrons
- Bottom floating status pill: Command Mode modern toggle switch + Listening visualizer
- Dual-view stacked architecture: Full Hero Dashboard & Conversation Stream
- 100% High-DPI Vector SVG iconography and responsive animations
"""

from __future__ import annotations

import logging
import math
from typing import Callable, List, Optional

import pyperclip
from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    Property,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QGradient,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QStyleOption,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from handless.safety.emergency_stop import emergency_stop
from .icons import (
    SVG_APPS_GRID,
    SVG_ARROW_LEFT_RIGHT,
    SVG_ARROW_UP,
    SVG_BRAND_CHROME,
    SVG_BRAND_YOUTUBE,
    SVG_CAPTURE_SCREEN,
    SVG_CHAT,
    SVG_CHECK,
    SVG_CHEVRON_DOWN,
    SVG_CHEVRON_RIGHT,
    SVG_CLICK,
    SVG_CLOCK,
    SVG_CLOSE,
    SVG_COPY,
    SVG_DOWNLOAD,
    SVG_EXPAND_HORIZONTAL,
    SVG_FILE_TEXT,
    SVG_FOLDER,
    SVG_GLOBE,
    SVG_GRID_9,
    SVG_HANDLESS_MARK,
    SVG_HOME,
    SVG_IMAGE,
    SVG_KEYBOARD,
    SVG_LIGHTNING,
    SVG_MIC,
    SVG_MIC_ACTIVE,
    SVG_MINUS,
    SVG_MUSIC,
    SVG_PAPERCLIP,
    SVG_PEN,
    SVG_PENCIL,
    SVG_PHONE,
    SVG_PHONE_OFF,
    SVG_PLAY,
    SVG_REFRESH,
    SVG_ROCKET,
    SVG_SEARCH,
    SVG_SETTINGS,
    SVG_SNAP,
    SVG_SPARKLE,
    SVG_STOP,
    SVG_USER,
    SVG_VIDEO_CAMERA,
    SVG_VOICE_WAVE,
    get_bot_logo_icon,
    get_bot_logo_pixmap,
    render_svg_icon,
    render_svg_pixmap,
)
from .screens import (
    ChatScreenView,
    DottedFluidOrbWidget,
    ExploreScreenView,
    Files3DIllustration,
    FilesScreenView,
    History3DIllustration,
    HistoryScreenView,
    LiveCallScreenView,
    MeetingTranscriptsView,
    MultiStepPlanCard,
    SettingsScreenView,
    Thunder3DIllustration,
    ThunderScreenView,
)
from .responsive import (
    clear_inherited_frame_borders,
    enable_horizontal_wheel,
    fit_to_width,
    flow_pill_rows,
)
from .styles import SIDEBAR_QSS
from .thinking_orbs import ThinkingOrbWidget

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Visual & Interactive Micro-Components
# ---------------------------------------------------------------------------

class GradientOrbWidget(ThinkingOrbWidget):
    """Thinking-orbs powered AI core indicator in Handless signature theme."""

    def __init__(self, parent: Optional[QWidget] = None, size: int = 34) -> None:
        super().__init__(size=size, state="breathing", theme="handless", parent=parent)

    def set_active(self, active: bool) -> None:
        super().set_active(active)


class SoundWaveVisualizer(QWidget):
    """Animated vertical sound wave equalizer bars during speech/listening."""

    def __init__(self, parent: Optional[QWidget] = None, bar_count: int = 4) -> None:
        super().__init__(parent)
        self.bar_count = bar_count
        self.setFixedSize(24, 20)
        self._is_active = False
        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(33)

    def set_active(self, active: bool) -> None:
        self._is_active = active
        self.update()

    def _on_tick(self) -> None:
        if self._is_active:
            self._phase = (self._phase + 0.22) % (2 * math.pi)
            self.update()
        elif self.isVisible():
            self._phase = (self._phase + 0.05) % (2 * math.pi)
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_w = 2.4
        gap = 2.5
        total_w = (self.bar_count * bar_w) + ((self.bar_count - 1) * gap)
        start_x = (w - total_w) / 2.0
        cy = h / 2.0

        for i in range(self.bar_count):
            x = start_x + (i * (bar_w + gap))
            if self._is_active:
                amp = (math.sin(self._phase + (i * 1.25)) + 1.0) * 0.5
                bar_h = 4.0 + (amp * 12.0)
                color = QColor(16, 185, 129, 230)  # Emerald green when listening
            else:
                amp = (math.sin(self._phase + (i * 0.8)) + 1.0) * 0.5
                bar_h = 3.0 + (amp * 3.0)
                color = QColor(113, 113, 122, 160)

            rect_y = cy - (bar_h / 2.0)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRect(int(x), int(rect_y), int(bar_w), int(bar_h)), 1.2, 1.2)


class ModernToggleSwitch(QWidget):
    """Sleek iOS/macOS-style sliding toggle switch for Command/Dictation mode."""
    toggled = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None, checked: bool = True) -> None:
        super().__init__(parent)
        self.setFixedSize(38, 22)
        self._checked = checked
        self._thumb_pos = 1.0 if checked else 0.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"thumb_pos")
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def get_thumb_pos(self) -> float:
        return self._thumb_pos

    def set_thumb_pos(self, pos: float) -> None:
        self._thumb_pos = pos
        self.update()

    thumb_pos = Property(float, get_thumb_pos, set_thumb_pos)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, checked: bool) -> None:
        if self._checked != checked:
            self._checked = checked
            self._anim.stop()
            self._anim.setStartValue(self._thumb_pos)
            self._anim.setEndValue(1.0 if checked else 0.0)
            self._anim.start()
            self.toggled.emit(checked)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_checked(not self._checked)
            event.accept()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = h / 2.0

        # Background track color interpolation
        # Checked = #18181B (24, 24, 27), Unchecked = #E4E4E7 (228, 228, 231)
        r = int(228 + (24 - 228) * self._thumb_pos)
        g = int(228 + (24 - 228) * self._thumb_pos)
        b = int(231 + (27 - 231) * self._thumb_pos)
        track_color = QColor(r, g, b)

        painter.setBrush(track_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, w, h, radius, radius)

        # White thumb knob with shadow
        thumb_diameter = h - 4
        travel_distance = w - thumb_diameter - 4
        thumb_x = 2 + (travel_distance * self._thumb_pos)
        thumb_y = 2

        # Shadow
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.drawEllipse(QPoint(int(thumb_x + thumb_diameter / 2), int(thumb_y + thumb_diameter / 2 + 1)), int(thumb_diameter / 2), int(thumb_diameter / 2))

        # Knob
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(QPoint(int(thumb_x + thumb_diameter / 2), int(thumb_y + thumb_diameter / 2)), int(thumb_diameter / 2), int(thumb_diameter / 2))


class Hero3DIllustration(QWidget):
    """Sleek 3D metallic emblem with dual capsule slits & sweeping orbital halo ring."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(115, 115)
        self._phase = 0.0

        # Gentle floating breathing animation (30 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(33)

    def _on_tick(self) -> None:
        self._phase = (self._phase + 0.035) % (2 * math.pi)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = (h / 2.0) - 2.0

        # Gentle floating offset
        float_y = math.sin(self._phase) * 2.2

        # 1. Soft Diffused Ambient Ground Shadow
        shadow_grad = QRadialGradient(cx, cy + 38, 40)
        shadow_grad.setColorAt(0.0, QColor(0, 0, 0, 35))
        shadow_grad.setColorAt(0.7, QColor(0, 0, 0, 10))
        shadow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(shadow_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy + 38), 42, 12)

        # 2. Back arc of tilted orbital ring
        painter.save()
        painter.translate(cx, cy + float_y)
        painter.rotate(-28)

        # Draw Back half of Ring (faded)
        back_pen = QPen(QColor(180, 180, 185, 120), 3.2)
        back_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(back_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(-44, -18, 88, 36, 0 * 16, 180 * 16)
        painter.restore()

        # 3. Two Vertical Dark Metallic Pill Cylinders (staggered & slightly tilted)
        painter.save()
        painter.translate(cx, cy + float_y)
        painter.rotate(-8)

        # Pill 1 (Left, shorter)
        p1_rect = QRect(-20, -22, 14, 46)
        p1_grad = QLinearGradient(p1_rect.left(), p1_rect.top(), p1_rect.right(), p1_rect.bottom())
        p1_grad.setColorAt(0.0, QColor(39, 39, 42))
        p1_grad.setColorAt(0.4, QColor(24, 24, 27))
        p1_grad.setColorAt(1.0, QColor(9, 9, 11))
        painter.setBrush(p1_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(p1_rect, 7, 7)

        # Subtle specular sheen on Pill 1
        p1_sheen = QLinearGradient(p1_rect.left() + 2, p1_rect.top() + 2, p1_rect.left() + 5, p1_rect.top() + 18)
        p1_sheen.setColorAt(0.0, QColor(255, 255, 255, 90))
        p1_sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(p1_sheen)
        painter.drawRoundedRect(QRect(-18, -20, 4, 16), 2, 2)

        # Pill 2 (Right, taller)
        p2_rect = QRect(2, -28, 15, 56)
        p2_grad = QLinearGradient(p2_rect.left(), p2_rect.top(), p2_rect.right(), p2_rect.bottom())
        p2_grad.setColorAt(0.0, QColor(63, 63, 70))
        p2_grad.setColorAt(0.35, QColor(24, 24, 27))
        p2_grad.setColorAt(1.0, QColor(9, 9, 11))
        painter.setBrush(p2_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(p2_rect, 7.5, 7.5)

        # Specular sheen on Pill 2
        p2_sheen = QLinearGradient(p2_rect.left() + 2, p2_rect.top() + 2, p2_rect.left() + 6, p2_rect.top() + 22)
        p2_sheen.setColorAt(0.0, QColor(255, 255, 255, 110))
        p2_sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(p2_sheen)
        painter.drawRoundedRect(QRect(4, -26, 4, 20), 2, 2)

        painter.restore()

        # 4. Front arc of sweeping orbital ring (cutting across in front)
        painter.save()
        painter.translate(cx, cy + float_y)
        painter.rotate(-28)

        front_pen = QPen(QColor(24, 24, 27, 240), 3.4)
        front_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(front_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(-44, -18, 88, 36, 180 * 16, 180 * 16)

        # Luminous highlight along the ring edge
        ring_sheen = QPen(QColor(255, 255, 255, 180), 1.2)
        painter.setPen(ring_sheen)
        painter.drawArc(-43, -17, 86, 34, 200 * 16, 80 * 16)

        painter.restore()


class AnimatedThinkingWidget(QWidget):
    """Thinking-orbs powered 20px dotted indicator for AI reasoning & processing."""

    def __init__(self, parent: Optional[QWidget] = None, state: str = "solving") -> None:
        super().__init__(parent)
        self.setFixedSize(54, 26)
        self._phase = 0.0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._orb = ThinkingOrbWidget(size=20, state=state, theme="handless", parent=self)
        layout.addWidget(self._orb)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(33)

    def _on_tick(self) -> None:
        self._phase = (self._phase + 0.16) % (2 * math.pi)
        self.update()

    def set_state(self, state: str) -> None:
        self._orb.set_state(state)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 13, 13)
        painter.fillPath(path, QColor(244, 244, 245, 230))
        painter.setPen(QPen(QColor(228, 228, 231, 200), 1))
        painter.drawPath(path)


class MessageToolbar(QWidget):
    """Floating vector SVG action toolbar attached to user messages."""

    def __init__(
        self,
        text: str,
        on_edit: Optional[Callable[[str], None]] = None,
        on_retry: Optional[Callable[[str], None]] = None,
        on_refine: Optional[Callable[[str], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.text = text
        self.on_edit = on_edit
        self.on_retry = on_retry
        self.on_refine = on_refine
        self.setObjectName("messageToolbar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(3)

        btn_sparkle = QPushButton(self)
        btn_sparkle.setObjectName("toolButton")
        btn_sparkle.setIcon(render_svg_icon(SVG_SPARKLE, 14, color="#E2E8F0", hover_color="#FDE047"))
        btn_sparkle.setIconSize(QSize(14, 14))
        btn_sparkle.setToolTip("Refine with AI")
        btn_sparkle.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sparkle.clicked.connect(self._refine)
        layout.addWidget(btn_sparkle)

        btn_edit = QPushButton(self)
        btn_edit.setObjectName("toolButton")
        btn_edit.setIcon(render_svg_icon(SVG_PENCIL, 14, color="#E2E8F0", hover_color="#FFFFFF"))
        btn_edit.setIconSize(QSize(14, 14))
        btn_edit.setToolTip("Edit prompt")
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.clicked.connect(self._edit)
        layout.addWidget(btn_edit)

        btn_retry = QPushButton(self)
        btn_retry.setObjectName("toolButton")
        btn_retry.setIcon(render_svg_icon(SVG_REFRESH, 14, color="#E2E8F0", hover_color="#60A5FA"))
        btn_retry.setIconSize(QSize(14, 14))
        btn_retry.setToolTip("Retry command")
        btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_retry.clicked.connect(self._retry)
        layout.addWidget(btn_retry)

        btn_copy = QPushButton(self)
        btn_copy.setObjectName("toolButton")
        btn_copy.setIcon(render_svg_icon(SVG_COPY, 14, color="#E2E8F0", hover_color="#34D399"))
        btn_copy.setIconSize(QSize(14, 14))
        btn_copy.setToolTip("Copy text")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.clicked.connect(self._copy)
        layout.addWidget(btn_copy)

    def _copy(self) -> None:
        pyperclip.copy(self.text)

    def _edit(self) -> None:
        if self.on_edit:
            self.on_edit(self.text)

    def _retry(self) -> None:
        if self.on_retry:
            self.on_retry(self.text)

    def _refine(self) -> None:
        if self.on_refine:
            self.on_refine(self.text)


class ActionCardWidget(QWidget):
    """Textured action card widget (e.g. Top_20_SaaS_Companies.csv, App Launched)."""

    def __init__(
        self,
        title: str,
        subtitle: str = "Completed action",
        icon_category: str = "file",
        btn_label: str = "download",
        on_action: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("actionCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(13, 9, 13, 9)
        layout.setSpacing(11)

        svg_xml, icon_color = self._resolve_icon(icon_category, title)
        icon_pixmap = render_svg_pixmap(svg_xml, 20, 20, color=icon_color)

        icon_lbl = QLabel(self)
        icon_lbl.setPixmap(icon_pixmap)
        icon_lbl.setFixedSize(20, 20)
        layout.addWidget(icon_lbl)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        t_lbl = QLabel(title, self)
        t_lbl.setObjectName("actionCardTitle")
        t_lbl.setWordWrap(True)
        text_layout.addWidget(t_lbl)

        if subtitle:
            s_lbl = QLabel(subtitle, self)
            s_lbl.setObjectName("actionCardSubtitle")
            text_layout.addWidget(s_lbl)

        layout.addLayout(text_layout, stretch=1)

        action_btn = QPushButton(self)
        action_btn.setObjectName("actionCardBtn")
        action_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        if btn_label.lower() in ("download", "down", "⬇"):
            action_btn.setIcon(render_svg_icon(SVG_DOWNLOAD, 15, color="#FFFFFF"))
            action_btn.setToolTip("Open / Download file")
        elif btn_label.lower() in ("check", "✓", "done"):
            action_btn.setIcon(render_svg_icon(SVG_CHECK, 15, color="#34D399"))
            action_btn.setToolTip("Success")
        else:
            action_btn.setText(btn_label)

        if on_action:
            action_btn.clicked.connect(on_action)
        layout.addWidget(action_btn)

    @staticmethod
    def _resolve_icon(category: str, title: str) -> tuple[str, str]:
        c = (category + " " + title).lower()
        if any(w in c for w in ("csv", "file", "doc", "sheet", "export", "pdf")):
            return SVG_FILE_TEXT, "#10B981"
        elif any(w in c for w in ("launch", "app", "open", "program")):
            return SVG_ROCKET, "#8B5CF6"
        elif any(w in c for w in ("snap", "window", "monitor", "display", "layout")):
            return SVG_SNAP, "#3B82F6"
        elif any(w in c for w in ("browser", "web", "url", "chrome", "google")):
            return SVG_GLOBE, "#06B6D4"
        elif any(w in c for w in ("music", "media", "play", "pause", "mute", "volume")):
            return SVG_MUSIC, "#F59E0B"
        elif any(w in c for w in ("dictat", "type", "text", "paste")):
            return SVG_PEN, "#EC4899"
        elif any(w in c for w in ("shortcut", "key", "press")):
            return SVG_KEYBOARD, "#6366F1"
        elif any(w in c for w in ("click", "mouse", "select")):
            return SVG_CLICK, "#14B8A6"
        return SVG_LIGHTNING, "#F59E0B"


# ---------------------------------------------------------------------------
# Left Navigation Rail Widget
# ---------------------------------------------------------------------------

class LeftNavRail(QWidget):
    """Vertical navigation rail (Home, Chat, Meeting, Apps, Lightning, Folder, Clock, Profile)."""
    home_clicked = Signal()
    chat_clicked = Signal()
    meeting_clicked = Signal()
    apps_clicked = Signal()
    lightning_clicked = Signal()
    folder_clicked = Signal()
    clock_clicked = Signal()
    settings_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("leftNavRail")
        self.setFixedWidth(52)
        self._active_tab = "home"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 12, 6, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # 1. Top Logo Mark (Handless Bot without background)
        self.mark_btn = QPushButton(self)
        self.mark_btn.setProperty("class", "navRailBtn")
        bot_pix = get_bot_logo_pixmap(without_bg=True, size=24)
        if not bot_pix.isNull():
            self.mark_btn.setIcon(QIcon(bot_pix))
            self.mark_btn.setIconSize(QSize(24, 24))
        else:
            self.mark_btn.setIcon(render_svg_icon(SVG_HANDLESS_MARK, 18, color="#18181B"))
            self.mark_btn.setIconSize(QSize(18, 18))
        self.mark_btn.setFixedSize(38, 38)
        self.mark_btn.setToolTip("handless™")
        self.mark_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mark_btn.clicked.connect(self.home_clicked)
        layout.addWidget(self.mark_btn)

        layout.addSpacing(6)

        # 2. Main Navigation Icons
        self.btn_home = QPushButton(self)
        self.btn_home.setFixedSize(38, 38)
        self.btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_home.setToolTip("Home Dashboard")
        self.btn_home.clicked.connect(self._on_home_press)
        layout.addWidget(self.btn_home)

        self.btn_chat = QPushButton(self)
        self.btn_chat.setFixedSize(38, 38)
        self.btn_chat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_chat.setToolTip("Conversation & History")
        self.btn_chat.clicked.connect(self._on_chat_press)
        layout.addWidget(self.btn_chat)

        self.btn_meeting = QPushButton(self)
        self.btn_meeting.setFixedSize(38, 38)
        self.btn_meeting.setProperty("class", "navRailBtn")
        self.btn_meeting.setIcon(render_svg_icon(SVG_VIDEO_CAMERA, 18, color="#52525B", hover_color="#18181B"))
        self.btn_meeting.setIconSize(QSize(18, 18))
        self.btn_meeting.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_meeting.setToolTip("Call Transcripts & Meeting Notes (Zoom, Meet, Teams, WhatsApp)")
        self.btn_meeting.clicked.connect(self._on_meeting_press)
        layout.addWidget(self.btn_meeting)

        self.btn_apps = QPushButton(self)
        self.btn_apps.setFixedSize(38, 38)
        self.btn_apps.setProperty("class", "navRailBtn")
        self.btn_apps.setIcon(render_svg_icon(SVG_APPS_GRID, 18, color="#52525B", hover_color="#18181B"))
        self.btn_apps.setIconSize(QSize(18, 18))
        self.btn_apps.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apps.setToolTip("Explore & Applications")
        self.btn_apps.clicked.connect(self._on_apps_press)
        layout.addWidget(self.btn_apps)

        self.btn_lightning = QPushButton(self)
        self.btn_lightning.setFixedSize(38, 38)
        self.btn_lightning.setProperty("class", "navRailBtn")
        self.btn_lightning.setIcon(render_svg_icon(SVG_LIGHTNING, 18, color="#52525B", hover_color="#18181B"))
        self.btn_lightning.setIconSize(QSize(18, 18))
        self.btn_lightning.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lightning.setToolTip("Thunder & Automations")
        self.btn_lightning.clicked.connect(self._on_lightning_press)
        layout.addWidget(self.btn_lightning)

        self.btn_folder = QPushButton(self)
        self.btn_folder.setFixedSize(38, 38)
        self.btn_folder.setProperty("class", "navRailBtn")
        self.btn_folder.setIcon(render_svg_icon(SVG_FOLDER, 18, color="#52525B", hover_color="#18181B"))
        self.btn_folder.setIconSize(QSize(18, 18))
        self.btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_folder.setToolTip("Files & Downloads")
        self.btn_folder.clicked.connect(self._on_folder_press)
        layout.addWidget(self.btn_folder)

        self.btn_clock = QPushButton(self)
        self.btn_clock.setFixedSize(38, 38)
        self.btn_clock.setProperty("class", "navRailBtn")
        self.btn_clock.setIcon(render_svg_icon(SVG_CLOCK, 18, color="#52525B", hover_color="#18181B"))
        self.btn_clock.setIconSize(QSize(18, 18))
        self.btn_clock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clock.setToolTip("Activity History")
        self.btn_clock.clicked.connect(self._on_clock_press)
        layout.addWidget(self.btn_clock)

        layout.addStretch(1)

        # 3. Bottom Profile Avatar & User Button
        self.avatar_lbl = QLabel("V", self)
        self.avatar_lbl.setObjectName("navAvatarBadge")
        self.avatar_lbl.setFixedSize(32, 32)
        self.avatar_lbl.setToolTip("Vyoma Workspace")
        layout.addWidget(self.avatar_lbl, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.btn_user = QPushButton(self)
        self.btn_user.setProperty("class", "navRailBtn")
        self.btn_user.setIcon(render_svg_icon(SVG_USER, 18, color="#52525B", hover_color="#18181B"))
        self.btn_user.setIconSize(QSize(18, 18))
        self.btn_user.setFixedSize(38, 38)
        self.btn_user.setToolTip("User Settings & Profile")
        self.btn_user.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_user.clicked.connect(self.settings_clicked)
        layout.addWidget(self.btn_user)

        self.set_active_tab("home")

    def set_active_tab(self, tab: str) -> None:
        self._active_tab = tab
        buttons = [
            ("home", self.btn_home, SVG_HOME),
            ("chat", self.btn_chat, SVG_CHAT),
            ("meeting", self.btn_meeting, SVG_VIDEO_CAMERA),
            ("apps", self.btn_apps, SVG_APPS_GRID),
            ("lightning", self.btn_lightning, SVG_LIGHTNING),
            ("folder", self.btn_folder, SVG_FOLDER),
            ("clock", self.btn_clock, SVG_CLOCK),
        ]
        for name, btn, svg in buttons:
            if tab == name:
                btn.setProperty("class", "navRailBtnActive")
                btn.setIcon(render_svg_icon(svg, 18, color="#FFFFFF"))
            else:
                btn.setProperty("class", "navRailBtn")
                btn.setIcon(render_svg_icon(svg, 18, color="#52525B", hover_color="#18181B"))
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_home_press(self) -> None:
        self.set_active_tab("home")
        self.home_clicked.emit()

    def _on_chat_press(self) -> None:
        self.set_active_tab("chat")
        self.chat_clicked.emit()

    def _on_meeting_press(self) -> None:
        self.set_active_tab("meeting")
        self.meeting_clicked.emit()

    def _on_apps_press(self) -> None:
        self.set_active_tab("apps")
        self.apps_clicked.emit()

    def _on_lightning_press(self) -> None:
        self.set_active_tab("lightning")
        self.lightning_clicked.emit()

    def _on_folder_press(self) -> None:
        self.set_active_tab("folder")
        self.folder_clicked.emit()

    def _on_clock_press(self) -> None:
        self.set_active_tab("clock")
        self.clock_clicked.emit()


# ---------------------------------------------------------------------------
# Hero Headline & Flourish Widget
# ---------------------------------------------------------------------------

class HeroHeadlineWidget(QWidget):
    """Hero headline with delicate italics and custom calligraphy underline swoop."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title = QLabel(self)
        title.setObjectName("heroTitle")
        title.setText(
            '<div style="font-size: 26px; font-weight: 700; color: #18181B; line-height: 1.15; font-family: \'Playfair Display\', \'Georgia\', serif;">'
            'Your desktop,<br>'
            'without <span style="font-style: italic; font-weight: 500; text-decoration: underline;">hands.</span>'
            '</div>'
        )
        title.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title)

        subtitle = QLabel(self)
        subtitle.setObjectName("heroSubtitle")
        subtitle.setText(
            '<div style="font-size: 11.5px; color: #71717A; line-height: 1.45; font-family: \'Segoe UI\', sans-serif;">'
            'Search, open, create, automate —<br>'
            'Handless handles it.'
            '</div>'
        )
        subtitle.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(subtitle)


# ---------------------------------------------------------------------------
# Unified Prompt & Quick Action Card Widget
# ---------------------------------------------------------------------------

class PromptInputCard(QWidget):
    """Container card with prompt input bar and 4 horizontal quick action cards."""
    command_submitted = Signal(str)
    voice_toggled = Signal()
    attach_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("promptContainerCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Top Input Row Bar
        input_row = QFrame(self)
        input_row.setObjectName("promptInputRow")
        input_row.setStyleSheet(
            "QFrame#promptInputRow { background-color: #F6F5EF; border: 1px solid #E5E1D6; border-radius: 14px; }"
            "QFrame#promptInputRow:focus-within { background-color: #FFFFFF; border: 1.2px solid #18181B; }"
        )
        row_layout = QHBoxLayout(input_row)
        row_layout.setContentsMargins(8, 4, 6, 4)
        row_layout.setSpacing(8)

        # Equalizer Wave Button
        self.wave_btn = QPushButton(input_row)
        self.wave_btn.setObjectName("headerButton")
        self.wave_btn.setIcon(render_svg_icon(SVG_VOICE_WAVE, 16, color="#71717A", hover_color="#18181B"))
        self.wave_btn.setIconSize(QSize(16, 16))
        self.wave_btn.setFixedSize(24, 24)
        self.wave_btn.setToolTip("Toggle Speech / Listening")
        self.wave_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.wave_btn.clicked.connect(self.voice_toggled)
        row_layout.addWidget(self.wave_btn)

        # Hairline vertical separator
        sep = QWidget(input_row)
        sep.setFixedSize(1, 16)
        sep.setStyleSheet("background-color: #E2DFD6;")
        row_layout.addWidget(sep)

        # Prompt input text
        self.input_field = QLineEdit(input_row)
        self.input_field.setObjectName("heroPromptInput")
        self.input_field.setPlaceholderText("Tell Handless what to do...")
        self.input_field.returnPressed.connect(self._handle_enter)
        row_layout.addWidget(self.input_field, stretch=1)

        # Paperclip attachment button
        self.attach_btn = QPushButton(input_row)
        self.attach_btn.setObjectName("promptAttachBtn")
        self.attach_btn.setIcon(render_svg_icon(SVG_PAPERCLIP, 16, color="#71717A", hover_color="#18181B"))
        self.attach_btn.setIconSize(QSize(16, 16))
        self.attach_btn.setFixedSize(28, 28)
        self.attach_btn.setToolTip("Attach file or capture context")
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.clicked.connect(self.attach_requested)
        row_layout.addWidget(self.attach_btn)

        # Black circular Send Button with Up Arrow (32x32)
        self.send_btn = QPushButton(input_row)
        self.send_btn.setObjectName("promptSendBtn")
        self.send_btn.setStyleSheet("background-color: #18181B; border-radius: 16px; border: none;")
        self.send_btn.setIcon(render_svg_icon(SVG_ARROW_UP, 16, color="#FFFFFF"))
        self.send_btn.setIconSize(QSize(16, 16))
        self.send_btn.setFixedSize(32, 32)
        self.send_btn.setToolTip("Submit Command")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._handle_enter)
        row_layout.addWidget(self.send_btn)

        layout.addWidget(input_row)

        # 2. Bottom 4 Quick Action Cards (Horizontal Grid)
        cards_widget = QWidget(self)
        cards_widget.setObjectName("quickCardsGrid")
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(6)

        quick_items = [
            ("Open Chrome", "open chrome", SVG_BRAND_CHROME, "#18181B"),
            ("Open YouTube", "open youtube", SVG_BRAND_YOUTUBE, "#18181B"),
            ("Capture Screen", "take a screenshot", SVG_CAPTURE_SCREEN, "#18181B"),
            ("Search Web", "search google for latest news", SVG_SEARCH, "#18181B"),
        ]

        for label, cmd, svg_xml, icon_color in quick_items:
            card_btn = QPushButton(cards_widget)
            card_btn.setProperty("class", "quickCard")
            card_btn.setStyleSheet(
                "QPushButton { background-color: #FAF9F5; border: 1px solid #E8E4DA; border-radius: 12px; }"
                "QPushButton:hover { background-color: #F2EFE6; border-color: #D2CDC0; }"
                "QPushButton:pressed { background-color: #EAE6DB; }"
            )
            card_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            card_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            card_btn.setMinimumWidth(0)

            c_layout = QVBoxLayout(card_btn)
            c_layout.setContentsMargins(2, 6, 2, 6)
            c_layout.setSpacing(3)
            c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            icon_lbl = QLabel(card_btn)
            icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            icon_lbl.setPixmap(render_svg_pixmap(svg_xml, 18, 18, color=icon_color))
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c_layout.addWidget(icon_lbl)

            text_lbl = QLabel(label, card_btn)
            text_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            text_lbl.setProperty("class", "quickCardTitle")
            text_lbl.setWordWrap(True)
            text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c_layout.addWidget(text_lbl)

            card_btn.clicked.connect(lambda checked=False, c=cmd: self.command_submitted.emit(c))
            cards_layout.addWidget(card_btn)

        layout.addWidget(cards_widget)

    def _handle_enter(self) -> None:
        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.command_submitted.emit(text)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(230, 227, 219), 1.2))
        painter.drawRoundedRect(rect, 18, 18)


# ---------------------------------------------------------------------------
# Recent Activity Feed Widget
# ---------------------------------------------------------------------------

class RecentActivityWidget(QWidget):
    """Recent executed tasks list with relative timestamps and action chevrons."""
    item_replayed = Signal(str)
    see_all_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("recentSectionContainer")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 4, 0, 0)
        self.main_layout.setSpacing(6)

        # Header Row
        header_row = QHBoxLayout()
        header_row.setContentsMargins(4, 0, 4, 2)

        title = QLabel("Recent", self)
        title.setObjectName("recentSectionTitle")
        header_row.addWidget(title)

        header_row.addStretch(1)

        see_all = QPushButton("See all →", self)
        see_all.setObjectName("recentSeeAllBtn")
        see_all.setCursor(Qt.CursorShape.PointingHandCursor)
        see_all.clicked.connect(self.see_all_clicked)
        header_row.addWidget(see_all)

        self.main_layout.addLayout(header_row)

        # List Container
        self.items_container = QWidget(self)
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(3)

        # Empty state until the user runs their first command
        self.empty_label = QLabel("Nothing yet. Try saying “open Chrome” or type a command above.", self.items_container)
        self.empty_label.setWordWrap(True)
        self.empty_label.setProperty("class", "recentItemTime")
        self.empty_label.setContentsMargins(6, 4, 6, 4)
        self.items_layout.addWidget(self.empty_label)

        self.main_layout.addWidget(self.items_container)

    def _add_row(self, title_text: str, time_text: str, svg: str, color: str, cmd: str) -> None:
        row = QWidget(self.items_container)
        row.setProperty("class", "recentItemRow")
        row.setCursor(Qt.CursorShape.PointingHandCursor)

        r_layout = QHBoxLayout(row)
        r_layout.setContentsMargins(6, 5, 8, 5)
        r_layout.setSpacing(10)

        # Icon box
        icon_box = QFrame(row)
        icon_box.setStyleSheet("background-color: #F5F3EC; border: 1px solid #E8E5DC; border-radius: 10px;")
        icon_box.setFixedSize(32, 32)
        ib_layout = QVBoxLayout(icon_box)
        ib_layout.setContentsMargins(0, 0, 0, 0)
        ib_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(icon_box)
        icon_lbl.setPixmap(render_svg_pixmap(svg, 16, 16, color=color))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ib_layout.addWidget(icon_lbl)
        r_layout.addWidget(icon_box)

        # Text column
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(1)

        t_lbl = QLabel(title_text, row)
        t_lbl.setProperty("class", "recentItemTitle")
        text_col.addWidget(t_lbl)

        tm_lbl = QLabel(time_text, row)
        tm_lbl.setProperty("class", "recentItemTime")
        text_col.addWidget(tm_lbl)

        r_layout.addLayout(text_col, stretch=1)

        # Chevron >
        chev = QLabel(row)
        chev.setPixmap(render_svg_pixmap(SVG_CHEVRON_RIGHT, 14, 14, color="#A1A1AA"))
        chev.setFixedSize(14, 14)
        r_layout.addWidget(chev)

        # Click handler
        row.mousePressEvent = lambda e: self.item_replayed.emit(cmd)
        self.items_layout.addWidget(row)

    def add_recent(self, title_text: str, time_text: str = "Just now", cmd: str = "") -> None:
        """Prepend a new recent action entry when user executes a command."""
        if self.empty_label is not None:
            self.items_layout.removeWidget(self.empty_label)
            self.empty_label.deleteLater()
            self.empty_label = None
        svg = SVG_ROCKET
        color = "#18181B"
        c_low = title_text.lower()
        if "chrome" in c_low or "browser" in c_low:
            svg = SVG_BRAND_CHROME
        elif "youtube" in c_low or "video" in c_low:
            svg = SVG_BRAND_YOUTUBE
        elif "capture" in c_low or "screenshot" in c_low:
            svg = SVG_CAPTURE_SCREEN
        elif "document" in c_low or "file" in c_low:
            svg = SVG_FILE_TEXT
        elif "setting" in c_low:
            svg = SVG_SETTINGS

        # Limit to 5 visible rows
        if self.items_layout.count() >= 5:
            last_item = self.items_layout.takeAt(self.items_layout.count() - 1)
            if last_item.widget():
                last_item.widget().deleteLater()

        # Insert at top
        row = QWidget(self.items_container)
        row.setProperty("class", "recentItemRow")
        row.setCursor(Qt.CursorShape.PointingHandCursor)

        r_layout = QHBoxLayout(row)
        r_layout.setContentsMargins(6, 5, 8, 5)
        r_layout.setSpacing(10)

        icon_box = QFrame(row)
        icon_box.setStyleSheet("background-color: #F5F3EC; border: 1px solid #E8E5DC; border-radius: 10px;")
        icon_box.setFixedSize(32, 32)
        ib_layout = QVBoxLayout(icon_box)
        ib_layout.setContentsMargins(0, 0, 0, 0)
        ib_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(icon_box)
        icon_lbl.setPixmap(render_svg_pixmap(svg, 16, 16, color=color))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ib_layout.addWidget(icon_lbl)
        r_layout.addWidget(icon_box)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(1)

        t_lbl = QLabel(title_text, row)
        t_lbl.setProperty("class", "recentItemTitle")
        text_col.addWidget(t_lbl)

        tm_lbl = QLabel(time_text, row)
        tm_lbl.setProperty("class", "recentItemTime")
        text_col.addWidget(tm_lbl)

        r_layout.addLayout(text_col, stretch=1)

        chev = QLabel(row)
        chev.setPixmap(render_svg_pixmap(SVG_CHEVRON_RIGHT, 14, 14, color="#A1A1AA"))
        chev.setFixedSize(14, 14)
        r_layout.addWidget(chev)

        row.mousePressEvent = lambda e: self.item_replayed.emit(cmd or title_text)
        self.items_layout.insertWidget(0, row)


# ---------------------------------------------------------------------------
# Bottom Status Pill
# ---------------------------------------------------------------------------

class BottomStatusPill(QWidget):
    """Floating pill container with Command Mode toggle, Live Call trigger, and Listening equalizer."""
    mode_toggled = Signal(bool)
    call_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("footerPillContainer")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # 1. Left side: Lightning icon + "Command Mode" text
        self.bolt_icon = QLabel(self)
        self.bolt_icon.setPixmap(render_svg_pixmap(SVG_LIGHTNING, 14, 14, color="#18181B"))
        self.bolt_icon.setFixedSize(14, 14)
        layout.addWidget(self.bolt_icon)

        self.mode_label = QLabel("Command Mode", self)
        self.mode_label.setObjectName("footerCommandModeLabel")
        self.mode_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.mode_label)

        # Sliding modern toggle switch
        self.toggle_switch = ModernToggleSwitch(self, checked=True)
        self.toggle_switch.toggled.connect(self._on_switch_toggled)
        layout.addWidget(self.toggle_switch)

        layout.addStretch(1)

        # Quick Live Call Phone Button
        self.call_btn = QPushButton(self)
        self.call_btn.setObjectName("footerCallButton")
        self.call_btn.setIcon(render_svg_icon(SVG_PHONE, 12, color="#10B981", hover_color="#059669"))
        self.call_btn.setIconSize(QSize(12, 12))
        self.call_btn.setFixedSize(22, 22)
        self.call_btn.setToolTip("Start Live Gemini 3.8 Call")
        self.call_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.call_btn.setStyleSheet("""
            QPushButton#footerCallButton {
                background-color: #E8F5E9;
                border: 1px solid #C8E6C9;
                border-radius: 11px;
            }
            QPushButton#footerCallButton:hover {
                background-color: #C8E6C9;
            }
        """)
        self.call_btn.clicked.connect(self.call_requested.emit)
        layout.addWidget(self.call_btn)

        # 2. Right side: Green Listening dot + label + equalizer
        self.dot_label = QLabel("●", self)
        self.dot_label.setStyleSheet("color: #10B981; font-size: 10px;")
        layout.addWidget(self.dot_label)

        self.listen_label = QLabel("Listening", self)
        self.listen_label.setObjectName("footerListeningBadge")
        self.listen_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.listen_label)

        sep = QWidget(self)
        sep.setFixedSize(1, 14)
        sep.setStyleSheet("background-color: #E2DFD6;")
        layout.addWidget(sep)

        self.wave_vis = SoundWaveVisualizer(self, bar_count=4)
        layout.addWidget(self.wave_vis)

    def minimumSizeHint(self) -> QSize:
        return QSize(220, 32)

    def _on_switch_toggled(self, checked: bool) -> None:
        if checked:
            self.mode_label.setText("Command Mode")
            self.bolt_icon.setPixmap(render_svg_pixmap(SVG_LIGHTNING, 14, 14, color="#18181B"))
        else:
            self.mode_label.setText("Dictation Mode")
            self.bolt_icon.setPixmap(render_svg_pixmap(SVG_PEN, 14, 14, color="#10B981"))
        self.mode_toggled.emit(checked)

    def set_listening_state(self, active: bool) -> None:
        self.wave_vis.set_active(active)
        if active:
            self.listen_label.setText("Listening")
            self.dot_label.setStyleSheet("color: #10B981; font-size: 10px;")
        else:
            self.listen_label.setText("Ready")
            self.dot_label.setStyleSheet("color: #71717A; font-size: 10px;")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(230, 227, 219), 1.2))
        painter.drawRoundedRect(rect, 18, 18)


# ---------------------------------------------------------------------------
# Main Modern Copilot Sidebar Window
# ---------------------------------------------------------------------------

class SidebarWindow(QWidget):
    """Modern, textured, and animated desktop AI copilot sidebar."""

    # Thread-safe Qt signals
    transcript_updated = Signal(str)
    status_updated = Signal(str)
    listening_changed = Signal(bool)
    dictation_changed = Signal(bool)
    closed_to_floating = Signal()
    dock_side_changed = Signal(str)
    live_call_toggled = Signal(bool)
    model_switched = Signal(str)

    def __init__(
        self,
        on_mic_toggled: Optional[Callable[[bool], None]] = None,
        on_open_settings: Optional[Callable[[], None]] = None,
        on_emergency_stop: Optional[Callable[[], None]] = None,
        on_command_submitted: Optional[Callable[[str], None]] = None,
        on_dictation_toggled: Optional[Callable[[bool], None]] = None,
        on_open_inspector: Optional[Callable[[], None]] = None,
        width: int = 450,
    ) -> None:
        super().__init__()
        self.on_mic_toggled = on_mic_toggled
        self.on_open_settings = on_open_settings
        self.on_emergency_stop = on_emergency_stop
        self.on_command_submitted = on_command_submitted
        self.on_dictation_toggled = on_dictation_toggled
        self.on_open_inspector = on_open_inspector
        self._sidebar_width = width
        self._dock_side = "right"  # "right" or "left"
        self._is_wide_mode = False

        self._is_dragging = False
        self._drag_pos = QPoint()
        self._drag_start_global = QPoint()
        self._is_listening = False
        self._is_dictation = False
        self._is_visible_state = False

        self._anim: Optional[QPropertyAnimation] = None
        self._thinking_widget: Optional[AnimatedThinkingWidget] = None

        self._setup_window_flags()
        self._init_ui()
        self._connect_signals()

    def _setup_window_flags(self) -> None:
        """Frameless, translucent, stays-on-top sidebar docked to screen edge."""
        self.setWindowTitle("Vyoma Handless — Desktop Copilot")
        bot_icon = get_bot_logo_icon(without_bg=False, size=64)
        if not bot_icon.isNull():
            self.setWindowIcon(bot_icon)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(SIDEBAR_QSS)

        self._calculate_dimensions()

    def _calculate_dimensions(self) -> None:
        """Position sidebar along the chosen screen edge, dynamically adapting to available space."""
        screen = (
            self.screen()
            or QApplication.screenAt(QCursor.pos())
            or QApplication.primaryScreen()
        )
        if screen:
            avail = screen.availableGeometry()
            margin_x = 12
            margin_y = 10
            min_w = self.minimumSizeHint().width()
            if self._is_wide_mode:
                # Always visibly wider than normal, even when large fonts raise the minimum
                w = max(640, min_w + 160)
            else:
                w = max(self._sidebar_width, min_w)
            # Never exceed 90% of available screen width
            max_allowed_w = max(360, int(avail.width() * 0.90))
            w = min(w, max_allowed_w)
            h = max(480, avail.height() - (margin_y * 2))
            y = avail.y() + margin_y

            # Pre-apply size so layout resolves
            self.resize(w, h)
            actual_w = max(w, self.width())
            if actual_w > max_allowed_w:
                actual_w = max_allowed_w
                self.setFixedWidth(actual_w)

            if self._dock_side == "left":
                x = avail.x() + margin_x
                off_x = avail.x() - actual_w - 40
            else:
                x = avail.x() + avail.width() - actual_w - margin_x
                off_x = avail.x() + avail.width() + 40

            # Guardrails: strictly guarantee the window stays completely within visible screen borders
            if x + actual_w > avail.x() + avail.width() - margin_x:
                x = avail.x() + avail.width() - actual_w - margin_x
            if x < avail.x() + margin_x:
                x = avail.x() + margin_x

            self.setGeometry(x, y, actual_w, h)
            self._target_rect = QRect(x, y, actual_w, h)
            self._offscreen_rect = QRect(off_x, y, actual_w, h)
        else:
            self.resize(self._sidebar_width, 820)

    def _ensure_within_screen_bounds(self) -> None:
        """Strict guardrail: ensure the sidebar never bleeds past screen edges."""
        if not self.isVisible() or not getattr(self, "_is_visible_state", False):
            return
        screen = (
            self.screen()
            or QApplication.screenAt(self.geometry().center())
            or QApplication.primaryScreen()
        )
        if not screen:
            return
        avail = screen.availableGeometry()
        margin_x = 12
        margin_y = 10
        cur_geom = self.geometry()
        cur_w = cur_geom.width()
        cur_h = cur_geom.height()
        cur_x = cur_geom.x()
        cur_y = cur_geom.y()

        needs_move = False
        new_x = cur_x
        new_y = cur_y

        if getattr(self, "_dock_side", "right") == "right":
            expected_right = avail.x() + avail.width() - margin_x
            if (cur_x + cur_w) != expected_right or (cur_x + cur_w) > (avail.x() + avail.width()):
                new_x = expected_right - cur_w
                needs_move = True
        elif getattr(self, "_dock_side", "right") == "left":
            expected_left = avail.x() + margin_x
            if cur_x != expected_left:
                new_x = expected_left
                needs_move = True

        if new_x < avail.x() + margin_x:
            new_x = avail.x() + margin_x
            needs_move = True

        if cur_y < avail.y() + margin_y or (cur_y + cur_h) > (avail.y() + avail.height()):
            new_y = avail.y() + margin_y
            needs_move = True

        if needs_move:
            self.move(new_x, new_y)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if (
            not getattr(self, "_is_dragging", False)
            and getattr(self, "_is_visible_state", False)
            and (not getattr(self, "_anim", None) or self._anim.state() != QPropertyAnimation.State.Running)
        ):
            self._ensure_within_screen_bounds()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(40, self._ensure_within_screen_bounds)

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(6, 6, 6, 6)

        # 1. Main Rounded Container with Shadow
        self.container = QWidget(self)
        self.container.setObjectName("sidebarContainer")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setColor(QColor(15, 23, 42, 60))
        shadow.setOffset(0, 6)
        self.container.setGraphicsEffect(shadow)

        # Horizontal split: Left Navigation Rail + Right Main Body
        body_layout = QHBoxLayout(self.container)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 2. Left Navigation Rail
        self.left_rail = LeftNavRail(self.container)
        self.left_rail.home_clicked.connect(self._show_dashboard_view)
        self.left_rail.chat_clicked.connect(self._show_chat_view)
        self.left_rail.meeting_clicked.connect(self._show_meeting_view)
        self.left_rail.apps_clicked.connect(self._show_explore_view)
        self.left_rail.lightning_clicked.connect(self._show_thunder_view)
        self.left_rail.folder_clicked.connect(self._show_files_view)
        self.left_rail.clock_clicked.connect(self._show_history_view)
        self.left_rail.settings_clicked.connect(self._handle_settings_click)
        self.left_rail.installEventFilter(self)
        body_layout.addWidget(self.left_rail)

        # 3. Right Content Area
        right_content = QWidget(self.container)
        right_layout = QVBoxLayout(right_content)
        right_layout.setContentsMargins(0, 0, 0, 12)
        right_layout.setSpacing(0)

        # Top Header (Brand, Status Pill, Header Buttons)
        self.header = self._build_header(right_content)
        self.header.installEventFilter(self)
        right_layout.addWidget(self.header)

        # Auto-adjust if display resolution or taskbar work area changes
        for s in QApplication.screens():
            try:
                s.availableGeometryChanged.connect(lambda geom: self._reposition(animated=False))
            except Exception:
                pass

        # View Switcher (Dashboard, Chat, Explore, Thunder, Files, History)
        self.view_stack = QStackedWidget(right_content)

        # Page 0: Hero Dashboard View (Home)
        self.dashboard_view = self._build_dashboard_view(self.view_stack)
        self.view_stack.addWidget(self.dashboard_view)

        # Page 1: Chat Stream View (Chat)
        self.chat_screen_view = ChatScreenView(self.view_stack)
        self.chat_screen_view.command_submitted.connect(self._submit_text_command)
        self.chat_screen_view.voice_toggled.connect(self._handle_mic_click)
        self.chat_screen_view.new_chat_requested.connect(self.clear_chat)
        self.view_stack.addWidget(self.chat_screen_view)

        # Backwards compatibility aliases
        self.chat_view = self.chat_screen_view
        self.chat_content = self.chat_screen_view.chat_content
        self.chat_layout = self.chat_screen_view.chat_layout
        self.scroll_area = self.chat_screen_view.scroll_area
        self.chat_input_field = self.chat_screen_view.input_field

        # Page 2: Explore View
        self.explore_screen_view = ExploreScreenView(self.view_stack)
        self.explore_screen_view.command_submitted.connect(self._submit_text_command)
        self.explore_screen_view.voice_toggled.connect(self._handle_mic_click)
        self.view_stack.addWidget(self.explore_screen_view)

        # Page 3: Thunder View
        self.thunder_screen_view = ThunderScreenView(self.view_stack)
        self.thunder_screen_view.command_submitted.connect(self._submit_text_command)
        self.thunder_screen_view.voice_toggled.connect(self._handle_mic_click)
        self.view_stack.addWidget(self.thunder_screen_view)

        # Page 4: Files View
        self.files_screen_view = FilesScreenView(self.view_stack)
        self.files_screen_view.command_submitted.connect(self._submit_text_command)
        self.files_screen_view.voice_toggled.connect(self._handle_mic_click)
        self.view_stack.addWidget(self.files_screen_view)

        # Page 5: History View
        self.history_screen_view = HistoryScreenView(self.view_stack)
        self.history_screen_view.command_submitted.connect(self._submit_text_command)
        self.history_screen_view.voice_toggled.connect(self._handle_mic_click)
        self.view_stack.addWidget(self.history_screen_view)

        # Page 6: Settings View
        self.settings_screen_view = SettingsScreenView(parent=self.view_stack)
        self.settings_screen_view.command_submitted.connect(self._submit_text_command)
        self.settings_screen_view.voice_toggled.connect(self._handle_mic_click)
        self.view_stack.addWidget(self.settings_screen_view)

        # Page 7: Live Call View (Gemini 3.8 Live & Extended Thinking)
        self.live_call_view = LiveCallScreenView(self.view_stack)
        self.live_call_view.call_ended_requested.connect(self.end_live_call)
        self.live_call_view.model_switch_requested.connect(self.model_switched)
        self.view_stack.addWidget(self.live_call_view)

        # Page 8: Call & Meeting Transcripts View (Zoom, Meet, WhatsApp, Teams)
        self.meeting_screen_view = MeetingTranscriptsView(parent=self.view_stack)
        self.meeting_screen_view.command_submitted.connect(self._submit_text_command)
        self.meeting_screen_view.voice_toggled.connect(self._handle_mic_click)
        self.view_stack.addWidget(self.meeting_screen_view)

        # Let every screen shrink to the sidebar width instead of clipping its right edge
        for i in range(self.view_stack.count()):
            page = self.view_stack.widget(i)
            flow_pill_rows(page)
            fit_to_width(page)
            enable_horizontal_wheel(page)
            clear_inherited_frame_borders(page)

        right_layout.addWidget(self.view_stack, stretch=1)
        self.view_stack.currentChanged.connect(lambda _: QTimer.singleShot(10, self._ensure_within_screen_bounds))

        # Bottom Status Pill
        self.bottom_pill = BottomStatusPill(right_content)
        self.bottom_pill.mode_toggled.connect(self._on_bottom_pill_mode_toggled)
        self.bottom_pill.call_requested.connect(self.toggle_live_call)
        pill_wrapper = QHBoxLayout()
        pill_wrapper.setContentsMargins(14, 4, 14, 0)
        pill_wrapper.addWidget(self.bottom_pill)
        right_layout.addLayout(pill_wrapper)

        body_layout.addWidget(right_content, stretch=1)
        outer_layout.addWidget(self.container)

        # Set unified cmd_input alias for backwards compatibility
        self.cmd_input = self.prompt_card.input_field

    def _build_header(self, parent: QWidget) -> QWidget:
        header = QWidget(parent)
        header.setObjectName("headerContainer")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(10, 8, 10, 6)
        h_layout.setSpacing(5)

        # Brand Column: "handless™" + "by Vyoma Group"
        brand_col = QVBoxLayout()
        brand_col.setContentsMargins(0, 0, 0, 0)
        brand_col.setSpacing(1)

        brand_title = QLabel("handless™", header)
        brand_title.setObjectName("headerBrandTitle")
        brand_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        brand_col.addWidget(brand_title)

        brand_sub = QLabel("by Vyoma Group", header)
        brand_sub.setObjectName("headerBrandSubtitle")
        brand_sub.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        brand_col.addWidget(brand_sub)
        h_layout.addLayout(brand_col)

        # Hairline separator
        sep = QWidget(header)
        sep.setFixedSize(1, 18)
        sep.setStyleSheet("background-color: #E2DFD6;")
        h_layout.addWidget(sep)

        # Ready Status Pill with Chevron
        self.status_pill = QWidget(header)
        self.status_pill.setObjectName("readyStatusPill")
        self.status_pill.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.status_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_pill.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sp_layout = QHBoxLayout(self.status_pill)
        sp_layout.setContentsMargins(6, 3, 6, 3)
        sp_layout.setSpacing(4)

        self.pill_dot = QLabel("●", self.status_pill)
        self.pill_dot.setStyleSheet("color: #10B981; font-size: 10px;")
        sp_layout.addWidget(self.pill_dot)

        self.pill_text = QLabel("Ready", self.status_pill)
        self.pill_text.setObjectName("readyStatusText")
        sp_layout.addWidget(self.pill_text)

        chev_down = QLabel(self.status_pill)
        chev_down.setPixmap(render_svg_pixmap(SVG_CHEVRON_DOWN, 10, 10, color="#71717A"))
        chev_down.setFixedSize(10, 10)
        sp_layout.addWidget(chev_down)

        self.status_pill.mousePressEvent = lambda e: self._open_status_menu()
        h_layout.addWidget(self.status_pill)

        h_layout.addStretch(1)

        # Action Buttons Layout (compact grouping)
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(1)

        # Live Call Phone Button
        self.call_btn = QPushButton(header)
        self.call_btn.setObjectName("headerButton")
        self.call_btn.setIcon(render_svg_icon(SVG_PHONE, 14, color="#10B981", hover_color="#059669"))
        self.call_btn.setIconSize(QSize(14, 14))
        self.call_btn.setFixedSize(26, 26)
        self.call_btn.setToolTip("Start Live Voice Call (Gemini 3.8 Live)")
        self.call_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.call_btn.clicked.connect(self.toggle_live_call)
        action_layout.addWidget(self.call_btn)

        # 9-Dot Menu Button
        self.menu_btn = QPushButton(header)
        self.menu_btn.setObjectName("headerButton")
        self.menu_btn.setIcon(render_svg_icon(SVG_GRID_9, 18, color="#52525B", hover_color="#18181B"))
        self.menu_btn.setIconSize(QSize(18, 18))
        self.menu_btn.setFixedSize(26, 26)
        self.menu_btn.setToolTip("Quick Actions & Workflows")
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.clicked.connect(self._open_quick_menu)
        action_layout.addWidget(self.menu_btn)

        # Dock Side Switch Button (Move Left/Right)
        self.dock_side_btn = QPushButton(header)
        self.dock_side_btn.setObjectName("headerButton")
        self.dock_side_btn.setIcon(render_svg_icon(SVG_ARROW_LEFT_RIGHT, 15, color="#52525B", hover_color="#18181B"))
        self.dock_side_btn.setIconSize(QSize(15, 15))
        self.dock_side_btn.setFixedSize(26, 26)
        self.dock_side_btn.setToolTip("Dock to Opposite Side (Left / Right)")
        self.dock_side_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dock_side_btn.clicked.connect(self.toggle_dock_side)
        action_layout.addWidget(self.dock_side_btn)

        # Wide / Expand Button (Toggle wide mode)
        self.wide_btn = QPushButton(header)
        self.wide_btn.setObjectName("headerButton")
        self.wide_btn.setIcon(render_svg_icon(SVG_EXPAND_HORIZONTAL, 15, color="#52525B", hover_color="#18181B"))
        self.wide_btn.setIconSize(QSize(15, 15))
        self.wide_btn.setFixedSize(26, 26)
        self.wide_btn.setToolTip("Toggle Wide View (Full Mode)")
        self.wide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.wide_btn.clicked.connect(self.toggle_wide_mode)
        action_layout.addWidget(self.wide_btn)

        # Settings Gear Button
        self.settings_btn = QPushButton(header)
        self.settings_btn.setObjectName("headerButton")
        self.settings_btn.setIcon(render_svg_icon(SVG_SETTINGS, 18, color="#52525B", hover_color="#18181B"))
        self.settings_btn.setIconSize(QSize(18, 18))
        self.settings_btn.setFixedSize(26, 26)
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self._handle_settings_click)
        action_layout.addWidget(self.settings_btn)

        # Separator
        sep2 = QWidget(header)
        sep2.setFixedSize(1, 14)
        sep2.setStyleSheet("background-color: #E2DFD6;")
        action_layout.addWidget(sep2)

        # Minimize to Floating Bot Icon Button
        self.min_btn = QPushButton(header)
        self.min_btn.setObjectName("headerButton")
        self.min_btn.setIcon(render_svg_icon(SVG_MINUS, 15, color="#71717A", hover_color="#18181B"))
        self.min_btn.setIconSize(QSize(15, 15))
        self.min_btn.setFixedSize(26, 26)
        self.min_btn.setToolTip("Float as Bot Icon")
        self.min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.min_btn.clicked.connect(self.minimize_to_floating)
        action_layout.addWidget(self.min_btn)

        # Close X Button
        self.close_btn = QPushButton(header)
        self.close_btn.setObjectName("headerButton")
        self.close_btn.setIcon(render_svg_icon(SVG_CLOSE, 16, color="#71717A", hover_color="#EF4444"))
        self.close_btn.setIconSize(QSize(16, 16))
        self.close_btn.setFixedSize(26, 26)
        self.close_btn.setToolTip("Hide Sidebar (Ctrl+Alt+H)")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.slide_out)
        action_layout.addWidget(self.close_btn)

        h_layout.addLayout(action_layout)

        return header

    def _build_dashboard_view(self, parent: QWidget) -> QWidget:
        """Page 0: Full Hero Dashboard matching the reference design."""
        scroll = QScrollArea(parent)
        scroll.setObjectName("chatScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        if scroll.viewport():
            scroll.viewport().setStyleSheet("background-color: transparent;")

        content = QWidget()
        content.setObjectName("dashboardContent")
        content.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)

        # 1. Hero Section (Headline + 3D Emblem)
        hero_widget = QWidget(content)
        hero_widget.setObjectName("heroContainer")
        hero_layout = QHBoxLayout(hero_widget)
        hero_layout.setContentsMargins(2, 4, 2, 4)
        hero_layout.setSpacing(10)

        # Left text column
        self.hero_text = HeroHeadlineWidget(hero_widget)
        hero_layout.addWidget(self.hero_text, stretch=1)

        # Right 3D Emblem
        self.hero_3d = Hero3DIllustration(hero_widget)
        hero_layout.addWidget(self.hero_3d, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(hero_widget)

        # 2. Unified Prompt Card (Prompt Input Bar + 4 Quick Action Cards)
        self.prompt_card = PromptInputCard(content)
        self.prompt_card.command_submitted.connect(self._submit_text_command)
        self.prompt_card.voice_toggled.connect(self._handle_mic_click)
        self.prompt_card.attach_requested.connect(self._handle_attach_click)
        layout.addWidget(self.prompt_card)

        # 3. Recent Activity Section
        self.recent_widget = RecentActivityWidget(content)
        self.recent_widget.item_replayed.connect(self._submit_text_command)
        self.recent_widget.see_all_clicked.connect(self._show_chat_view)
        layout.addWidget(self.recent_widget)

        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_chat_view(self, parent: QWidget) -> QWidget:
        """Page 1: Conversation Stream & Result View."""
        container = QWidget(parent)
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(14, 6, 14, 6)
        c_layout.setSpacing(8)

        # Scroll Area for chat messages
        self.scroll_area = QScrollArea(container)
        self.scroll_area.setObjectName("chatScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background-color: transparent; border: none;")
        if self.scroll_area.viewport():
            self.scroll_area.viewport().setStyleSheet("background-color: transparent;")

        self.chat_content = QWidget()
        self.chat_content.setObjectName("chatStreamContainer")
        self.chat_content.setStyleSheet("background-color: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(6, 6, 6, 6)
        self.chat_layout.setSpacing(10)

        # Initial Welcome Greeting Card
        self._add_greeting_card()

        self.chat_layout.addStretch(1)
        self.scroll_area.setWidget(self.chat_content)
        c_layout.addWidget(self.scroll_area, stretch=1)

        # Secondary Input Pill inside Chat Stream
        chat_input_pill = QWidget(container)
        chat_input_pill.setObjectName("promptInputRow")
        cip_layout = QHBoxLayout(chat_input_pill)
        cip_layout.setContentsMargins(8, 4, 6, 4)
        cip_layout.setSpacing(8)

        chat_mic = QPushButton(chat_input_pill)
        chat_mic.setObjectName("headerButton")
        chat_mic.setIcon(render_svg_icon(SVG_VOICE_WAVE, 16, color="#71717A", hover_color="#18181B"))
        chat_mic.setFixedSize(24, 24)
        chat_mic.clicked.connect(self._handle_mic_click)
        cip_layout.addWidget(chat_mic)

        self.chat_input_field = QLineEdit(chat_input_pill)
        self.chat_input_field.setObjectName("heroPromptInput")
        self.chat_input_field.setPlaceholderText("Reply or ask follow-up...")
        self.chat_input_field.returnPressed.connect(self._handle_chat_enter)
        cip_layout.addWidget(self.chat_input_field, stretch=1)

        chat_send = QPushButton(chat_input_pill)
        chat_send.setObjectName("promptSendBtn")
        chat_send.setIcon(render_svg_icon(SVG_ARROW_UP, 16, color="#FFFFFF"))
        chat_send.setFixedSize(30, 30)
        chat_send.clicked.connect(self._handle_chat_enter)
        cip_layout.addWidget(chat_send)

        c_layout.addWidget(chat_input_pill)
        return container

    def _connect_signals(self) -> None:
        self.transcript_updated.connect(self._set_transcript_text)
        self.status_updated.connect(self._set_status_text)
        self.listening_changed.connect(self._set_listening_ui)
        self.dictation_changed.connect(self._set_dictation_ui)

    def _show_dashboard_view(self) -> None:
        self.view_stack.setCurrentIndex(0)
        self.left_rail.set_active_tab("home")
        self.cmd_input = self.prompt_card.input_field
        if hasattr(self, "settings_btn"):
            self.settings_btn.setStyleSheet("")

    def _show_chat_view(self) -> None:
        self.view_stack.setCurrentIndex(1)
        self.left_rail.set_active_tab("chat")
        self.cmd_input = self.chat_input_field
        self.chat_screen_view._scroll_to_bottom()
        if hasattr(self, "settings_btn"):
            self.settings_btn.setStyleSheet("")

    def _show_explore_view(self) -> None:
        self.view_stack.setCurrentIndex(2)
        self.left_rail.set_active_tab("apps")
        self.cmd_input = self.explore_screen_view.input_field
        if hasattr(self, "settings_btn"):
            self.settings_btn.setStyleSheet("")

    def _show_thunder_view(self) -> None:
        self.view_stack.setCurrentIndex(3)
        self.left_rail.set_active_tab("lightning")
        self.cmd_input = self.thunder_screen_view.input_field
        if hasattr(self, "settings_btn"):
            self.settings_btn.setStyleSheet("")

    def _show_files_view(self) -> None:
        self.view_stack.setCurrentIndex(4)
        self.left_rail.set_active_tab("folder")
        self.cmd_input = self.files_screen_view.input_field
        if hasattr(self, "settings_btn"):
            self.settings_btn.setStyleSheet("")

    def _show_history_view(self) -> None:
        self.view_stack.setCurrentIndex(5)
        self.left_rail.set_active_tab("clock")
        self.cmd_input = self.history_screen_view.input_field
        if hasattr(self, "settings_btn"):
            self.settings_btn.setStyleSheet("")

    def _show_settings_view(self) -> None:
        self.view_stack.setCurrentIndex(6)
        self.left_rail.set_active_tab("settings")
        self.cmd_input = self.settings_screen_view.input_field
        if hasattr(self, "settings_btn"):
            self.settings_btn.setStyleSheet("background-color: #ECE7DC; border-radius: 6px;")

    def _show_meeting_view(self) -> None:
        self.view_stack.setCurrentIndex(8)
        self.left_rail.set_active_tab("meeting")
        self.cmd_input = self.meeting_screen_view.input_field
        if hasattr(self, "settings_btn"):
            self.settings_btn.setStyleSheet("")

    def _add_greeting_card(self) -> None:
        card = QWidget(self.chat_content)
        card.setObjectName("greetingCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(9)

        title = QLabel("Hey there!", card)
        title.setObjectName("greetingTitle")
        layout.addWidget(title)

        body = QLabel(
            "Need answers or help with your desktop? I've got you covered!\n\n"
            "Just speak or type what you need, and handless handles it.",
            card,
        )
        body.setObjectName("greetingBody")
        body.setWordWrap(True)
        layout.addWidget(body)

        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(6)
        chips_layout.setContentsMargins(0, 4, 0, 0)

        chip_data = [
            ("Chrome", "open chrome", SVG_BRAND_CHROME, "#2563EB"),
            ("YouTube", "open youtube", SVG_BRAND_YOUTUBE, "#DC2626"),
            ("Snap Left", "snap left", SVG_SNAP, "#7C3AED"),
            ("Google", "go to google.com", SVG_SEARCH, "#059669"),
        ]

        for label, cmd, svg_xml, icon_color in chip_data:
            chip = QPushButton(label, card)
            chip.setObjectName("chipButton")
            chip.setIcon(render_svg_icon(svg_xml, 13, color=icon_color))
            chip.setIconSize(QSize(13, 13))
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda checked=False, c=cmd: self._submit_text_command(c))
            chips_layout.addWidget(chip)

        chips_layout.addStretch(1)
        layout.addLayout(chips_layout)
        self.chat_layout.addWidget(card)

    def add_user_message(self, text: str) -> None:
        """Add right-aligned user speech/text bubble."""
        container = QWidget(self.chat_content)
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 2, 0, 2)
        vbox.setSpacing(4)
        vbox.setAlignment(Qt.AlignmentFlag.AlignRight)

        bubble = QWidget(container)
        bubble.setObjectName("userBubble")
        bubble.setMaximumWidth(int(self._sidebar_width * 0.76))

        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(12, 9, 12, 9)
        lbl = QLabel(text, bubble)
        lbl.setObjectName("userBubbleText")
        lbl.setWordWrap(True)
        b_layout.addWidget(lbl)
        vbox.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignRight)

        toolbar = MessageToolbar(
            text=text,
            on_edit=self._on_edit_message,
            on_retry=self._submit_text_command,
            on_refine=lambda t: self._submit_text_command(f"Explain or optimize: {t}"),
            parent=container,
        )
        vbox.addWidget(toolbar, alignment=Qt.AlignmentFlag.AlignRight)

        self._insert_before_stretch(container)
        self._scroll_to_bottom()

    def add_assistant_message(self, text: str) -> None:
        """Add left-aligned assistant text bubble."""
        bubble = QWidget(self.chat_content)
        bubble.setObjectName("assistantBubble")
        bubble.setMaximumWidth(int(self._sidebar_width * 0.80))

        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(13, 11, 13, 11)
        lbl = QLabel(text, bubble)
        lbl.setObjectName("assistantBubbleText")
        lbl.setWordWrap(True)
        b_layout.addWidget(lbl)

        self._insert_before_stretch(bubble)
        self._scroll_to_bottom()

    def add_action_card(
        self,
        title: str,
        subtitle: str = "Completed action",
        icon_category: str = "file",
        btn_label: str = "download",
        on_action: Optional[Callable[[], None]] = None,
    ) -> None:
        """Add action card with vector SVG icon and record to recent feed."""
        card = ActionCardWidget(
            title=title,
            subtitle=subtitle,
            icon_category=icon_category,
            btn_label=btn_label,
            on_action=on_action,
            parent=self.chat_content,
        )
        card.setMaximumWidth(int(self._sidebar_width * 0.84))
        self._insert_before_stretch(card)
        self._scroll_to_bottom()

        # Update Recent Activity Feed live
        self.recent_widget.add_recent(title, "Just now", "")

    def add_config_proposal_card(self, proposal: Any) -> Any:
        """Add in-chat 1-click self-configuration proposal card."""
        return self.chat_screen_view.add_config_proposal_card(proposal)

    def show_thinking(self, active: bool) -> None:
        """Toggle floating bead thinking animation."""
        if active:
            if self._thinking_widget is None:
                self._thinking_widget = AnimatedThinkingWidget(self.chat_content)
                self._insert_before_stretch(self._thinking_widget)
                self._scroll_to_bottom()
        else:
            if self._thinking_widget is not None:
                self.chat_layout.removeWidget(self._thinking_widget)
                self._thinking_widget.deleteLater()
                self._thinking_widget = None

    def _insert_before_stretch(self, widget: QWidget) -> None:
        count = self.chat_layout.count()
        index = max(0, count - 1)
        self.chat_layout.insertWidget(index, widget)

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def _on_edit_message(self, text: str) -> None:
        self.cmd_input.setText(text)
        self.cmd_input.setFocus()
        self.cmd_input.selectAll()

    def _handle_chat_enter(self) -> None:
        text = self.chat_input_field.text().strip()
        if text:
            self.chat_input_field.clear()
            self._submit_text_command(text)

    def _handle_attach_click(self) -> None:
        """Attach a file or capture screen context."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Attach File to Context", "", "All Files (*.*)")
        if file_path:
            self.add_action_card(f"Attached: {file_path.split('/')[-1]}", "File context added", "file", "✓")
            self.set_status("File attached ✓")

    def _open_status_menu(self) -> None:
        """Dropdown menu for Ready status pill."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #ECE8DE;
                border-radius: 8px;
                padding: 6px;
                color: #18181B;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background: #F4F1EA;
            }
        """)
        menu.addAction("● Ready", lambda: self.set_status("Ready"))
        menu.addAction("⛔ Emergency Stop", self._handle_stop_click)
        menu.addSeparator()
        menu.addAction("Desktop Element Inspector", self._handle_open_inspector)

        pos = self.status_pill.mapToGlobal(QPoint(0, self.status_pill.height() + 4))
        menu.exec(pos)

    def _open_quick_menu(self) -> None:
        """Popup quick actions menu from 9-dot grid button or nav rail."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #ECE8DE;
                border-radius: 8px;
                padding: 6px;
                color: #18181B;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background: #F4F1EA;
            }
        """)

        act_chrome = menu.addAction("Launch Chrome", lambda: self._submit_text_command("open chrome"))
        act_chrome.setIcon(render_svg_icon(SVG_BRAND_CHROME, 14, color="#18181B"))

        act_yt = menu.addAction("Open YouTube", lambda: self._submit_text_command("open youtube"))
        act_yt.setIcon(render_svg_icon(SVG_BRAND_YOUTUBE, 14, color="#DC2626"))

        act_snap = menu.addAction("Snap Window Left", lambda: self._submit_text_command("snap left"))
        act_snap.setIcon(render_svg_icon(SVG_SNAP, 14, color="#7C3AED"))

        act_shot = menu.addAction("Capture Screen", lambda: self._submit_text_command("take a screenshot"))
        act_shot.setIcon(render_svg_icon(SVG_CAPTURE_SCREEN, 14, color="#059669"))

        menu.addSeparator()

        act_inspect = menu.addAction("Desktop Element Inspector", self._handle_open_inspector)
        act_inspect.setIcon(render_svg_icon(SVG_SEARCH, 14, color="#0284C7"))

        act_sett = menu.addAction("Settings", self._handle_settings_click)
        act_sett.setIcon(render_svg_icon(SVG_SETTINGS, 14, color="#52525B"))

        menu.addSeparator()

        act_dock = menu.addAction("⇄ Switch Dock Side (Left / Right)", self.toggle_dock_side)
        act_dock.setIcon(render_svg_icon(SVG_ARROW_LEFT_RIGHT, 14, color="#52525B"))

        act_wide = menu.addAction("⤢ Toggle Wide Mode", self.toggle_wide_mode)
        act_wide.setIcon(render_svg_icon(SVG_EXPAND_HORIZONTAL, 14, color="#52525B"))

        act_float = menu.addAction("― Float on Desktop", self.minimize_to_floating)
        act_float.setIcon(render_svg_icon(SVG_MINUS, 14, color="#52525B"))

        menu.addSeparator()

        act_clear = menu.addAction("Clear Chat History", self.clear_chat)
        act_clear.setIcon(render_svg_icon(SVG_REFRESH, 14, color="#71717A"))

        pos = self.menu_btn.mapToGlobal(QPoint(0, self.menu_btn.height() + 4))
        menu.exec(pos)

    def _open_workflows_menu(self) -> None:
        """Popup workflows and macros menu."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #ECE8DE;
                border-radius: 8px;
                padding: 6px;
                color: #18181B;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background: #F4F1EA;
            }
        """)
        menu.addAction("⚡ Morning Setup", lambda: self._submit_text_command("morning setup"))
        menu.addAction("⚡ Coding Mode", lambda: self._submit_text_command("open vscode and terminal"))
        menu.addAction("⚡ Meeting Mode (Mute + Focus)", lambda: self._submit_text_command("mute audio and close notifications"))
        menu.exec(QCursor.pos())

    def _open_files_menu(self) -> None:
        """Open recent folders / file jumps."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #ECE8DE;
                border-radius: 8px;
                padding: 6px;
                color: #18181B;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background: #F4F1EA;
            }
        """)
        menu.addAction("📁 Open Downloads", lambda: self._submit_text_command("open downloads folder"))
        menu.addAction("📁 Open Screenshots", lambda: self._submit_text_command("open screenshots folder"))
        menu.addAction("📁 Open Documents", lambda: self._submit_text_command("open documents folder"))
        menu.exec(QCursor.pos())

    def _handle_open_inspector(self) -> None:
        if self.on_open_inspector:
            self.on_open_inspector()
        else:
            self._submit_text_command("open element inspector")

    def clear_chat(self) -> None:
        while self.chat_layout.count() > 2:
            item = self.chat_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.show_thinking(False)

    # Signal handlers & UI state synchronization
    def _on_bottom_pill_mode_toggled(self, checked: bool) -> None:
        self.set_dictation_mode(not checked)
        if self.on_dictation_toggled:
            self.on_dictation_toggled(not checked)

    def set_dictation_mode(self, enabled: bool) -> None:
        self.dictation_changed.emit(enabled)

    def _set_dictation_ui(self, enabled: bool) -> None:
        self._is_dictation = enabled
        self.bottom_pill.toggle_switch.set_checked(not enabled)
        if enabled:
            self.prompt_card.input_field.setPlaceholderText("Dictation Mode: Speak to type directly into active app...")
            self.chat_input_field.setPlaceholderText("Dictation Mode active...")
            self.pill_text.setText("Dictating")
            self.pill_dot.setStyleSheet("color: #10B981; font-size: 10px;")
        else:
            self.prompt_card.input_field.setPlaceholderText("Tell Handless what to do...")
            self.chat_input_field.setPlaceholderText("Reply or ask follow-up...")
            self.pill_text.setText("Ready")
            self.pill_dot.setStyleSheet("color: #10B981; font-size: 10px;")

    def _handle_mic_click(self) -> None:
        new_state = not self._is_listening
        self.set_listening(new_state)
        if self.on_mic_toggled:
            self.on_mic_toggled(new_state)

    def _handle_stop_click(self) -> None:
        if emergency_stop.is_stopped():
            emergency_stop.reset()
            self.set_status("Ready ✓")
        else:
            emergency_stop.trigger(reason="Sidebar Stop Action")
            self.set_status("Stopped")
            if self.on_emergency_stop:
                self.on_emergency_stop()

    def _handle_settings_click(self) -> None:
        if self.view_stack.currentIndex() == 6:
            self._show_dashboard_view()
        else:
            self._show_settings_view()

    # Live Voice Call Controls (Gemini 3.8 Live)
    def start_live_call(self) -> None:
        """Switch to Page 7 and begin live conversational call."""
        self._is_live_call_active = True
        self.call_btn.setIcon(render_svg_icon(SVG_PHONE_OFF, 14, color="#EF4444"))
        self.call_btn.setToolTip("End Live Voice Call")
        self.view_stack.setCurrentIndex(7)
        self.live_call_view.start_call_timer()
        self.live_call_toggled.emit(True)

    def end_live_call(self) -> None:
        """End live call and return to dashboard."""
        self._is_live_call_active = False
        self.call_btn.setIcon(render_svg_icon(SVG_PHONE, 14, color="#10B981"))
        self.call_btn.setToolTip("Start Live Voice Call (Gemini 3.8 Live)")
        self.live_call_view.stop_call_timer()
        self.view_stack.setCurrentIndex(0)
        self.live_call_toggled.emit(False)

    def toggle_live_call(self) -> None:
        """Toggle live call session on or off."""
        if getattr(self, "_is_live_call_active", False) or self.view_stack.currentIndex() == 7:
            self.end_live_call()
        else:
            self.start_live_call()

    # Screen Docking, Wide Mode, Auto-Fit, and Window Mobility
    def auto_fit_to_side(self, side: Optional[str] = None, animated: bool = True) -> None:
        """Auto-fit and adjust sidebar along the chosen or nearest screen edge."""
        if side in ("left", "right"):
            self._dock_side = side
            self.dock_side_changed.emit(side)
            self._reposition(animated=animated)
        else:
            self._snap_to_nearest_edge(animated=animated)

    def _snap_to_nearest_edge(self, animated: bool = True) -> None:
        """Auto-fit and snap sidebar smoothly to the nearest screen edge (left or right)."""
        cur_geom = self.geometry()
        center_pt = cur_geom.center()
        screen = (
            QApplication.screenAt(center_pt)
            or QApplication.screenAt(QCursor.pos())
            or QApplication.primaryScreen()
        )
        if not screen:
            return

        avail = screen.availableGeometry()
        screen_mid_x = avail.x() + (avail.width() // 2)

        # Determine dock side based on window center relative to screen center
        target_side = "right" if center_pt.x() >= screen_mid_x else "left"
        old_side = self._dock_side
        self._dock_side = target_side

        if old_side != target_side:
            self.dock_side_changed.emit(target_side)

        margin_x = 12
        margin_y = 10
        min_w = self.minimumSizeHint().width()
        w = max(640, min_w + 160) if self._is_wide_mode else max(self._sidebar_width, min_w)
        max_allowed_w = max(360, int(avail.width() * 0.90))
        w = min(w, max_allowed_w)
        h = max(480, avail.height() - (margin_y * 2))
        y = avail.y() + margin_y

        self.resize(w, h)
        actual_w = max(w, self.width())
        if actual_w > max_allowed_w:
            actual_w = max_allowed_w
            self.setFixedWidth(actual_w)

        if target_side == "left":
            x = avail.x() + margin_x
            off_x = avail.x() - actual_w - 40
        else:
            x = avail.x() + avail.width() - actual_w - margin_x
            off_x = avail.x() + avail.width() + 40

        # Guardrails: strictly guarantee the window stays completely within visible screen borders
        if x + actual_w > avail.x() + avail.width() - margin_x:
            x = avail.x() + avail.width() - actual_w - margin_x
        if x < avail.x() + margin_x:
            x = avail.x() + margin_x

        target_rect = QRect(x, y, actual_w, h)
        self._target_rect = target_rect
        self._offscreen_rect = QRect(off_x, y, actual_w, h)

        if not self.isVisible():
            self.setGeometry(target_rect)
            return

        if animated:
            if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
                self._anim.stop()
            self._anim = QPropertyAnimation(self, b"geometry")
            self._anim.setDuration(240)
            self._anim.setStartValue(cur_geom)
            self._anim.setEndValue(target_rect)
            self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anim.finished.connect(self._ensure_within_screen_bounds)
            self._anim.start()
        else:
            self.setGeometry(target_rect)
            self._ensure_within_screen_bounds()

    def dock_to_left(self, animated: bool = True) -> None:
        """Dock sidebar smoothly to the left edge of the screen."""
        self._dock_side = "left"
        self.dock_side_changed.emit("left")
        self._reposition(animated=animated)

    def dock_to_right(self, animated: bool = True) -> None:
        """Dock sidebar smoothly to the right edge of the screen."""
        self._dock_side = "right"
        self.dock_side_changed.emit("right")
        self._reposition(animated=animated)

    def toggle_dock_side(self, animated: bool = True) -> None:
        """Switch between left and right screen dock positions."""
        if self._dock_side == "right":
            self.dock_to_left(animated=animated)
        else:
            self.dock_to_right(animated=animated)

    def set_wide_mode(self, wide: bool, animated: bool = True) -> None:
        """Toggle between wide/full-width mode and standard width."""
        if self._is_wide_mode == wide:
            return
        self._is_wide_mode = wide
        self._reposition(animated=animated)

    def toggle_wide_mode(self, animated: bool = True) -> None:
        """Toggle wide mode on/off."""
        self.set_wide_mode(not self._is_wide_mode, animated=animated)

    def minimize_to_floating(self) -> None:
        """Smoothly shrink down to the floating bot logo tile."""
        self.slide_out()

    def _reposition(self, animated: bool = True) -> None:
        """Recalculate geometry and animate to target rect."""
        old_geom = self.geometry()
        self._calculate_dimensions()
        target = self._target_rect
        if not self.isVisible():
            self.setGeometry(target)
            return
        if animated:
            if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
                self._anim.stop()
            self._anim = QPropertyAnimation(self, b"geometry")
            self._anim.setDuration(260)
            self._anim.setStartValue(old_geom)
            self._anim.setEndValue(target)
            self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anim.start()
        else:
            self.setGeometry(target)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Handle dragging from header and nav rail, plus double-click wide toggle."""
        header_widget = getattr(self, "header", None)
        rail_widget = getattr(self, "left_rail", None)
        if watched in (header_widget, rail_widget):
            ev_type = event.type()
            if ev_type == QEvent.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.LeftButton and watched == header_widget:
                    self.toggle_wide_mode()
                    return True
            elif ev_type == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    child = watched.childAt(event.position().toPoint())
                    if not isinstance(child, (QPushButton, QComboBox, QLineEdit, QTextEdit)):
                        self._is_dragging = True
                        self._drag_start_global = event.globalPosition().toPoint()
                        self._drag_pos = self._drag_start_global - self.frameGeometry().topLeft()
                        return False
            elif ev_type == QEvent.Type.MouseMove:
                if self._is_dragging and not self._drag_pos.isNull() and (event.buttons() & Qt.MouseButton.LeftButton):
                    curr_pos = event.globalPosition().toPoint()
                    if (curr_pos - self._drag_start_global).manhattanLength() > 4:
                        new_pos = curr_pos - self._drag_pos
                        screen = (
                            QApplication.screenAt(curr_pos)
                            or QApplication.screenAt(self.geometry().center())
                            or QApplication.primaryScreen()
                        )
                        if screen:
                            avail = screen.availableGeometry()
                            clamped_x = max(avail.x() + 4, min(new_pos.x(), avail.x() + avail.width() - self.width() - 4))
                            clamped_y = max(avail.y() + 4, min(new_pos.y(), avail.y() + avail.height() - self.height() - 4))
                            self.move(clamped_x, clamped_y)
                        else:
                            self.move(new_pos)
                        return True
            elif ev_type == QEvent.Type.MouseButtonRelease:
                if self._is_dragging:
                    self._is_dragging = False
                    curr_pos = event.globalPosition().toPoint()
                    did_drag = (curr_pos - self._drag_start_global).manhattanLength() > 6
                    self._drag_pos = QPoint()
                    if did_drag:
                        self._snap_to_nearest_edge(animated=True)
                        return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 80:
            self._is_dragging = True
            self._drag_start_global = event.globalPosition().toPoint()
            self._drag_pos = self._drag_start_global - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._is_dragging and not self._drag_pos.isNull() and (event.buttons() & Qt.MouseButton.LeftButton):
            curr_pos = event.globalPosition().toPoint()
            if hasattr(self, "_drag_start_global") and (curr_pos - self._drag_start_global).manhattanLength() > 4:
                self.move(curr_pos - self._drag_pos)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._is_dragging:
            self._is_dragging = False
            curr_pos = event.globalPosition().toPoint()
            did_drag = hasattr(self, "_drag_start_global") and (curr_pos - self._drag_start_global).manhattanLength() > 6
            self._drag_pos = QPoint()
            if did_drag:
                self._snap_to_nearest_edge(animated=True)
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def set_listening(self, active: bool) -> None:
        if active and emergency_stop.is_stopped():
            emergency_stop.reset()
        self.listening_changed.emit(active)

    def set_transcript(self, text: str) -> None:
        self.transcript_updated.emit(text)

    def set_status(self, text: str) -> None:
        self.status_updated.emit(text)

    def _set_listening_ui(self, active: bool) -> None:
        self._is_listening = active
        self.bottom_pill.set_listening_state(active)
        if active:
            self.pill_text.setText("Listening...")
            self.pill_dot.setStyleSheet("color: #10B981; font-size: 10px;")
            self.show_thinking(True)
        else:
            if self.pill_text.text() == "Listening...":
                self.pill_text.setText("Processing...")

    def _submit_text_command(self, text: str) -> None:
        if not text:
            return
        if emergency_stop.is_stopped():
            emergency_stop.reset()

        self._show_chat_view()
        self.add_user_message(text)
        self.show_thinking(True)
        self.set_status("Processing command...")

        # Record to recent feed immediately
        self.recent_widget.add_recent(text, "Just now", text)

        if self.on_command_submitted:
            self.on_command_submitted(text)

    def _set_transcript_text(self, text: str) -> None:
        if text:
            self.prompt_card.input_field.setText(text)
            self.chat_input_field.setText(text)

    def _set_status_text(self, text: str) -> None:
        self.pill_text.setText(text)
        if "Done" in text or "✓" in text or "Success" in text or "Pasted" in text:
            self.show_thinking(False)
            self.pill_dot.setStyleSheet("color: #10B981; font-size: 10px;")
            QTimer.singleShot(2500, self._reset_to_ready)
        elif "Error" in text or "Didn't understand" in text:
            self.show_thinking(False)
            self.pill_dot.setStyleSheet("color: #EF4444; font-size: 10px;")

    def _reset_to_ready(self) -> None:
        if not self._is_listening:
            self.pill_text.setText("Dictating" if self._is_dictation else "Ready")
            self.pill_dot.setStyleSheet("color: #10B981; font-size: 10px;")

    # Slide Animations
    def toggle_sidebar(self) -> None:
        if self.isVisible():
            self.slide_out()
        else:
            self.slide_in()

    def slide_in(self) -> None:
        self._calculate_dimensions()
        self.move(self._offscreen_rect.topLeft())
        self.show()
        self.raise_()
        self.activateWindow()

        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()

        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(260)
        self._anim.setStartValue(QRect(self._offscreen_rect.topLeft(), self.size()))
        self._anim.setEndValue(self._target_rect)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self._ensure_within_screen_bounds)
        self._anim.start()
        self._is_visible_state = True

    def slide_out(self) -> None:
        self._calculate_dimensions()
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(220)
        self._anim.setStartValue(self.pos())
        self._anim.setEndValue(self._offscreen_rect.topLeft())
        self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim.finished.connect(self._on_slide_out_finished)
        self._anim.start()
        self._is_visible_state = False

    def _on_slide_out_finished(self) -> None:
        self.hide()
        if self._anim:
            try:
                self._anim.finished.disconnect(self._on_slide_out_finished)
            except Exception:
                pass
        self.closed_to_floating.emit()
