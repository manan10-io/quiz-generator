"""
vision_ocr.py — Google Cloud Vision API OCR engine.

Used as a cloud fallback when Tesseract confidence is below threshold,
or when explicitly configured via USE_GOOGLE_VISION=true.

Vision advantages over local Tesseract:
  - Much more accurate on low-resolution / heavily degraded images
  - Better at handwritten text (not relevant for MCQ papers but useful edge case)
  - Handles mixed-script text without needing separate language packs
  - Returns bounding-box and paragraph structure information

The implementation wraps the Cloud Vision TEXT_DETECTION feature using the
REST API (not the Python client library) so it works without the heavy
google-cloud-vision package — just httpx and a simple API key.
"""

import base64
import logging
from typing import Any

import httpx

from app.config import settings
from app.ocr.base_ocr import OCREngine, OCRResult

logger = logging.getLogger(__name__)

VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"


class GoogleVisionOCR(OCREngine):
    name = "google_vision"

    def is_available(self) -> bool:
        return bool(settings.GOOGLE_VISION_API_KEY and settings.USE_GOOGLE_VISION)

    def extract_text(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
    ) -> OCRResult:
        if not self.is_available():
            return OCRResult(
                text="",
                confidence=0.0,
                engine=self.name,
                warnings=["Google Vision API not configured (GOOGLE_VISION_API_KEY missing)"],
            )

        # Map Tesseract-style codes to BCP-47 tags Vision expects
        lang_hints = self._map_languages(languages or ["en", "hi", "gu"])
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "requests": [
                {
                    "image": {"content": b64_image},
                    "features": [{"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 1}],
                    "imageContext": {"languageHints": lang_hints},
                }
            ]
        }

        try:
            response = httpx.post(
                VISION_API_URL,
                json=payload,
                params={"key": settings.GOOGLE_VISION_API_KEY},
                timeout=30.0,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        except httpx.HTTPStatusError as e:
            err = f"Vision API HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(err)
            return OCRResult(text="", confidence=0.0, engine=self.name, warnings=[err])
        except httpx.RequestError as e:
            err = f"Vision API network error: {e}"
            logger.error(err)
            return OCRResult(text="", confidence=0.0, engine=self.name, warnings=[err])

        return self._parse_response(data, lang_hints)

    def _parse_response(self, data: dict[str, Any], lang_hints: list[str]) -> OCRResult:
        responses = data.get("responses", [])
        if not responses:
            return OCRResult(text="", confidence=0.0, engine=self.name,
                             warnings=["Empty response from Vision API"])

        first = responses[0]

        if "error" in first:
            err = first["error"].get("message", "Unknown Vision API error")
            return OCRResult(text="", confidence=0.0, engine=self.name, warnings=[err])

        # fullTextAnnotation gives clean paragraph-structured text
        full_annotation = first.get("fullTextAnnotation")
        if full_annotation:
            text = full_annotation.get("text", "")
            confidence = self._extract_confidence(full_annotation)
        else:
            # Fall back to simple textAnnotations list
            annotations = first.get("textAnnotations", [])
            text = annotations[0].get("description", "") if annotations else ""
            confidence = 80.0  # Vision doesn't expose confidence for simple TEXT_DETECTION

        warnings: list[str] = []
        if not text.strip():
            warnings.append("No text detected by Google Vision API")

        return OCRResult(
            text=text,
            confidence=confidence,
            engine=self.name,
            languages_used=lang_hints,
            warnings=warnings,
            word_count=len(text.split()),
        )

    def _extract_confidence(self, full_annotation: dict[str, Any]) -> float:
        """
        Average word confidence across all pages. The fullTextAnnotation
        contains a pages→blocks→paragraphs→words→symbols hierarchy, each
        with a boundingPoly and an optional confidence field.
        """
        confidences: list[float] = []
        for page in full_annotation.get("pages", []):
            for block in page.get("blocks", []):
                for para in block.get("paragraphs", []):
                    for word in para.get("words", []):
                        conf = word.get("confidence")
                        if conf is not None:
                            confidences.append(float(conf) * 100.0)

        if not confidences:
            return 85.0  # Vision is generally high confidence; use generous default
        return sum(confidences) / len(confidences)

    def _map_languages(self, languages: list[str]) -> list[str]:
        """Convert Tesseract-style codes to BCP-47 tags expected by Vision."""
        MAPPING = {
            "eng": "en", "hin": "hi", "guj": "gu",
            "en": "en", "hi": "hi", "gu": "gu",
        }
        return [MAPPING.get(lang, lang) for lang in languages]


# ─── Singleton ────────────────────────────────────────────────────────────────
vision_ocr = GoogleVisionOCR()
