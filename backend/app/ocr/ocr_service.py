"""
ocr_service.py — Top-level OCR orchestrator.

Decision tree:
  1. If input is a PDF → render pages with PDFRenderer → OCR each page
  2. For each image:
     a. Preprocess (deskew, denoise, threshold) via ImagePreprocessor
     b. Run Tesseract
     c. If Tesseract confidence < LOW_CONFIDENCE_THRESHOLD
        AND Google Vision is configured → retry with Vision API
     d. Merge page texts in order
  3. Return combined text + merged OCRResult metadata

This gives the best possible accuracy:
  - Fast local Tesseract for the majority of clean scans
  - Cloud Vision fallback only when Tesseract clearly struggles
"""

import io
import logging
from dataclasses import dataclass, field

from PIL import Image

from app.config import settings
from app.ocr.base_ocr import OCRResult
from app.ocr.tesseract_ocr import tesseract_ocr
from app.ocr.vision_ocr import vision_ocr
from app.ocr.preprocessor import preprocessor
from app.ocr.language_detector import language_detector
from app.ocr.pdf_renderer import pdf_renderer

logger = logging.getLogger(__name__)

# Below this Tesseract confidence score, Vision API fallback is attempted
LOW_CONFIDENCE_THRESHOLD = 60.0


@dataclass
class OCRServiceResult:
    text: str
    page_count: int
    engine_used: str                        # "tesseract" | "google_vision" | "mixed"
    page_results: list[OCRResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    languages_detected: list[str] = field(default_factory=list)

    @property
    def mean_confidence(self) -> float:
        if not self.page_results:
            return 0.0
        return sum(r.confidence for r in self.page_results) / len(self.page_results)


class OCRService:

    def extract_from_image_bytes(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
    ) -> OCRServiceResult:
        """OCR a single image (PNG, JPEG, WEBP, etc.) from raw bytes."""
        page_result = self._ocr_single_image(image_bytes, languages or [])

        langs_detected = language_detector.detect_scripts(page_result.text)
        lang_list: list[str] = []
        if langs_detected.has_english:
            lang_list.append("English")
        if langs_detected.has_hindi:
            lang_list.append("Hindi")
        if langs_detected.has_gujarati:
            lang_list.append("Gujarati")

        return OCRServiceResult(
            text=page_result.text,
            page_count=1,
            engine_used=page_result.engine,
            page_results=[page_result],
            warnings=page_result.warnings,
            languages_detected=lang_list,
        )

    def extract_from_pdf_bytes(
        self,
        pdf_bytes: bytes,
        languages: list[str] | None = None,
    ) -> OCRServiceResult:
        """Render PDF pages and OCR each one, then stitch the text together."""
        all_warnings: list[str] = []
        page_results: list[OCRResult] = []
        text_parts: list[str] = []

        try:
            pages = pdf_renderer.render_pages(pdf_bytes)
        except RuntimeError as e:
            return OCRServiceResult(
                text="",
                page_count=0,
                engine_used="tesseract",
                warnings=[str(e)],
            )

        for rendered_page in pages:
            buf = io.BytesIO()
            rendered_page.image.save(buf, format="JPEG", quality=92)
            page_bytes = buf.getvalue()

            result = self._ocr_single_image(page_bytes, languages or [])
            page_results.append(result)
            all_warnings.extend(result.warnings)

            if result.text.strip():
                text_parts.append(
                    f"[Page {rendered_page.page_number}]\n{result.text}"
                )

        combined_text = "\n\n".join(text_parts)
        engines_used = {r.engine for r in page_results}
        engine_label = list(engines_used)[0] if len(engines_used) == 1 else "mixed"

        langs_detected = language_detector.detect_scripts(combined_text)
        lang_list = (
            (["English"] if langs_detected.has_english else [])
            + (["Hindi"] if langs_detected.has_hindi else [])
            + (["Gujarati"] if langs_detected.has_gujarati else [])
        )

        return OCRServiceResult(
            text=combined_text,
            page_count=len(pages),
            engine_used=engine_label,
            page_results=page_results,
            warnings=all_warnings,
            languages_detected=lang_list,
        )

    # ─── Internal helpers ─────────────────────────────────────────────────────

    def _ocr_single_image(
        self, image_bytes: bytes, user_languages: list[str]
    ) -> OCRResult:
        """
        OCR one image with engine selection and optional Vision API fallback.
        """
        # Determine which Tesseract language packs to request
        recommended = language_detector.recommend_tesseract_languages(
            user_hint=user_languages or None
        )

        # Run Tesseract first (always — it's free and local)
        tess_result = tesseract_ocr.extract_text(
            image_bytes,
            languages=recommended,
            preprocess=True,
        )

        # If Tesseract is confident enough (or Vision isn't available), return now
        if (
            not tess_result.is_low_confidence
            or not vision_ocr.is_available()
        ):
            return tess_result

        # Tesseract low confidence → try Vision API as fallback
        logger.info(
            "Tesseract confidence %.1f%% below threshold — trying Google Vision",
            tess_result.confidence,
        )
        vision_result = vision_ocr.extract_text(image_bytes, languages=recommended)

        if vision_result.is_empty:
            # Vision also found nothing — stick with Tesseract's (possibly
            # imperfect) output rather than returning empty text
            vision_result.warnings.append(
                "Vision API returned no text — keeping Tesseract output"
            )
            return tess_result

        # Return the result with higher confidence
        if vision_result.confidence >= tess_result.confidence:
            vision_result.warnings.insert(
                0,
                f"Used Google Vision (confidence {vision_result.confidence:.0f}%) "
                f"over Tesseract ({tess_result.confidence:.0f}%)"
            )
            return vision_result

        return tess_result

    def _pil_to_bytes(self, image: Image.Image, fmt: str = "JPEG") -> bytes:
        buf = io.BytesIO()
        image.save(buf, format=fmt, quality=92)
        return buf.getvalue()


# ─── Singleton ────────────────────────────────────────────────────────────────
ocr_service = OCRService()
