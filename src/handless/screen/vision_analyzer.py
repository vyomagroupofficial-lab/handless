"""Computer Vision Screen Analyzer using mss and Gemini 2.5 Flash.

Provides visual fallback for applications without accessibility metadata (custom canvas,
games, poorly coded Electron apps). Captures fast screenshots and maps Gemini's
normalized 0-1000 bounding boxes back to physical Windows screen pixels.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple
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
        """Find the screen pixel coordinates (x, y) of a control via visual reasoning."""
        key = get_gemini_api_key()
        if not key:
            logger.warning("Vision fallback skipped: No Gemini API key configured.")
            return None

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key)
            image, (width, height) = self.capture_screenshot()

            prompt = (
                f"Locate the UI element described as: '{target_description}' in this application screenshot.\n"
                f"Identify its bounding box on a normalized 0 to 1000 scale [ymin, xmin, ymax, xmax]."
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=[image, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ScreenVisionResponse,
                    temperature=0.1,
                ),
            )

            res: ScreenVisionResponse = response.parsed
            if not res.elements:
                return None

            best = res.elements[0]
            ymin, xmin, ymax, xmax = best.box_2d

            # Convert 0-1000 normalized grid to actual screen pixels
            abs_x = int(((xmin + xmax) / 2.0 / 1000.0) * width)
            abs_y = int(((ymin + ymax) / 2.0 / 1000.0) * height)

            logger.info("Vision found '%s' at pixel center (%d, %d)", target_description, abs_x, abs_y)
            return abs_x, abs_y

        except Exception as exc:
            logger.error("Vision screen analysis failed: %s", exc)
            return None
