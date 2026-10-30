"""Render high-resolution screenshots of all sidebar screens and floating widget to the artifact directory."""

import os
import sys

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from handless.ui.floating_widget import FloatingCopilotWidget
from handless.ui.sidebar import SidebarWindow

ARTIFACT_DIR = r"C:\Users\USER\.gemini\antigravity\brain\78f612f1-8d30-4ff4-841f-c8194e0ecbb3"


def render_all_screens():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    sidebar = SidebarWindow(width=440)
    sidebar.resize(440, 920)
    sidebar.show()
    app.processEvents()

    screens = [
        (0, "screen_0_home.png", sidebar._show_dashboard_view),
        (1, "screen_1_chat.png", sidebar._show_chat_view),
        (2, "screen_2_explore.png", sidebar._show_explore_view),
        (3, "screen_3_thunder.png", sidebar._show_thunder_view),
        (4, "screen_4_files.png", sidebar._show_files_view),
        (5, "screen_5_history.png", sidebar._show_history_view),
        (6, "screen_6_settings.png", sidebar._show_settings_view),
        (7, "screen_7_live_call.png", sidebar.start_live_call),
        (8, "screen_8_meeting_transcripts.png", sidebar._show_meeting_view),
    ]

    # Pre-populate sample diarized meeting turns for Screen 8 demonstration
    from handless.intelligence.grok_persona import ConfigProposal
    from handless.meeting.models import TranscriptTurn

    # Add sample Grok chat and config proposal in Chat Screen View
    sidebar.chat_screen_view.add_user_message("hi how are u bro")
    sidebar.chat_screen_view.add_assistant_message("Yo! Living my best life at 0.01% CPU while you stare at your screen like a deer in headlights 💀 What are we automating today or are we just here to exchange 'hi's? 🔥")
    sidebar.chat_screen_view.add_user_message("can you change dictation shortcut to Ctrl+Alt+D?")
    prop = ConfigProposal(
        setting_key="hotkeys.toggle_dictation",
        setting_label="Dictation Shortcut",
        current_value="Ctrl + Shift",
        proposed_value="Ctrl + Alt + D",
        summary="Rebind global dictation hotkey to Ctrl + Alt + D",
        roast_comment="Rewiring so you don't accidentally fire dictation every time you type Ctrl+Shift+T 💀",
    )
    sidebar.chat_screen_view.add_config_proposal_card(prop)

    sample_turns = [
        TranscriptTurn(
            id="t1",
            speaker="Speaker 1",
            text="Hey team, in today's Zoom sync let's review the Q3 product roadmap and backend pipeline migration.",
            timestamp=1730000000,
            is_user=False,
            source="system",
        ),
        TranscriptTurn(
            id="t2",
            speaker="You",
            text="Sounds great! I've already verified the dual-channel loopback audio capture and Groq Whisper transcription with 99.4% accuracy.",
            timestamp=1730000045,
            is_user=True,
            source="mic",
        ),
        TranscriptTurn(
            id="t3",
            speaker="Speaker 2",
            text="Awesome progress. Let's make sure we deliver the executive summary to the leadership board by Friday at 3 PM for $50,000 budget sign-off.",
            timestamp=1730000110,
            is_user=False,
            source="system",
        ),
        TranscriptTurn(
            id="t4",
            speaker="You",
            text="I will run the 1-click AI summary and copy the transcript formatted for Claude right after this call.",
            timestamp=1730000160,
            is_user=True,
            source="mic",
        ),
    ]
    for t in sample_turns:
        sidebar.meeting_screen_view.add_turn(t)
    sidebar.meeting_screen_view.app_badge.setText("● Zoom Meeting")
    sidebar.meeting_screen_view.title_label.setText("Product Strategy & Architecture Call")
    sidebar.meeting_screen_view.clock_pill.setText("● Rec 04:12")
    sidebar.meeting_screen_view.clock_pill.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 700;")
    sidebar.meeting_screen_view.record_btn.setText("⏹ Stop")
    sidebar.meeting_screen_view.record_btn.setStyleSheet("""
        QPushButton#recordCallBtn {
            background-color: #18181B;
            color: #FFFFFF;
            border: none;
            border-radius: 12px;
            padding: 6px 12px;
            font-weight: 700;
            font-size: 11px;
        }
    """)
    sidebar.meeting_screen_view.mic_eq.set_level(0.7)
    sidebar.meeting_screen_view.sys_eq.set_level(0.85)

    for idx, filename, show_fn in screens:
        show_fn()
        app.processEvents()

        # Create target image
        img = QImage(sidebar.size(), QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor(0, 0, 0, 0))

        sidebar.render(img)
        out_path = os.path.join(ARTIFACT_DIR, filename)
        img.save(out_path)
        print(f"Rendered screen {idx} -> {out_path}")

    # Render Explore Apps View
    sidebar._show_explore_view()
    sidebar.explore_screen_view._set_category_by_name("Apps")
    app.processEvents()
    explore_apps_img = QImage(sidebar.size(), QImage.Format.Format_ARGB32_Premultiplied)
    explore_apps_img.fill(QColor(0, 0, 0, 0))
    sidebar.render(explore_apps_img)
    explore_apps_out = os.path.join(ARTIFACT_DIR, "screen_2_explore_apps.png")
    explore_apps_img.save(explore_apps_out)
    print(f"Rendered Explore Apps -> {explore_apps_out}")

    # Render Explore Productivity View
    sidebar.explore_screen_view._set_category_by_name("Productivity")
    app.processEvents()
    explore_prod_img = QImage(sidebar.size(), QImage.Format.Format_ARGB32_Premultiplied)
    explore_prod_img.fill(QColor(0, 0, 0, 0))
    sidebar.render(explore_prod_img)
    explore_prod_out = os.path.join(ARTIFACT_DIR, "screen_2_explore_productivity.png")
    explore_prod_img.save(explore_prod_out)
    print(f"Rendered Explore Productivity -> {explore_prod_out}")

    # Render wide mode preview (Dashboard)
    sidebar._show_dashboard_view()
    sidebar.set_wide_mode(True, animated=False)
    app.processEvents()
    wide_img = QImage(sidebar.size(), QImage.Format.Format_ARGB32_Premultiplied)
    wide_img.fill(QColor(0, 0, 0, 0))
    sidebar.render(wide_img)
    wide_out = os.path.join(ARTIFACT_DIR, "sidebar_wide_preview.png")
    wide_img.save(wide_out)
    print(f"Rendered wide mode preview -> {wide_out}")

    # Render settings wide mode preview
    sidebar._show_settings_view()
    app.processEvents()
    settings_wide_img = QImage(sidebar.size(), QImage.Format.Format_ARGB32_Premultiplied)
    settings_wide_img.fill(QColor(0, 0, 0, 0))
    sidebar.render(settings_wide_img)
    settings_wide_out = os.path.join(ARTIFACT_DIR, "settings_wide_preview.png")
    settings_wide_img.save(settings_wide_out)
    print(f"Rendered settings wide mode preview -> {settings_wide_out}")

    sidebar.close()

    # Render floating copilot widget preview
    floating = FloatingCopilotWidget()
    floating.show()
    app.processEvents()

    # Use grab to capture translucent window + children
    pix = floating.grab()

    # Place on a clean preview canvas for clear visual inspection
    canvas = QImage(240, 240, QImage.Format.Format_ARGB32_Premultiplied)
    canvas.fill(QColor(245, 245, 247))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    # Draw centered floating widget scaled nicely
    scaled_pix = pix.scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    cx = (240 - scaled_pix.width()) // 2
    cy = (240 - scaled_pix.height()) // 2
    painter.drawPixmap(cx, cy, scaled_pix)
    painter.end()

    f_out_path = os.path.join(ARTIFACT_DIR, "floating_widget_preview.png")
    canvas.save(f_out_path)
    print(f"Rendered floating widget -> {f_out_path}")
    floating.close()

    # Render Desktop Element Inspector preview
    from handless.ui.element_inspector import DesktopElementInspector
    from unittest.mock import MagicMock
    mock_uia = MagicMock()
    mock_uia.get_top_level_windows.return_value = [
        {"title": "WhatsApp - Google Chrome", "class_name": "Chrome_WidgetWin_1", "handle": 12345},
        {"title": "Vyoma Handless", "class_name": "Qt6QWindowIcon", "handle": 67890},
    ]
    inspector = DesktopElementInspector(uia=mock_uia)
    inspector.resize(1020, 720)
    inspector.show()
    app.processEvents()

    sample_elem = {
        "name": "Send Message",
        "auto_id": "btn_send_msg",
        "control_type": "Button",
        "is_visible": True,
        "is_enabled": True,
        "is_web_content": True,
        "source_tag": "[WEB]",
        "rect": {"left": 820, "top": 640, "width": 84, "height": 38},
        "wrapper": MagicMock(window_text=lambda: "Send Message"),
    }
    inspector._elements_cache = [sample_elem]
    inspector._apply_filters()
    inspector._update_detail_card(sample_elem)
    app.processEvents()

    inspector_img = QImage(inspector.size(), QImage.Format.Format_ARGB32_Premultiplied)
    inspector_img.fill(QColor(0, 0, 0, 0))
    inspector.render(inspector_img)
    inspector_out = os.path.join(ARTIFACT_DIR, "element_inspector_preview.png")
    inspector_img.save(inspector_out)
    print(f"Rendered element inspector -> {inspector_out}")
    inspector.close()


if __name__ == "__main__":
    render_all_screens()


