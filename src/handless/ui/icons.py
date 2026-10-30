"""Vector SVG Icon Library for Vyoma Handless.

Provides clean, crisp, scalable vector SVG assets inspired by Lucide, Feather,
and Windows 11 Fluent icons, completely replacing emoji glyphs with high-DPI
vector icons.
"""

from __future__ import annotations

import os
from typing import Optional
from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# ---------------------------------------------------------------------------
# SVG Definitions (ViewBox 0 0 24 24, stroke-width 2, round linecaps)
# ---------------------------------------------------------------------------

# 9-Dot App / Menu Grid (matching reference image top-right header)
SVG_GRID_9 = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <circle cx="5" cy="5" r="2"/>
  <circle cx="12" cy="5" r="2"/>
  <circle cx="19" cy="5" r="2"/>
  <circle cx="5" cy="12" r="2"/>
  <circle cx="12" cy="12" r="2"/>
  <circle cx="19" cy="12" r="2"/>
  <circle cx="5" cy="19" r="2"/>
  <circle cx="12" cy="19" r="2"/>
  <circle cx="19" cy="19" r="2"/>
</svg>
"""

# Settings Gear
SVG_SETTINGS = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
  <circle cx="12" cy="12" r="3"/>
</svg>
"""

# Close Cross
SVG_CLOSE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="18" y1="6" x2="6" y2="18"/>
  <line x1="6" y1="6" x2="18" y2="18"/>
</svg>
"""

# AI Sparkle / Refine (matching floating toolbar)
SVG_SPARKLE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <path d="M12 2L14.2 8.8L21 11L14.2 13.2L12 20L9.8 13.2L3 11L9.8 8.8L12 2Z"/>
  <path d="M19 16L19.9 18.1L22 19L19.9 19.9L19 22L18.1 19.9L16 19L18.1 18.1L19 16Z"/>
</svg>
"""

# Pencil / Edit (matching floating toolbar)
SVG_PENCIL = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/>
</svg>
"""

# Retry / Refresh (matching floating toolbar)
SVG_REFRESH = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-1.19"/>
</svg>
"""

# Copy Document (matching floating toolbar)
SVG_COPY = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
</svg>
"""

# Search Lens (matching bottom input bar)
SVG_SEARCH = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="11" cy="11" r="8"/>
  <line x1="21" y1="21" x2="16.65" y2="16.65"/>
</svg>
"""

# Modern Microphone Capsule
SVG_MIC = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="9" y="2" width="6" height="12" rx="3"/>
  <path d="M5 10a7 7 0 0 0 14 0"/>
  <line x1="12" y1="17" x2="12" y2="21"/>
  <line x1="8" y1="21" x2="16" y2="21"/>
</svg>
"""

# Muted Microphone
SVG_MIC_OFF = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="1" y1="1" x2="23" y2="23"/>
  <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"/>
  <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"/>
  <line x1="12" y1="19" x2="12" y2="23"/>
  <line x1="8" y1="23" x2="16" y2="23"/>
</svg>
"""

# Live Call Phone Handset
SVG_PHONE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
</svg>
"""

# Live Call Phone End / Off
SVG_PHONE_OFF = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7 2 2 0 0 1 1.72 2v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.42 19.42 0 0 1-3.33-2.67m-2.67-3.34a19.79 19.79 0 0 1-3.07-8.63A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91"/>
  <line x1="23" y1="1" x2="1" y2="23"/>
</svg>
"""

# Active Filled Microphone with Pulsing Sound Waves
SVG_MIC_ACTIVE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <rect x="9" y="2" width="6" height="12" rx="3"/>
  <path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M5 10a7 7 0 0 0 14 0"/>
  <line x1="12" y1="17" x2="12" y2="21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  <line x1="8" y1="21" x2="16" y2="21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>
"""

# Document / File (CSV / Text card icon from screenshot)
SVG_FILE_TEXT = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
  <polyline points="14 2 14 8 20 8"/>
  <line x1="16" y1="13" x2="8" y2="13"/>
  <line x1="16" y1="17" x2="8" y2="17"/>
  <line x1="10" y1="9" x2="8" y2="9"/>
</svg>
"""

# Download Icon (matching tray + arrow on CSV card from screenshot)
SVG_DOWNLOAD = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
  <polyline points="7 10 12 15 17 10"/>
  <line x1="12" y1="15" x2="12" y2="3"/>
</svg>
"""

# Rocket (App Launch)
SVG_ROCKET = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/>
  <path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/>
  <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/>
  <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>
</svg>
"""

# Window Snap / Grid Split
SVG_SNAP = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="3" width="18" height="18" rx="2"/>
  <line x1="12" y1="3" x2="12" y2="21"/>
</svg>
"""

# Globe / Browser
SVG_GLOBE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/>
  <line x1="2" y1="12" x2="22" y2="12"/>
  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
</svg>
"""

# Music / Media Play
SVG_MUSIC = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M9 18V5l12-2v13"/>
  <circle cx="6" cy="18" r="3"/>
  <circle cx="18" cy="16" r="3"/>
</svg>
"""

# Lightning Bolt (Command Mode)
SVG_LIGHTNING = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
</svg>
"""

# Fountain Pen Nib (Dictation Mode)
SVG_PEN = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 19l7-7 3 3-7 7-3-3z"/>
  <path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/>
  <path d="M2 2l7.586 7.586"/>
  <circle cx="11" cy="11" r="2"/>
</svg>
"""

# Stop Square
SVG_STOP = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <rect x="4" y="4" width="16" height="16" rx="3" ry="3"/>
</svg>
"""

# Red Record Dot Circle
SVG_RECORD_DOT = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <circle cx="12" cy="12" r="7"/>
</svg>
"""

# Clean Left Arrow (Back)
SVG_ARROW_LEFT = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="19" y1="12" x2="5" y2="12"/>
  <polyline points="12 19 5 12 12 5"/>
</svg>
"""

# Play Triangle (Resume)
SVG_PLAY = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <polygon points="5 3 19 12 5 21 5 3"/>
</svg>
"""

# Checkmark
SVG_CHECK = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="20 6 9 17 4 12"/>
</svg>
"""

# Keyboard Shortcut
SVG_KEYBOARD = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="2" y="4" width="20" height="16" rx="2"/>
  <line x1="6" y1="8" x2="6" y2="8"/>
  <line x1="10" y1="8" x2="10" y2="8"/>
  <line x1="14" y1="8" x2="14" y2="8"/>
  <line x1="18" y1="8" x2="18" y2="8"/>
  <line x1="6" y1="12" x2="6" y2="12"/>
  <line x1="18" y1="12" x2="18" y2="12"/>
  <line x1="9" y1="16" x2="15" y2="16"/>
</svg>
"""

# Mouse Click
SVG_CLICK = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M3 3l7 18 3-7 7-3L3 3z"/>
  <path d="M13 13l6 6"/>
</svg>
"""

# Crosshair / Target Inspect
SVG_CROSSHAIR = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/>
  <line x1="22" y1="12" x2="18" y2="12"/>
  <line x1="6" y1="12" x2="2" y2="12"/>
  <line x1="12" y1="6" x2="12" y2="2"/>
  <line x1="12" y1="22" x2="12" y2="18"/>
</svg>
"""

# Window / Application App
SVG_WINDOW = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="2" y="3" width="20" height="18" rx="2"/>
  <line x1="2" y1="9" x2="22" y2="9"/>
  <circle cx="6" cy="6" r="1" fill="currentColor"/>
  <circle cx="10" cy="6" r="1" fill="currentColor"/>
</svg>
"""

# Eye (Preview / Highlight)
SVG_EYE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
  <circle cx="12" cy="12" r="3"/>
</svg>
"""

# Code / Automation Locator
SVG_CODE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="16 18 22 12 16 6"/>
  <polyline points="8 6 2 12 8 18"/>
</svg>
"""

# Double Slit Handless Brand Mark (Left Rail Top)
SVG_HANDLESS_MARK = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round">
  <line x1="9" y1="17" x2="11" y2="7"/>
  <line x1="13" y1="17" x2="15" y2="7"/>
</svg>
"""

# Home Icon (Left Rail)
SVG_HOME = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
  <polyline points="9 22 9 12 15 12 15 22"/>
</svg>
"""

# Chat / Message Bubble (Left Rail)
SVG_CHAT = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
</svg>
"""

# 4-Square Apps Grid / Bento (Left Rail)
SVG_APPS_GRID = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="3" width="7" height="7" rx="1.5"/>
  <rect x="14" y="3" width="7" height="7" rx="1.5"/>
  <rect x="14" y="14" width="7" height="7" rx="1.5"/>
  <rect x="3" y="14" width="7" height="7" rx="1.5"/>
</svg>
"""

# Folder (Left Rail)
SVG_FOLDER = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
</svg>
"""

# Clock / Recent History (Left Rail)
SVG_CLOCK = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/>
  <polyline points="12 6 12 12 16 14"/>
</svg>
"""

# User / Profile Outline (Left Rail Bottom)
SVG_USER = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
  <circle cx="12" cy="7" r="4"/>
</svg>
"""

# Voice Wave Equalizer Bars (Input Box & Footer)
SVG_VOICE_WAVE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
  <line x1="4" y1="10" x2="4" y2="14"/>
  <line x1="8" y1="6" x2="8" y2="18"/>
  <line x1="12" y1="3" x2="12" y2="21"/>
  <line x1="16" y1="7" x2="16" y2="17"/>
  <line x1="20" y1="10" x2="20" y2="14"/>
</svg>
"""

# Paperclip Attachment (Input Box)
SVG_PAPERCLIP = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
</svg>
"""

# Arrow Up (Circular Send Button)
SVG_ARROW_UP = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <line x1="12" y1="19" x2="12" y2="5"/>
  <polyline points="5 12 12 5 19 12"/>
</svg>
"""

# Chevron Right (Recent Items)
SVG_CHEVRON_RIGHT = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="9 18 15 12 9 6"/>
</svg>
"""

# Chevron Down (Ready Status Dropdown)
SVG_CHEVRON_DOWN = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 9 12 15 18 9"/>
</svg>
"""

# Google Chrome Brand Glyph (Quick Card & Recent Row)
SVG_BRAND_CHROME = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/>
  <circle cx="12" cy="12" r="4"/>
  <line x1="21.17" y1="8" x2="12" y2="8"/>
  <line x1="3.95" y1="6.06" x2="8.54" y2="14"/>
  <line x1="10.88" y1="21.94" x2="15.46" y2="14"/>
</svg>
"""

# YouTube Brand Glyph (Quick Card)
SVG_BRAND_YOUTUBE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
</svg>
"""

# Capture Screen Viewfinder (Quick Card)
SVG_CAPTURE_SCREEN = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 8V5a1 1 0 0 1 1-1h3"/>
  <path d="M16 4h3a1 1 0 0 1 1 1v3"/>
  <path d="M4 16v3a1 1 0 0 0 1 1h3"/>
  <path d="M16 20h3a1 1 0 0 0 1-1v-3"/>
  <circle cx="12" cy="12" r="2.5"/>
</svg>
"""

# Image / Gallery Thumbnail (Recent Feed)
SVG_IMAGE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
  <circle cx="8.5" cy="8.5" r="1.5"/>
  <polyline points="21 15 16 10 5 21"/>
</svg>
"""

# Mail / Envelope (Explore & Thunder)
SVG_MAIL = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="2" y="4" width="20" height="16" rx="2"/>
  <path d="M22 6l-10 7L2 6"/>
</svg>
"""

# Calendar / Schedule (Explore & Thunder)
SVG_CALENDAR = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
  <line x1="16" y1="2" x2="16" y2="6"/>
  <line x1="8" y1="2" x2="8" y2="6"/>
  <line x1="3" y1="10" x2="21" y2="10"/>
</svg>
"""

# Plus Symbol (+)
SVG_PLUS = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <line x1="12" y1="5" x2="12" y2="19"/>
  <line x1="5" y1="12" x2="19" y2="12"/>
</svg>
"""

# Outline Play Triangle (▷)
SVG_PLAY_OUTLINE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <polygon points="6 4 20 12 6 20 6 4"/>
</svg>
"""

# Three Dots Horizontal (···)
SVG_MORE_HORIZONTAL = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <circle cx="12" cy="12" r="2"/>
  <circle cx="19" cy="12" r="2"/>
  <circle cx="5" cy="12" r="2"/>
</svg>
"""

# Graduation Cap / Study (Thunder Templates)
SVG_GRADUATION_CAP = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
  <path d="M6 12v5c0 2 3 3 6 3s6-1 6-3v-5"/>
</svg>
"""

# Video Camera (Thunder Templates)
SVG_VIDEO_CAMERA = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polygon points="23 7 16 12 23 17 23 7"/>
  <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
</svg>
"""

# Briefcase / Office (Thunder Templates)
SVG_BRIEFCASE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
  <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
</svg>
"""

# Code Brackets <> (Thunder Templates)
SVG_CODE_BRACKETS = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="16 18 22 12 16 6"/>
  <polyline points="8 6 2 12 8 18"/>
</svg>
"""

# Chart Trends (Thunder & Explore)
SVG_CHART_TRENDS = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
  <polyline points="17 6 23 6 23 12"/>
</svg>
"""

# Cloud Search / Find a file (Files Quick Actions)
SVG_CLOUD_SEARCH = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
  <circle cx="11" cy="13" r="3"/>
  <line x1="13.5" y1="15.5" x2="16" y2="18"/>
</svg>
"""

# Hard Disk / Storage (Files Storage Overview)
SVG_STORAGE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="22" y1="12" x2="2" y2="12"/>
  <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>
  <line x1="6" y1="16" x2="6.01" y2="16"/>
  <line x1="10" y1="16" x2="10.01" y2="16"/>
</svg>
"""

# Green Circle Checkmark (Chat Multi-Step Plan)
SVG_CHECK_CIRCLE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <circle cx="12" cy="12" r="10" fill="#10B981"/>
  <polyline points="8 12 11 15 16 9" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

# Active Dot Ring Indicator (Chat Multi-Step Plan)
SVG_DOT_RING = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <circle cx="12" cy="12" r="9" stroke="#18181B" stroke-width="2"/>
  <circle cx="12" cy="12" r="4.5" fill="#18181B"/>
</svg>
"""

# Pending Dot (Chat Multi-Step Plan)
SVG_DOT_PENDING = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <circle cx="12" cy="12" r="6" fill="#A1A1AA"/>
</svg>
"""

# Microsoft Edge Brand Glyph
SVG_BRAND_EDGE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
</svg>
"""

# Notion Brand Glyph
SVG_BRAND_NOTION = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.98-.7-2.053-.607L3.198 2.388c-.466.046-.56.326-.373.513l1.634 1.307zm.84 3.73v13.62c0 .84.42 1.12 1.213 1.073l14.15-.84c.84-.047 1.072-.56 1.072-1.26V6.914c0-.7-.373-1.026-1.073-.98l-14.29.84c-.746.046-1.072.466-1.072 1.164zm13.12 1.353c.093.373 0 .746-.373.793l-.933.186v10.122c-1.12.653-2.193.98-3.08.98-1.4 0-1.727-.466-2.753-1.773l-4.153-6.577v6.623l1.493.326c.42.093.513.373.513.653 0 .42-.373.42-.513.42l-4.013.233c-.093-.28 0-.653.373-.746l1.027-.233V10.22l-1.4-.14c-.373-.047-.466-.326-.466-.606 0-.327.327-.42.56-.42l4.246-.28 4.293 6.67V9.754l-1.353-.14c-.373-.047-.467-.326-.467-.606 0-.327.327-.42.56-.42l4.013-.233c.373 0 .56.28.56.56z"/>
</svg>
"""

# VS Code Brand Glyph
SVG_BRAND_VSCODE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <path d="M23.15 2.587L18.21.21a1.494 1.494 0 0 0-1.705.29l-9.46 8.63-4.12-3.128a.999.999 0 0 0-1.276.057L.327 7.261A1 1 0 0 0 .32 8.68l3.415 3.32-3.415 3.32a1 1 0 0 0 .007 1.419l1.322 1.202a.999.999 0 0 0 1.276.057l4.12-3.128 9.46 8.63a1.492 1.492 0 0 0 1.704.29l4.94-2.377A1.5 1.5 0 0 0 24 20.06V3.939a1.5 1.5 0 0 0-.85-1.352zm-5.146 14.861L10.826 12l7.178-5.448v10.896z"/>
</svg>
"""

# Gmail Brand Glyph
SVG_BRAND_GMAIL = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
  <path d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.263H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z"/>
</svg>
"""





SVG_BRAIN = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.04z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.04z"/></svg>"""

SVG_SHIELD = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>"""

SVG_LOCK = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>"""

SVG_INFO = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>"""

SVG_HELP_CIRCLE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>"""

SVG_SLIDERS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>"""

SVG_BRAND_GOOGLE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.65v3h3.88c2.27-2.09 3.665-5.17 3.665-9.09z"/><path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.28v3.09C3.25 21.3 7.31 24 12 24z"/><path fill="#FBBC05" d="M5.28 14.32c-.25-.72-.38-1.49-.38-2.32s.14-1.6.38-2.32V6.59H1.28C.46 8.21 0 10.05 0 12s.46 3.79 1.28 5.41l4-3.09z"/><path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.25 2.7 1.28 6.59l4 3.09c.95-2.83 3.6-4.93 6.72-4.93z"/></svg>"""

SVG_ARROW_LEFT_RIGHT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 11 21 7 17 3"/><line x1="21" y1="7" x2="9" y2="7"/><polyline points="7 21 3 17 7 13"/><line x1="3" y1="17" x2="15" y2="17"/></svg>"""

SVG_EXPAND_HORIZONTAL = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>"""

SVG_MINUS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>"""

SVG_BRAND_SPOTIFY = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M7 9c3.5-1 7.5-.5 10 1"/><path d="M8 12c3-.8 6-.3 8 1"/><path d="M9 15c2.3-.5 4.7-.2 6 1"/></svg>"""

SVG_BRAND_DISCORD = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6h0a14.5 14.5 0 0 0-4-1.2 11.5 11.5 0 0 0-.5 1.2 13 13 0 0 0-3 0A11.5 11.5 0 0 0 10 4.8 14.5 14.5 0 0 0 6 6C3.5 10 3 14 3.5 18a14.5 14.5 0 0 0 4.5 2.2c.4-.5.7-1 1-1.6a9.5 9.5 0 0 1-1.6-.8l.4-.3a10.5 10.5 0 0 0 8.4 0l.4.3a9.5 9.5 0 0 1-1.6.8c.3.6.6 1.1 1 1.6 1.6-.4 3.1-1.1 4.5-2.2.5-4.5 0-8.5-2.5-12z"/><circle cx="9" cy="13" r="1"/><circle cx="15" cy="13" r="1"/></svg>"""

SVG_BRAND_WHATSAPP = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/><path d="M9 10a.5.5 0 0 0 1 0V9a.5.5 0 0 0-1 0v1zm4 4a.5.5 0 0 0 1 0v-1a.5.5 0 0 0-1 0v1z"/></svg>"""

SVG_TERMINAL = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>"""

SVG_INCOGNITO = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10h18M7 15h2m6 0h2"/><circle cx="7" cy="15" r="3"/><circle cx="17" cy="15" r="3"/><path d="M12 4l3 6H9l3-6z"/></svg>"""



# ---------------------------------------------------------------------------
# Rendering Helpers
# ---------------------------------------------------------------------------

def render_svg_pixmap(
    svg_xml: str,
    width: int = 20,
    height: int = 20,
    color: Optional[str] = None,
) -> QPixmap:
    """Render an SVG XML string into a high-DPI transparent QPixmap with custom color tint."""
    xml = svg_xml.strip()
    if color:
        xml = xml.replace("currentColor", color)

    renderer = QSvgRenderer(QByteArray(xml.encode("utf-8")))
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()

    return pixmap


def render_svg_icon(
    svg_xml: str,
    size: int = 20,
    color: Optional[str] = None,
    hover_color: Optional[str] = None,
) -> QIcon:
    """Create a QIcon from SVG XML, optionally supporting hover color states."""
    icon = QIcon()
    normal_pix = render_svg_pixmap(svg_xml, size, size, color=color or "#4B5563")
    icon.addPixmap(normal_pix, QIcon.Mode.Normal)

    if hover_color:
        hover_pix = render_svg_pixmap(svg_xml, size, size, color=hover_color)
        icon.addPixmap(hover_pix, QIcon.Mode.Active)

    return icon


def get_bot_logo_path(without_bg: bool = True) -> str:
    """Get absolute file path to Handless Bot logo."""
    filename = "handless-bot-withoutbg.png" if without_bg else "handless-bot.png"
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    c1 = os.path.join(os.path.dirname(pkg_dir), "assets", filename)
    if os.path.exists(c1):
        return c1
    c2 = os.path.join(r"C:\Users\USER\Downloads", filename)
    if os.path.exists(c2):
        return c2
    return ""


def get_bot_logo_pixmap(without_bg: bool = True, size: Optional[int] = None) -> QPixmap:
    """Get smoothly scaled QPixmap of Handless Bot logo."""
    path = get_bot_logo_path(without_bg)
    if path and os.path.exists(path):
        pm = QPixmap(path)
        if size and not pm.isNull():
            return pm.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return pm
    return QPixmap()


def get_bot_logo_icon(without_bg: bool = True, size: int = 32) -> QIcon:
    """Get QIcon of Handless Bot logo."""
    pm = get_bot_logo_pixmap(without_bg=without_bg, size=size)
    if not pm.isNull():
        return QIcon(pm)
    return QIcon()


