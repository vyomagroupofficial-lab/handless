"""Render showcase image of all 9 ThinkingOrb states in Handless UI theme."""

import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication

from handless.ui.thinking_orbs import ThinkingOrbWidget, STATE_TO_MODE

def main():
    app = QApplication.instance() or QApplication([])

    states = [
        ("working", "Working", "Tilted particles orbiting the sphere"),
        ("searching", "Searching", "Scanning radar meridian sweep"),
        ("solving", "Solving", "Rubik bands twisting & clicking solved"),
        ("listening", "Listening", "Rolling waves with emerald crests"),
        ("connecting", "Connecting", "Constellation web & signal packets"),
        ("weaving", "Weaving", "Three plaited helical strands"),
        ("composing", "Composing", "Undulating multi-band sash"),
        ("breathing", "Breathing", "Organic radial morphing ring"),
        ("shaping", "Shaping", "Geometry: Circle → Triangle → Square"),
    ]

    # Grid: 3 columns x 3 rows
    # Card size: 240 x 240, spacing: 20, margins: 30
    card_w, card_h = 240, 240
    gap = 24
    margin_x, margin_y = 36, 80

    total_w = margin_x * 2 + 3 * card_w + 2 * gap
    total_h = margin_y + 3 * card_h + 2 * gap + 40

    img = QImage(total_w, total_h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor("#FBFBF9"))

    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    # Header title
    title_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
    sub_font = QFont("Segoe UI", 11, QFont.Weight.Normal)
    label_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
    desc_font = QFont("Segoe UI", 9, QFont.Weight.Normal)

    painter.setFont(title_font)
    painter.setPen(QColor("#18181B"))
    painter.drawText(margin_x, 42, "Handless Dotted Thinking Orbs")

    painter.setFont(sub_font)
    painter.setPen(QColor("#71717A"))
    painter.drawText(margin_x, 64, "Faithfully ported from Jakub Antalik's thinking-orbs • Handless Charcoal & Emerald Theme")

    # Render each state card
    for idx, (st_name, st_title, st_desc) in enumerate(states):
        col = idx % 3
        row = idx // 3
        x = margin_x + col * (card_w + gap)
        y = margin_y + row * (card_h + gap)

        # Card background
        painter.setPen(QColor("#E5E3DC"))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRoundedRect(x, y, card_w, card_h, 16, 16)

        # Orb widget
        orb = ThinkingOrbWidget(size=110, state=st_name, theme="handless")
        if st_name == "listening":
            orb.set_level(0.7)
        orb_img = QImage(110, 110, QImage.Format.Format_ARGB32_Premultiplied)
        orb_img.fill(Qt.GlobalColor.transparent)
        orb.render(orb_img)

        orb_x = x + (card_w - 110) // 2
        orb_y = y + 18
        painter.drawImage(orb_x, orb_y, orb_img)

        # Card Title
        painter.setFont(label_font)
        painter.setPen(QColor("#18181B"))
        painter.drawText(QRectF(x + 12, y + 138, card_w - 24, 24), Qt.AlignmentFlag.AlignCenter, st_title)

        # Card Mode Pill
        mode_name = STATE_TO_MODE[st_name]
        painter.setFont(desc_font)
        painter.setPen(QColor("#10B981"))
        painter.drawText(QRectF(x + 12, y + 162, card_w - 24, 18), Qt.AlignmentFlag.AlignCenter, f"mode: {mode_name}")

        # Card Description
        painter.setFont(desc_font)
        painter.setPen(QColor("#71717A"))
        painter.drawText(QRectF(x + 16, y + 184, card_w - 32, 40), Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap, st_desc)

    painter.end()

    out_path = Path("C:/Users/USER/.gemini/antigravity/brain/78f612f1-8d30-4ff4-841f-c8194e0ecbb3/thinking_orbs_showcase.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path))
    print(f"Saved showcase to {out_path}")

if __name__ == "__main__":
    main()

