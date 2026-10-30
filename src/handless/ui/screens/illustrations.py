"""Custom 3D Metallic Emblem Illustrations for Vyoma Handless Screens.

Provides antialiased, hardware-accelerated vector illustrations featuring:
- Hero3DIllustration: Dual graphite metallic pills with tilted orbital halo ring (Home & Explore)
- Thunder3DIllustration: 3D metallic lightning bolt sculpture with silver orbital ring (Thunder)
- Files3DIllustration: 3D isometric folder with documents and orbital halo ring (Files)
- History3DIllustration: 3D clock dial with document cards and orbital halo ring (History)
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget


class BaseEmblemWidget(QWidget):
    """Base class for animated floating 3D emblems."""

    def __init__(self, parent: Optional[QWidget] = None, width: int = 110, height: int = 100) -> None:
        super().__init__(parent)
        self.setFixedSize(width, height)
        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(33)

    def _on_tick(self) -> None:
        self._phase = (self._phase + 0.035) % (2 * math.pi)
        self.update()


class Hero3DIllustration(BaseEmblemWidget):
    """Dual capsule slits & sweeping orbital halo ring (Home & Explore)."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = (h / 2.0) - 2.0
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
        back_pen = QPen(QColor(180, 180, 185, 120), 3.2)
        back_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(back_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(-44, -18, 88, 36, 0 * 16, 180 * 16)
        painter.restore()

        # 3. Two Vertical Dark Metallic Pill Cylinders
        painter.save()
        painter.translate(cx, cy + float_y)
        painter.rotate(-8)

        # Pill 1 (Left)
        p1_rect = QRect(-20, -22, 14, 46)
        p1_grad = QLinearGradient(p1_rect.left(), p1_rect.top(), p1_rect.right(), p1_rect.bottom())
        p1_grad.setColorAt(0.0, QColor(39, 39, 42))
        p1_grad.setColorAt(0.4, QColor(24, 24, 27))
        p1_grad.setColorAt(1.0, QColor(9, 9, 11))
        painter.setBrush(p1_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(p1_rect, 7, 7)

        # Sheen on Pill 1
        p1_sheen = QLinearGradient(p1_rect.left() + 2, p1_rect.top() + 2, p1_rect.left() + 5, p1_rect.top() + 18)
        p1_sheen.setColorAt(0.0, QColor(255, 255, 255, 90))
        p1_sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(p1_sheen)
        painter.drawRoundedRect(QRect(-18, -20, 4, 16), 2, 2)

        # Pill 2 (Right)
        p2_rect = QRect(2, -28, 15, 56)
        p2_grad = QLinearGradient(p2_rect.left(), p2_rect.top(), p2_rect.right(), p2_rect.bottom())
        p2_grad.setColorAt(0.0, QColor(63, 63, 70))
        p2_grad.setColorAt(0.35, QColor(24, 24, 27))
        p2_grad.setColorAt(1.0, QColor(9, 9, 11))
        painter.setBrush(p2_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(p2_rect, 7.5, 7.5)

        # Sheen on Pill 2
        p2_sheen = QLinearGradient(p2_rect.left() + 2, p2_rect.top() + 2, p2_rect.left() + 6, p2_rect.top() + 22)
        p2_sheen.setColorAt(0.0, QColor(255, 255, 255, 110))
        p2_sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(p2_sheen)
        painter.drawRoundedRect(QRect(4, -26, 4, 20), 2, 2)
        painter.restore()

        # 4. Front arc of sweeping orbital ring
        painter.save()
        painter.translate(cx, cy + float_y)
        painter.rotate(-28)
        front_pen = QPen(QColor(24, 24, 27, 240), 3.4)
        front_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(front_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(-44, -18, 88, 36, 180 * 16, 180 * 16)

        ring_sheen = QPen(QColor(255, 255, 255, 180), 1.2)
        painter.setPen(ring_sheen)
        painter.drawArc(-43, -17, 86, 34, 200 * 16, 80 * 16)
        painter.restore()


class Thunder3DIllustration(BaseEmblemWidget):
    """3D Metallic Lightning Bolt sculpture with silver orbital halo ring (Thunder Screen)."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = (h / 2.0) - 2.0
        float_y = math.sin(self._phase) * 2.2

        # 1. Ground Shadow
        shadow_grad = QRadialGradient(cx, cy + 38, 42)
        shadow_grad.setColorAt(0.0, QColor(0, 0, 0, 35))
        shadow_grad.setColorAt(0.7, QColor(0, 0, 0, 10))
        shadow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(shadow_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy + 38), 44, 12)

        # 2. Back arc of tilted orbital ring
        painter.save()
        painter.translate(cx, cy + float_y)
        painter.rotate(-26)
        back_pen = QPen(QColor(180, 180, 185, 120), 3.2)
        painter.setPen(back_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(-46, -18, 92, 36, 0 * 16, 180 * 16)
        painter.restore()

        # 3. 3D Metallic Lightning Bolt
        painter.save()
        painter.translate(cx, cy + float_y)

        bolt_path = QPainterPath()
        bolt_path.moveTo(3, -32)
        bolt_path.lineTo(-16, 2)
        bolt_path.lineTo(-2, 2)
        bolt_path.lineTo(-6, 32)
        bolt_path.lineTo(18, -4)
        bolt_path.lineTo(4, -4)
        bolt_path.closeSubpath()

        bolt_grad = QLinearGradient(-15, -30, 18, 30)
        bolt_grad.setColorAt(0.0, QColor(50, 50, 55))
        bolt_grad.setColorAt(0.35, QColor(24, 24, 27))
        bolt_grad.setColorAt(1.0, QColor(9, 9, 11))
        painter.setBrush(bolt_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillPath(bolt_path, bolt_grad)

        # Specular sheen bevel
        sheen_pen = QPen(QColor(255, 255, 255, 90), 1.5)
        painter.setPen(sheen_pen)
        painter.drawLine(3, -32, -16, 2)
        painter.drawLine(-2, 2, -6, 32)
        painter.restore()

        # 4. Front arc of orbital ring
        painter.save()
        painter.translate(cx, cy + float_y)
        painter.rotate(-26)
        front_pen = QPen(QColor(24, 24, 27, 240), 3.4)
        painter.setPen(front_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(-46, -18, 92, 36, 180 * 16, 180 * 16)

        ring_sheen = QPen(QColor(255, 255, 255, 180), 1.2)
        painter.setPen(ring_sheen)
        painter.drawArc(-45, -17, 90, 34, 200 * 16, 80 * 16)
        painter.restore()


class Files3DIllustration(BaseEmblemWidget):
    """3D Isometric Folder sculpture with documents & orbital halo ring (Files Screen)."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = (h / 2.0) - 2.0
        float_y = math.sin(self._phase) * 2.2

        # 1. Ground Shadow
        shadow_grad = QRadialGradient(cx, cy + 38, 44)
        shadow_grad.setColorAt(0.0, QColor(0, 0, 0, 35))
        shadow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(shadow_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy + 38), 44, 12)

        # 2. Back arc of tilted orbital ring
        painter.save()
        painter.translate(cx, cy + float_y)
        painter.rotate(-28)
        back_pen = QPen(QColor(180, 180, 185, 120), 3.2)
        painter.setPen(back_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(-46, -18, 92, 36, 0 * 16, 180 * 16)
        painter.restore()

        # 3. 3D Folder & Documents
        painter.save()
        painter.translate(cx, cy + float_y)
        painter.rotate(-6)

        # Folder Back Flap (dark charcoal)
        back_path = QPainterPath()
        back_path.addRoundedRect(-24, -26, 46, 38, 5, 5)
        b_grad = QLinearGradient(-24, -26, 22, 12)
        b_grad.setColorAt(0.0, QColor(39, 39, 42))
        b_grad.setColorAt(1.0, QColor(18, 18, 20))
        painter.fillPath(back_path, b_grad)

        # Document Sheet (white/cream tilted)
        doc_path = QPainterPath()
        doc_path.addRoundedRect(-18, -32, 36, 36, 3, 3)
        painter.fillPath(doc_path, QColor(255, 255, 255))
        painter.setPen(QPen(QColor(220, 218, 212), 1))
        painter.drawPath(doc_path)

        # Folder Front Flap (light ivory/translucent)
        front_path = QPainterPath()
        front_path.moveTo(-26, -4)
        front_path.lineTo(24, -4)
        front_path.lineTo(20, 22)
        front_path.lineTo(-22, 22)
        front_path.closeSubpath()

        f_grad = QLinearGradient(-26, -4, 24, 22)
        f_grad.setColorAt(0.0, QColor(245, 244, 238, 245))
        f_grad.setColorAt(1.0, QColor(230, 228, 220, 245))
        painter.setPen(QPen(QColor(200, 196, 186), 1))
        painter.setBrush(f_grad)
        painter.drawPath(front_path)
        painter.restore()

        # 4. Front arc of orbital ring
        painter.save()
        painter.translate(cx, cy + float_y)
        painter.rotate(-28)
        front_pen = QPen(QColor(24, 24, 27, 240), 3.4)
        painter.setPen(front_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(-46, -18, 92, 36, 180 * 16, 180 * 16)
        painter.restore()


class History3DIllustration(BaseEmblemWidget):
    """3D Clock face dial with tilted orbital halo ring (History Screen)."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = (h / 2.0) - 2.0
        float_y = math.sin(self._phase) * 2.2

        # 1. Ground Shadow
        shadow_grad = QRadialGradient(cx, cy + 38, 44)
        shadow_grad.setColorAt(0.0, QColor(0, 0, 0, 35))
        shadow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(shadow_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy + 38), 44, 12)

        # 2. Back arc of tilted orbital ring
        painter.save()
        painter.translate(cx, cy + float_y)
        painter.rotate(-26)
        back_pen = QPen(QColor(180, 180, 185, 120), 3.2)
        painter.setPen(back_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(-46, -18, 92, 36, 0 * 16, 180 * 16)
        painter.restore()

        # 3. 3D Clock Card & Dial
        painter.save()
        painter.translate(cx, cy + float_y)
        painter.rotate(6)

        # Card Back
        card_rect = QRect(-26, -26, 48, 52)
        c_grad = QLinearGradient(card_rect.left(), card_rect.top(), card_rect.right(), card_rect.bottom())
        c_grad.setColorAt(0.0, QColor(255, 255, 255))
        c_grad.setColorAt(1.0, QColor(240, 238, 230))
        painter.setBrush(c_grad)
        painter.setPen(QPen(QColor(220, 218, 210), 1))
        painter.drawRoundedRect(card_rect, 10, 10)

        # Clock Face Dial
        dial_center = QPointF(-2, 0)
        dial_radius = 16.0
        painter.setBrush(QColor(250, 249, 244))
        painter.setPen(QPen(QColor(24, 24, 27), 2))
        painter.drawEllipse(dial_center, dial_radius, dial_radius)

        # Clock Hands
        painter.setPen(QPen(QColor(24, 24, 27), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(dial_center.x()), int(dial_center.y()), int(dial_center.x()), int(dial_center.y() - 9))
        painter.drawLine(int(dial_center.x()), int(dial_center.y()), int(dial_center.x() + 7), int(dial_center.y() + 4))

        painter.restore()

        # 4. Front arc of orbital ring
        painter.save()
        painter.translate(cx, cy + float_y)
        painter.rotate(-26)
        front_pen = QPen(QColor(24, 24, 27, 240), 3.4)
        painter.setPen(front_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(-46, -18, 92, 36, 180 * 16, 180 * 16)
        painter.restore()

