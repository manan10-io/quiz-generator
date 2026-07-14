"""
base_ocr.py — Abstract interface that every OCR engine implementation must
satisfy. This lets the orchestrating OCRService swap between Tesseract
(local, free) and Google Vision (cloud, paid, higher accuracy) without
the caller needing to know which one is active.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class OCRResult:
    """Normalised result returned by every OCR engine."""

    text: str
    confidence: float          # 0.0–100.0, engine's own confidence score
    engine: str                 # "tesseract" | "google_vision"
    languages_used: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    word_count: int = 0

    @property
    def is_low_confidence(self) -> bool:
        """Below this threshold, the caller should consider a fallback engine."""
        return self.confidence < 60.0

    @property
    def is_empty(self) -> bool:
        return len(self.text.strip()) < 10


class OCREngine(ABC):
    """Common interface for all OCR backends."""

    name: str = "base"

    @abstractmethod
    def extract_text(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
    ) -> OCRResult:
        """
        Run OCR on raw image bytes (PNG/JPEG/etc) and return an OCRResult.
        `languages` are ISO-639 style hints (e.g. ["eng", "hin", "guj"]
        for Tesseract, or ["en", "hi", "gu"] for Vision — each subclass
        maps these to whatever format its underlying API expects).
        """
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this engine is configured and ready to use (e.g. API key set)."""
        raise NotImplementedError
