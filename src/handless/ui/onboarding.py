"""First-run setup for Vyoma Handless.

A calm, step-by-step window shown the first time Handless starts (and again from
the tray menu). It walks the user through everything the app needs from Windows:

1. Welcome
2. Microphone: checks the Windows privacy switch, opens the right Settings page,
   and runs a live level test so the user knows they are heard.
3. Screen & safety: screen understanding and confirmation preferences.
4. AI keys: optional Groq / Gemini keys, stored in Windows Credential Manager.
5. Startup: launch at sign-in and where the sidebar docks.
6. All set: the shortcuts that matter.

Windows does not let an app grant itself microphone access, so step 2 guides the
user to the switch rather than changing it silently.
"""

from __future__ import annotations

import logging
import math
import os
from array import array
import subprocess
import sys
import threading
import webbrowser
from typing import Callable, List, Optional

from PySide6.QtCore import QObject, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from handless.config import AppConfig, save_config
from handless.ui.icons import (
    SVG_CHECK_CIRCLE,
    SVG_EYE,
    SVG_KEYBOARD,
    SVG_LOCK,
    SVG_MIC,
    SVG_ROCKET,
    SVG_SHIELD,
    get_bot_logo_pixmap,
    render_svg_pixmap,
)

logger = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "VyomaHandless"
MIC_CONSENT_KEY = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"

INK = "#18181B"
MUTED = "#71717A"
PAPER = "#FAF9F5"
LINE = "#ECE7DC"
GOOD = "#047857"
WARN = "#B45309"

QSS = f"""
QDialog {{ background: transparent; }}
QLabel {{ color: {INK}; background: transparent; border: none; }}
QLabel#title {{ font-family: 'Playfair Display', Georgia, serif; font-size: 26px; font-weight: 700; }}
QLabel#body {{ color: #52525B; font-size: 13px; }}
QLabel#small {{ color: {MUTED}; font-size: 11.5px; }}
QLabel#stepLabel {{ color: {MUTED}; font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
QFrame#card {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 14px; }}
QPushButton#primary {{
    background: {INK}; color: #FFFFFF; border: none; border-radius: 19px;
    padding: 0 26px; min-height: 38px; font-size: 13px; font-weight: 600;
}}
QPushButton#primary:hover {{ background: #27272A; }}
QPushButton#primary:disabled {{ background: #A1A1AA; }}
QPushButton#ghost {{
    background: transparent; color: #52525B; border: none; padding: 0 14px;
    min-height: 38px; font-size: 13px; font-weight: 500;
}}
QPushButton#ghost:hover {{ color: {INK}; }}
QPushButton#secondary {{
    background: {PAPER}; color: {INK}; border: 1px solid #E2DED2; border-radius: 15px;
    padding: 0 16px; min-height: 30px; font-size: 12px; font-weight: 600;
}}
QPushButton#secondary:hover {{ background: #F1EEE5; }}
QPushButton#close {{ background: transparent; border: none; color: {MUTED}; font-size: 16px; }}
QPushButton#close:hover {{ color: {INK}; }}
QLineEdit {{
    background: {PAPER}; border: 1px solid #E2DED2; border-radius: 10px;
    padding: 8px 10px; font-size: 12.5px; color: {INK};
}}
QLineEdit:focus {{ border-color: {INK}; background: #FFFFFF; }}
QCheckBox {{ font-size: 12.5px; color: {INK}; spacing: 10px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid #C9C4B6; background: #FFFFFF; }}
QCheckBox::indicator:checked {{ background: {INK}; border-color: {INK}; image: url(__CHECK_SVG__); }}
QProgressBar {{ background: #EFECE3; border: none; border-radius: 4px; max-height: 8px; }}
QProgressBar::chunk {{ background: {INK}; border-radius: 4px; }}
"""


_CHECK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" '
    'stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'
)


def _stylesheet() -> str:
    """QSS with the checkbox tick written to a file (QSS cannot embed SVG data)."""
    import tempfile

    path = os.path.join(tempfile.gettempdir(), "vyoma-handless-check.svg")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(_CHECK_SVG)
    except OSError:
        return QSS.replace(" image: url(__CHECK_SVG__);", "")
    return QSS.replace("__CHECK_SVG__", path.replace("\\", "/"))


# ---------------------------------------------------------------------------
# Windows helpers
# ---------------------------------------------------------------------------

def _read_reg_str(root, path: str, name: str) -> Optional[str]:
    try:
        import winreg

        with winreg.OpenKey(root, path) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value)
    except OSError:
        return None


def microphone_privacy_state() -> str:
    """Return "allowed", "blocked" or "unknown" for desktop-app microphone access."""
    if sys.platform != "win32":
        return "unknown"
    import winreg

    checks = [
        (winreg.HKEY_LOCAL_MACHINE, MIC_CONSENT_KEY),
        (winreg.HKEY_CURRENT_USER, MIC_CONSENT_KEY),
        (winreg.HKEY_CURRENT_USER, MIC_CONSENT_KEY + r"\NonPackaged"),
    ]
    seen = False
    for root, path in checks:
        value = _read_reg_str(root, path, "Value")
        if value is None:
            continue
        seen = True
        if value.lower() == "deny":
            return "blocked"
    return "allowed" if seen else "unknown"


def open_microphone_settings() -> None:
    try:
        os.startfile("ms-settings:privacy-microphone")  # noqa: S606
    except OSError:
        logger.warning("Could not open Windows microphone privacy settings.")


def launch_command() -> str:
    """Command line Windows should run at sign-in."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --background'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pythonw if os.path.exists(pythonw) else sys.executable
    return f'"{exe}" -m handless.app --background'


def is_launch_at_startup_enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    return _read_reg_str(winreg.HKEY_CURRENT_USER, RUN_KEY, RUN_VALUE) is not None


def set_launch_at_startup(enabled: bool) -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, launch_command())
            else:
                try:
                    winreg.DeleteValue(key, RUN_VALUE)
                except FileNotFoundError:
                    pass
        return True
    except OSError as exc:
        logger.error("Could not update launch-at-startup setting: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Microphone level test
# ---------------------------------------------------------------------------

class _MicTester(QObject):
    """Records a short sample on a worker thread and reports the input level."""

    level = Signal(float)
    finished = Signal(bool, str)  # heard, message

    def __init__(self, device_index: int = -1) -> None:
        super().__init__()
        self.device_index = device_index

    def start(self, seconds: float = 3.0) -> None:
        threading.Thread(target=self._run, args=(seconds,), daemon=True).start()

    def _run(self, seconds: float) -> None:
        try:
            import sounddevice as sd
        except Exception as exc:  # pragma: no cover - packaging problem
            self.finished.emit(False, f"Audio library unavailable: {exc}")
            return

        peak = 0.0
        try:
            device = None if self.device_index < 0 else self.device_index
            block = 1600
            with sd.RawInputStream(samplerate=16000, channels=1, dtype="int16", device=device, blocksize=block) as stream:
                for _ in range(int(seconds * 16000 / block)):
                    data, _ = stream.read(block)
                    samples = array("h", bytes(data))
                    rms = math.sqrt(sum(x * x for x in samples) / len(samples)) / 32768 if samples else 0.0
                    level = min(1.0, rms * 12)
                    peak = max(peak, level)
                    self.level.emit(level)
        except Exception as exc:
            msg = str(exc)
            if "Invalid device" in msg or "-9996" in msg or "Error opening" in msg:
                msg = "No microphone found. Plug one in or check the privacy switch below."
            self.finished.emit(False, msg)
            return
        self.level.emit(0.0)
        if peak > 0.08:
            self.finished.emit(True, "We can hear you clearly.")
        elif peak > 0.0:
            self.finished.emit(False, "Very quiet. Speak closer, or turn the input volume up in Sound settings.")
        else:
            self.finished.emit(False, "Only silence came through. Windows may be blocking the microphone.")


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

def _icon_label(svg: str, size: int = 22, color: str = INK) -> QLabel:
    lbl = QLabel()
    lbl.setPixmap(render_svg_pixmap(svg, size, size, color=color))
    lbl.setFixedSize(size + 2, size + 2)
    return lbl


def _text(text: str, name: str = "body", wrap: bool = True) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName(name)
    lbl.setWordWrap(wrap)
    lbl.setTextFormat(Qt.TextFormat.RichText)
    lbl.setOpenExternalLinks(True)
    return lbl


def _card() -> tuple:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(10)
    return frame, layout


class _Page(QWidget):
    def __init__(self, step: str, title: str, body: str, icon_svg: Optional[str] = None) -> None:
        super().__init__()
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(12)

        if step:
            self.layout_.addWidget(_text(step.upper(), "stepLabel"))
        head = QHBoxLayout()
        head.setSpacing(12)
        if icon_svg:
            head.addWidget(_icon_label(icon_svg, 26), alignment=Qt.AlignmentFlag.AlignVCenter)
        title_lbl = _text(title, "title")
        head.addWidget(title_lbl, stretch=1)
        self.layout_.addLayout(head)
        if body:
            self.layout_.addWidget(_text(body))
        self.layout_.addSpacing(6)

    def add(self, widget: QWidget) -> None:
        self.layout_.addWidget(widget)

    def finish(self) -> None:
        self.layout_.addStretch(1)


class _StepDots(QWidget):
    def __init__(self, count: int) -> None:
        super().__init__()
        self.count = count
        self.current = 0
        self.setFixedHeight(10)
        self.setFixedWidth(count * 22)

    def set_current(self, index: int) -> None:
        self.current = index
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        x = 0
        for i in range(self.count):
            width = 18 if i == self.current else 6
            color = QColor(INK) if i <= self.current else QColor("#D9D5C9")
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, 2, width, 6, 3, 3)
            x += width + 6
        p.end()


# ---------------------------------------------------------------------------
# Wizard
# ---------------------------------------------------------------------------

class OnboardingWizard(QDialog):
    """Six-step first-run setup. ``exec()`` returns Accepted when finished."""

    def __init__(self, config: AppConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.config = config
        self._drag_pos: Optional[QPoint] = None
        self._mic_tester: Optional[_MicTester] = None

        self.setWindowTitle("Set up Vyoma Handless")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(_stylesheet())
        self.setFixedSize(600, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)

        self.sheet = QFrame(self)
        self.sheet.setObjectName("sheet")
        self.sheet.setStyleSheet(f"QFrame#sheet {{ background: {PAPER}; border: 1px solid #E6E1D4; border-radius: 22px; }}")
        shadow = QGraphicsDropShadowEffect(self.sheet)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(24, 24, 27, 40))
        self.sheet.setGraphicsEffect(shadow)
        root.addWidget(self.sheet)

        sheet_layout = QVBoxLayout(self.sheet)
        sheet_layout.setContentsMargins(40, 22, 40, 26)
        sheet_layout.setSpacing(0)

        # Top bar: brand + close
        top = QHBoxLayout()
        logo = QLabel()
        pix = get_bot_logo_pixmap(without_bg=True, size=26)
        if not pix.isNull():
            logo.setPixmap(pix)
        top.addWidget(logo)
        top.addSpacing(8)
        brand = QLabel("Vyoma Handless")
        brand.setStyleSheet("font-size: 13px; font-weight: 700;")
        top.addWidget(brand)
        top.addStretch(1)
        close_btn = QPushButton("✕")
        close_btn.setObjectName("close")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("Skip setup")
        close_btn.clicked.connect(self._skip)
        top.addWidget(close_btn)
        sheet_layout.addLayout(top)
        sheet_layout.addSpacing(26)

        self.stack = QStackedWidget()
        sheet_layout.addWidget(self.stack, stretch=1)

        self._pages: List[QWidget] = [
            self._build_welcome(),
            self._build_microphone(),
            self._build_screen(),
            self._build_keys(),
            self._build_startup(),
            self._build_done(),
        ]
        for page in self._pages:
            self.stack.addWidget(page)

        # Bottom bar: dots + back/continue
        sheet_layout.addSpacing(18)
        bottom = QHBoxLayout()
        self.dots = _StepDots(len(self._pages))
        bottom.addWidget(self.dots, alignment=Qt.AlignmentFlag.AlignVCenter)
        bottom.addStretch(1)
        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("ghost")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self._back)
        bottom.addWidget(self.back_btn)
        self.next_btn = QPushButton("Get started")
        self.next_btn.setObjectName("primary")
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setDefault(True)
        self.next_btn.clicked.connect(self._next)
        bottom.addWidget(self.next_btn)
        sheet_layout.addLayout(bottom)

        self._go(0)

    # -- pages ---------------------------------------------------------------

    def _build_welcome(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(14)
        layout.addStretch(1)

        logo = QLabel()
        pix = get_bot_logo_pixmap(without_bg=True, size=104)
        if not pix.isNull():
            logo.setPixmap(pix)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        title = _text("Your desktop,<br>without <i>hands.</i>", "title")
        title.setStyleSheet("font-size: 34px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        body = _text(
            "Speak naturally and Handless opens apps, types for you, and handles the busywork.<br>"
            "Setup takes about a minute. We'll ask only for what Handless needs."
        )
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(body)
        layout.addStretch(2)
        return page

    def _build_microphone(self) -> QWidget:
        page = _Page(
            "Step 1 of 4",
            "Let Handless hear you",
            "Your voice is how you talk to Handless. Audio is captured only while you hold a shortcut.",
            SVG_MIC,
        )

        card, c = _card()
        self.mic_state_lbl = _text("", "body")
        c.addWidget(self.mic_state_lbl)
        settings_btn = QPushButton("Open microphone privacy settings")
        settings_btn.setObjectName("secondary")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.clicked.connect(open_microphone_settings)
        c.addWidget(settings_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        page.add(card)

        test_card, t = _card()
        t.addWidget(_text("<b>Test your microphone</b><br>Press test, then say a few words.", "body"))
        self.mic_level = QProgressBar()
        self.mic_level.setRange(0, 100)
        self.mic_level.setValue(0)
        self.mic_level.setTextVisible(False)
        t.addWidget(self.mic_level)
        row = QHBoxLayout()
        self.mic_test_btn = QPushButton("Test microphone")
        self.mic_test_btn.setObjectName("secondary")
        self.mic_test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_test_btn.clicked.connect(self._run_mic_test)
        row.addWidget(self.mic_test_btn)
        self.mic_result_lbl = _text("", "small")
        row.addWidget(self.mic_result_lbl, stretch=1)
        t.addLayout(row)
        page.add(test_card)

        page.finish()
        return page

    def _build_screen(self) -> QWidget:
        page = _Page(
            "Step 2 of 4",
            "Screen & safety",
            "Handless reads the controls on screen through Windows UI Automation to click and type for you. "
            "Nothing is recorded in the background.",
            SVG_EYE,
        )
        card, c = _card()
        self.vision_cb = QCheckBox("Use screenshots when a control can't be found")
        self.vision_cb.setChecked(self.config.ai.enable_vision_fallback)
        c.addWidget(self.vision_cb)
        c.addWidget(_text("A screenshot of the active window is sent to your AI provider only for that request.", "small"))
        c.addSpacing(6)
        self.confirm_cb = QCheckBox("Ask me before shutting down, deleting or closing things")
        self.confirm_cb.setChecked(self.config.safety.confirm_destructive_actions)
        c.addWidget(self.confirm_cb)
        page.add(card)

        stop_card, s = _card()
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(_icon_label(SVG_SHIELD, 20), alignment=Qt.AlignmentFlag.AlignTop)
        row.addWidget(_text("<b>Emergency stop</b><br>Press <b>Ctrl + Shift + Q</b> or tap <b>Esc</b> twice to halt any action instantly.", "body"), stretch=1)
        s.addLayout(row)
        page.add(stop_card)
        page.finish()
        return page

    def _build_keys(self) -> QWidget:
        page = _Page(
            "Step 3 of 4",
            "Connect your AI",
            "Optional, but recommended. Keys are stored encrypted in Windows Credential Manager, never in a file.",
            SVG_LOCK,
        )
        from handless.security.credentials import has_gemini_api_key, has_groq_api_key

        card, c = _card()
        c.addWidget(_text(
            "<b>Groq</b> &nbsp;<span style='color:#71717A'>fast speech-to-text and chat</span><br>"
            "<a style='color:#18181B' href='https://console.groq.com/keys'>Get a free key at console.groq.com</a>",
            "body",
        ))
        self.groq_input = QLineEdit()
        self.groq_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_input.setPlaceholderText("Already saved, leave blank to keep" if has_groq_api_key() else "gsk_...")
        c.addWidget(self.groq_input)
        page.add(card)

        card2, c2 = _card()
        c2.addWidget(_text(
            "<b>Google Gemini</b> &nbsp;<span style='color:#71717A'>screen understanding and live voice</span><br>"
            "<a style='color:#18181B' href='https://aistudio.google.com/apikey'>Get a free key at aistudio.google.com</a>",
            "body",
        ))
        self.gemini_input = QLineEdit()
        self.gemini_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_input.setPlaceholderText("Already saved, leave blank to keep" if has_gemini_api_key() else "AIza...")
        c2.addWidget(self.gemini_input)
        page.add(card2)

        self.keys_note = _text("Without keys, Handless still runs common commands offline.", "small")
        page.add(self.keys_note)
        page.finish()
        return page

    def _build_startup(self) -> QWidget:
        page = _Page(
            "Step 4 of 4",
            "Make it yours",
            "Choose how Handless fits into your day. You can change these later in Settings.",
            SVG_ROCKET,
        )
        card, c = _card()
        self.startup_cb = QCheckBox("Start Handless when I sign in to Windows")
        self.startup_cb.setChecked(is_launch_at_startup_enabled() or not self.config.ui.onboarding_completed)
        c.addWidget(self.startup_cb)
        c.addWidget(_text("It starts quietly as a small floating button.", "small"))
        c.addSpacing(6)
        self.dock_left_cb = QCheckBox("Dock the sidebar on the left side of the screen")
        self.dock_left_cb.setChecked(self.config.ui.sidebar_position == "left")
        c.addWidget(self.dock_left_cb)
        page.add(card)
        page.finish()
        return page

    def _build_done(self) -> QWidget:
        page = _Page("", "You're all set", "Here are the shortcuts that matter. Try one now.", SVG_CHECK_CIRCLE)
        card, c = _card()
        shortcuts = [
            ("Ctrl + Space", "Hold and speak a command"),
            ("Hold Ctrl + Shift", "Dictate text at your cursor"),
            ("Win + Shift + Space", "Ask about anything on screen"),
            ("Ctrl + Alt + H", "Show or hide the sidebar"),
            ("Ctrl + Shift + Q", "Emergency stop"),
        ]
        for keys, desc in shortcuts:
            row = QHBoxLayout()
            row.setSpacing(14)
            key_lbl = QLabel(keys)
            key_lbl.setStyleSheet(
                f"background: {PAPER}; border: 1px solid #E2DED2; border-radius: 7px; padding: 4px 9px;"
                "font-size: 11.5px; font-weight: 700;"
            )
            key_lbl.setFixedWidth(150)
            key_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(key_lbl)
            row.addWidget(_text(desc, "body"), stretch=1)
            c.addLayout(row)
        page.add(card)
        tip = QHBoxLayout()
        tip.addWidget(_icon_label(SVG_KEYBOARD, 18, MUTED))
        tip.addWidget(_text("Find Handless any time in the system tray, next to the clock.", "small"), stretch=1)
        page.layout_.addLayout(tip)
        page.finish()
        return page

    # -- navigation ----------------------------------------------------------

    def _go(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.dots.set_current(index)
        last = len(self._pages) - 1
        self.back_btn.setVisible(0 < index < last)
        labels = {0: "Get started", last: "Launch Handless"}
        self.next_btn.setText(labels.get(index, "Continue"))
        if index == 1:
            self._refresh_mic_state()

    def _back(self) -> None:
        self._go(max(0, self.stack.currentIndex() - 1))

    def _next(self) -> None:
        index = self.stack.currentIndex()
        if index == 3 and not self._save_keys():
            return
        if index == len(self._pages) - 1:
            self._finish()
            return
        self._go(index + 1)

    def _skip(self) -> None:
        self.config.ui.onboarding_completed = True
        save_config(self.config)
        self.reject()

    def _finish(self) -> None:
        self.config.ai.enable_vision_fallback = self.vision_cb.isChecked()
        self.config.safety.confirm_destructive_actions = self.confirm_cb.isChecked()
        self.config.ui.sidebar_position = "left" if self.dock_left_cb.isChecked() else "right"
        self.config.ui.onboarding_completed = True
        save_config(self.config)
        set_launch_at_startup(self.startup_cb.isChecked())
        self.accept()

    # -- step logic ----------------------------------------------------------

    MIC_TEXT_WIDTH = 440

    def _refresh_mic_state(self) -> None:
        state = microphone_privacy_state()
        if state == "blocked":
            self.mic_state_lbl.setText(
                f"<span style='color:{WARN}'><b>Windows is blocking microphone access.</b></span><br>"
                "Turn on <b>Microphone access</b> and <b>Let desktop apps access your microphone</b>, then come back."
            )
        elif state == "allowed":
            self.mic_state_lbl.setText(
                f"<span style='color:{GOOD}'><b>Microphone access is on.</b></span><br>"
                "Windows lets desktop apps like Handless use your microphone."
            )
        else:
            self.mic_state_lbl.setText(
                "Make sure <b>Microphone access</b> and <b>Let desktop apps access your microphone</b> are on in Windows Settings."
            )
        # Rich, word-wrapped labels are not re-measured on setText; reserve the wrapped height
        self.mic_state_lbl.setMinimumHeight(self.mic_state_lbl.heightForWidth(self.MIC_TEXT_WIDTH))

    def _run_mic_test(self) -> None:
        self.mic_test_btn.setEnabled(False)
        self.mic_test_btn.setText("Listening…")
        self.mic_result_lbl.setText("Say something like “open Chrome”.")
        self.mic_result_lbl.setStyleSheet("")
        self._mic_tester = _MicTester(self.config.voice.device_index)
        self._mic_tester.level.connect(lambda v: self.mic_level.setValue(int(v * 100)))
        self._mic_tester.finished.connect(self._on_mic_test_done)
        self._mic_tester.start()

    def _on_mic_test_done(self, heard: bool, message: str) -> None:
        self.mic_test_btn.setEnabled(True)
        self.mic_test_btn.setText("Test again")
        color = GOOD if heard else WARN
        self.mic_result_lbl.setStyleSheet(f"color: {color}; font-weight: 600;")
        self.mic_result_lbl.setText(("✓  " if heard else "") + message)
        self._refresh_mic_state()

    def _save_keys(self) -> bool:
        from handless.security.credentials import store_gemini_api_key, store_groq_api_key

        groq = self.groq_input.text().strip()
        gemini = self.gemini_input.text().strip()
        problems = []
        if groq:
            if not store_groq_api_key(groq):
                problems.append("Groq")
            else:
                self.config.voice.stt_engine = "groq_whisper"
        if gemini and not store_gemini_api_key(gemini):
            problems.append("Gemini")
        if problems:
            self.keys_note.setStyleSheet(f"color: {WARN}; font-weight: 600;")
            self.keys_note.setText(f"Couldn't save the {' and '.join(problems)} key to Credential Manager. Try again.")
            return False
        return True

    # -- frameless window dragging -------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._drag_pos = None

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            return  # Esc should not silently dismiss setup; use the close button
        super().keyPressEvent(event)


def should_run_onboarding(config: AppConfig, argv: List[str]) -> bool:
    if "--setup" in argv:
        return True
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("HANDLESS_SKIP_ONBOARDING"):
        return False
    return not config.ui.onboarding_completed
