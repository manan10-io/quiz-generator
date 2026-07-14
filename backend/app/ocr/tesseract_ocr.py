"""
tesseract_ocr.py — Local Tesseract OCR engine implementation.

Uses pytesseract for the Python binding. Supports multi-language OCR
(English + Hindi + Gujarati simultaneously via Tesseract's native "+"
syntax), confidence scoring via Tesseract's word-level TSV output, and
graceful degradation when a requested language pack isn't installed on
the host (falls back to whichever requested languages ARE available,
rather than failing outright).
"""

import io
import logging
from functools import lru_cache

import pytesseract
from PIL import Image

from app.config import settings
from app.ocr.base_ocr import OCREngine, OCRResult
from app.ocr.preprocessor import preprocessor

logger = logging.getLogger(__name__)


class TesseractOCR(OCREngine):
    name = "tesseract"

    def __init__(self):
        if settings.TESSERACT_CMD != "tesseract":
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    def is_available(self) -> bool:
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception as e:
            logger.error("Tesseract binary not found or not executable: %s", e)
            return False

    @lru_cache(maxsize=1)
    def _installed_languages(self) -> set[str]:
        """Query Tesseract for which language packs are actually installed."""
        try:
            return set(pytesseract.get_languages(config=""))
        except Exception as e:
            logger.warning("Could not query installed Tesseract languages: %s", e)
            return {"eng"}

    def _resolve_languages(self, requested: list[str]) -> tuple[list[str], list[str]]:
        """
        Filters the requested language list down to what's actually installed.
        Returns (usable_languages, missing_languages). Always guarantees at
        least ["eng"] is returned if it's installed, since that's the
        universal fallback.
        """
        installed = self._installed_languages()
        usable = [lang for lang in requested if lang in installed]
        missing = [lang for lang in requested if lang not in installed]

        if not usable:
            usable = ["eng"] if "eng" in installed else list(installed)[:1]

        return usable, missing

    def extract_text(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
        preprocess: bool = True,
    ) -> OCRResult:
        warnings: list[str] = []
        requested = languages or ["eng", "hin", "guj"]
        usable_langs, missing_langs = self._resolve_languages(requested)

        if missing_langs:
            warnings.append(
                f"Language pack(s) not installed on server: {', '.join(missing_langs)} "
                f"— install with 'apt-get install tesseract-ocr-{'  tesseract-ocr-'.join(missing_langs)}'. "
                f"Falling back to: {', '.join(usable_langs)}"
            )

        lang_string = "+".join(usable_langs)

        try:
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            return OCRResult(
                text="",
                confidence=0.0,
                engine=self.name,
                languages_used=usable_langs,
                warnings=[f"Could not open image: {e}"],
            )

        if preprocess:
            try:
                proc_result = preprocessor.process(image)
                image = proc_result.image
                if proc_result.skew_angle_corrected != 0:
                    warnings.append(
                        f"Corrected {proc_result.skew_angle_corrected:.1f}° skew"
                    )
            except Exception as e:
                logger.warning("Preprocessing failed, using raw image: %s", e)
                warnings.append("Image preprocessing failed — used raw image")

        # PSM 6: "Assume a single uniform block of text" — best general choice
        # for question papers (paragraphs of mixed question/option text).
        # OEM 1: LSTM-only engine — more accurate than legacy on modern Tesseract.
        tess_config = "--psm 6 --oem 1"

        try:
            text = pytesseract.image_to_string(
                image, lang=lang_string, config=tess_config
            )
        except pytesseract.TesseractError as e:
            return OCRResult(
                text="",
                confidence=0.0,
                engine=self.name,
                languages_used=usable_langs,
                warnings=warnings + [f"Tesseract error: {e}"],
            )

        confidence = self._compute_confidence(image, lang_string, tess_config)
        word_count = len(text.split())

        if word_count == 0:
            warnings.append("No text detected — image may be blank, too low-resolution, or non-text content")
        elif confidence < 50:
            warnings.append(f"Low OCR confidence ({confidence:.0f}%) — text may contain errors")

        return OCRResult(
            text=text,
            confidence=confidence,
            engine=self.name,
            languages_used=usable_langs,
            warnings=warnings,
            word_count=word_count,
        )

    def _compute_confidence(self, image: Image.Image, lang: str, config: str) -> float:
        """
        Computes mean word-level confidence using Tesseract's TSV output.
        Returns 0–100. Words with confidence -1 (non-text regions) are excluded.
        """
        try:
            data = pytesseract.image_to_data(
                image, lang=lang, config=config,
                output_type=pytesseract.Output.DICT,
            )
            confidences = [
                int(c) for c in data.get("conf", [])
                if str(c).lstrip("-").isdigit() and int(c) >= 0
            ]
            if not confidences:
                return 0.0
            return sum(confidences) / len(confidences)
        except Exception as e:
            logger.warning("Confidence computation failed: %s", e)
            return 50.0  # neutral default — don't block the pipeline on this


# ─── Singleton ────────────────────────────────────────────────────────────────
tesseract_ocr = TesseractOCR()
