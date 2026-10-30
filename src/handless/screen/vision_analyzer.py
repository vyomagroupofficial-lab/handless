"""Computer Vision Screen Analyzer using mss and Gemini 2.5 Flash.

Provides visual fallback for applications without accessibility metadata (custom canvas,
games, poorly coded Electron apps). Captures fast screenshots and maps Gemini's
normalized 0-1000 bounding boxes back to physical Windows screen pixels.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from mss import mss
from PIL import Image
from pydantic import BaseModel, Field

from handless.security.credentials import get_gemini_api_key

logger = logging.getLogger(__name__)


class ElementVisionBox(BaseModel):
    label: str
    box_2d: list[int] = Field(description="[ymin, xmin, ymax, xmax] normalized on 0 to 1000 scale")
    confidence: float = Field(default=0.8)


class ScreenVisionResponse(BaseModel):
    elements: list[ElementVisionBox]
    reasoning: Optional[str] = None


class ScreenAnalysisResult(BaseModel):
    summary: str = Field(description="High-level summary of what is displayed on the screen")
    active_application: Optional[str] = Field(default=None, description="The primary open app (e.g. Chrome, VS Code)")
    key_findings: list[str] = Field(default_factory=list, description="Key insights, text snippets, or answers to the user's query")
    actionable_suggestions: list[str] = Field(default_factory=list, description="Suggested voice or desktop automation commands based on the current screen")
    raw_markdown: Optional[str] = Field(default=None, description="Detailed explanatory markdown text")


class ScreenVisionAnalyzer:
    """Captures screenshots and locates controls visually via Gemini Multimodal."""

    def __init__(self, model_name: str = "gemini-2.5-flash") -> None:
        self.model_name = model_name

    def capture_screenshot(self, monitor_index: int = 1) -> Tuple[Image.Image, Tuple[int, int]]:
        """Capture screenshot of the specified monitor using mss.

        Returns:
            (PIL Image, (screen_width, screen_height))
        """
        with mss() as sct:
            # monitor 1 is primary display
            monitors = sct.monitors
            mon = monitors[monitor_index] if len(monitors) > monitor_index else monitors[0]
            sct_img = sct.grab(mon)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img, (mon["width"], mon["height"])

    def locate_element_coordinates(
        self, target_description: str
    ) -> Optional[Tuple[int, int]]:
        """Find the screen pixel coordinates (x, y) of a control via visual reasoning,
        with multi-model fallback and geometric active-window recovery when quotas are exhausted.
        """
        key = get_gemini_api_key()
        if not key:
            logger.warning("Vision fallback skipped: No Gemini API key configured.")
            return self._fallback_active_window_coordinates(target_description)

        candidate_models = [self.model_name]
        for m in ("gemini-2.0-flash", "gemini-1.5-flash"):
            if m not in candidate_models:
                candidate_models.append(m)

        image = None
        width, height = (1920, 1080)
        try:
            image, (width, height) = self.capture_screenshot()
        except Exception as cap_err:
            logger.debug("Failed capturing screenshot for vision: %s", cap_err)

        if image is not None:
            prompt = (
                f"You are a computer vision assistant for desktop UI automation on Windows 11.\n"
                f"Locate the UI element, button, card, profile, icon, avatar, tab, or text described as: '{target_description}'.\n"
                f"Carefully search the screenshot for matching text (e.g. names, headings, labels), visual icons, or avatars.\n"
                f"Identify its bounding box on a normalized 0 to 1000 scale [ymin, xmin, ymax, xmax] where (0,0) is top-left and (1000, 1000) is bottom-right."
            )

            for model_to_try in candidate_models:
                try:
                    from google import genai
                    from google.genai import types

                    client = genai.Client(api_key=key)
                    response = client.models.generate_content(
                        model=model_to_try,
                        contents=[image, prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=ScreenVisionResponse,
                            temperature=0.1,
                        ),
                    )

                    res: ScreenVisionResponse = response.parsed
                    if res and res.elements:
                        best = res.elements[0]
                        ymin, xmin, ymax, xmax = best.box_2d
                        abs_x = int(((xmin + xmax) / 2.0 / 1000.0) * width)
                        abs_y = int(((ymin + ymax) / 2.0 / 1000.0) * height)
                        logger.info("Vision found '%s' at pixel center (%d, %d) using %s", target_description, abs_x, abs_y, model_to_try)
                        return abs_x, abs_y

                except Exception as exc:
                    err_str = str(exc)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        logger.warning("Gemini model '%s' quota exhausted (429). Trying next fallback...", model_to_try)
                        continue
                    else:
                        logger.error("Vision screen analysis failed on %s: %s", model_to_try, exc)
                        break

        # Fallback to active window geometric coordinates when vision is unavailable/exhausted
        logger.info("Falling back to active window geometric coordinates for '%s'...", target_description)
        return self._fallback_active_window_coordinates(target_description)

    def _fallback_active_window_coordinates(self, target_description: str) -> Optional[Tuple[int, int]]:
        """Fallback when vision API is rate-limited: locates active window center or child control."""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd or not win32gui.IsWindowVisible(hwnd):
                return None
            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            w = right - left
            h = bottom - top
            if w <= 50 or h <= 50:
                return None

            # Collect visible child controls if any
            children = []
            def enum_cb(child_hwnd, _):
                if win32gui.IsWindowVisible(child_hwnd):
                    crect = win32gui.GetWindowRect(child_hwnd)
                    cw = crect[2] - crect[0]
                    ch = crect[3] - crect[1]
                    if 25 <= cw < w and 25 <= ch < h:
                        children.append((crect[1], crect[0], (crect[0] + crect[2]) // 2, (crect[1] + crect[3]) // 2))
                return True
            try:
                win32gui.EnumChildWindows(hwnd, enum_cb, None)
            except Exception:
                pass

            if children:
                # Sort children top-to-bottom, left-to-right
                children.sort(key=lambda c: (c[0] // 30, c[1]))
                target_lower = target_description.lower()
                idx = 0
                if "second" in target_lower or "2nd" in target_lower:
                    idx = min(1, len(children) - 1)
                elif "third" in target_lower or "3rd" in target_lower:
                    idx = min(2, len(children) - 1)
                elif "last" in target_lower:
                    idx = len(children) - 1
                center_x, center_y = children[idx][2], children[idx][3]
                logger.info("Active window child control fallback picked (%d, %d)", center_x, center_y)
                return center_x, center_y

            # Active window center fallback
            center_x = left + w // 2
            center_y = top + h // 2
            logger.info("Active window geometric center fallback picked (%d, %d)", center_x, center_y)
            return center_x, center_y
        except Exception as exc:
            logger.debug("Active window coordinate fallback failed: %s", exc)
            return None

    def analyze_screen(
        self, query: str = "Summarize the active screen and key visible content"
    ) -> Optional[ScreenAnalysisResult]:
        """Perform deep visual understanding and Q&A over the live desktop screen."""
        key = get_gemini_api_key()
        if not key:
            logger.warning("Screen analysis skipped: No Gemini API key configured.")
            return None

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key)
            image, _ = self.capture_screenshot()

            prompt = (
                "You are Vyoma Vision Copilot, an intelligent visual assistant analyzing the user's active Windows desktop.\n"
                f"User Request / Question: \"{query}\"\n"
                "Analyze the attached live desktop screenshot thoroughly:\n"
                "1. Identify what application(s) and documents/tabs are visible.\n"
                "2. Provide key findings, text snippets, or direct answers to the user's question.\n"
                "3. Provide 2-4 concrete, actionable voice automation commands the user could say right now to interact with this screen."
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=[image, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ScreenAnalysisResult,
                    temperature=0.2,
                ),
            )

            result: ScreenAnalysisResult = response.parsed
            if result:
                logger.info("Screen visual analysis succeeded with model '%s'", self.model_name)
                return result
            return None

        except Exception as exc:
            logger.error("Screen visual analysis failed: %s", exc)
            return None

    def detect_screen_elements(
        self, query: str = "All interactive buttons, menus, text fields, and icons"
    ) -> List[Dict[str, Any]]:
        """Identify key UI elements visually and return their bounding boxes and centers for UI overlay."""
        key = get_gemini_api_key()
        if not key:
            return []

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key)
            image, (width, height) = self.capture_screenshot()

            prompt = (
                f"Identify visible interactive UI controls matching: '{query}'.\n"
                f"For each control, provide a descriptive label and bounding box [ymin, xmin, ymax, xmax] on a 0 to 1000 scale."
            )

            target_model = self.model_name if "gemma" not in self.model_name.lower() else "gemini-2.5-flash"
            response = client.models.generate_content(
                model=target_model,
                contents=[image, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ScreenVisionResponse,
                    temperature=0.1,
                ),
            )

            res: ScreenVisionResponse = response.parsed
            if not res or not res.elements:
                return []

            results = []
            for el in res.elements[:15]:
                ymin, xmin, ymax, xmax = el.box_2d
                abs_x = int(((xmin + xmax) / 2.0 / 1000.0) * width)
                abs_y = int(((ymin + ymax) / 2.0 / 1000.0) * height)
                results.append({
                    "label": el.label,
                    "box_2d": el.box_2d,
                    "normalized_box": [ymin / 1000.0, xmin / 1000.0, ymax / 1000.0, xmax / 1000.0],
                    "pixel_center": [abs_x, abs_y],
                    "confidence": el.confidence,
                })
            return results
        except Exception as exc:
            logger.error("Failed to detect screen elements: %s", exc)
            return []

    def inspect_point(
        self, x: int, y: int, query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Inspect what UI control, text, or icon is located at physical screen coordinates (x, y)."""
        key = get_gemini_api_key()
        if not key:
            return {"error": "Gemini API key not configured"}

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key)
            image, (width, height) = self.capture_screenshot()

            norm_x = int((x / max(1, width)) * 1000)
            norm_y = int((y / max(1, height)) * 1000)

            prompt = (
                f"You are Vyoma Vision Inspector analyzing a live Windows 11 desktop screenshot.\n"
                f"The user clicked at exact screen coordinates (X={x}, Y={y}) which corresponds to normalized position "
                f"[y={norm_y}, x={norm_x}] on a 0-1000 scale.\n"
            )
            if query:
                prompt += f"User specific question: '{query}'\n"
            prompt += (
                "Analyze the exact element, control, button, text, or window under or nearest to this point.\n"
                "Return JSON with:\n"
                "- 'element_name': Name or text of the element at that spot\n"
                "- 'element_type': button, input, tab, icon, text, menu, link, canvas\n"
                "- 'app_name': Likely active application\n"
                "- 'description': What clicking this control or reading this section does\n"
                "- 'suggested_voice_command': Natural voice phrase to interact with it\n"
                "- 'extracted_text': Any text visible directly on or adjacent to this element\n"
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[image, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            text_resp = response.text.strip() if response and response.text else "{}"
            clean = re.sub(r"^```(?:json)?\s*", "", text_resp, flags=re.MULTILINE)
            clean = re.sub(r"```$", "", clean.strip(), flags=re.MULTILINE).strip()
            data = json.loads(clean)
            data["coords"] = {"x": x, "y": y, "norm_x": norm_x, "norm_y": norm_y}
            return data
        except Exception as exc:
            logger.error("Failed to inspect screen point: %s", exc)
            return {"error": str(exc), "coords": {"x": x, "y": y}}

    def extract_screen_text(self) -> Dict[str, Any]:
        """Perform multimodal OCR to extract all structured text, code snippets, and tables from the screen."""
        key = get_gemini_api_key()
        if not key:
            return {"error": "Gemini API key not configured"}

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key)
            image, _ = self.capture_screenshot()

            prompt = (
                "You are an expert OCR and screen text extraction engine.\n"
                "Read the attached desktop screenshot and extract all legible text.\n"
                "Structure the output in JSON with:\n"
                "- 'full_text': Complete plain text transcript in reading order\n"
                "- 'code_snippets': List of code blocks found (with language if detected)\n"
                "- 'tables': List of any tabular data represented as Markdown tables\n"
                "- 'detected_urls_or_paths': List of URLs, file paths, or email addresses visible\n"
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[image, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            text_resp = response.text.strip() if response and response.text else "{}"
            clean = re.sub(r"^```(?:json)?\s*", "", text_resp, flags=re.MULTILINE)
            clean = re.sub(r"```$", "", clean.strip(), flags=re.MULTILINE).strip()
            return json.loads(clean)
        except Exception as exc:
            logger.error("Failed to extract screen text: %s", exc)
            return {"error": str(exc)}

