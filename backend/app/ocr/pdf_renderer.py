"""
pdf_renderer.py — Converts PDF pages into high-resolution images for OCR.

PDF text-layer extraction (pdfplumber / pymupdf) is always attempted first
in parser_service.py. This module is called only when that extraction
returns fewer than 50 characters (i.e. the PDF is likely scanned / image-based).

Strategy:
  - Uses PyMuPDF (fitz) for rendering because it's much faster than
    pdf2image + poppler, handles encrypted/damaged PDFs better, and does
    not require a system-level poppler binary.
  - Renders at 300 DPI (2× the default 150 DPI) for Tesseract's optimal range.
  - Returns individual page images as PIL Image objects so the caller can
    preprocess each page independently before OCR.
"""

import io
import logging
from dataclasses import dataclass

from PIL import Image

logger = logging.getLogger(__name__)

# DPI at which to render each PDF page for OCR
# Tesseract accuracy peaks around 300 DPI and diminishes above ~400 DPI
RENDER_DPI = 300


@dataclass
class RenderedPage:
    page_number: int       # 1-based
    image: Image.Image
    width_px: int
    height_px: int


class PDFRenderer:

    def render_pages(self, pdf_bytes: bytes) -> list[RenderedPage]:
        """
        Render all pages of a PDF to PIL Images at RENDER_DPI.
        Returns pages in reading order. Raises RuntimeError if fitz unavailable.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise RuntimeError(
                "PyMuPDF is required for PDF OCR. Install with: pip install pymupdf"
            ) from e

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            raise RuntimeError(f"Could not open PDF: {e}") from e

        pages: list[RenderedPage] = []
        # Scale factor: (target_dpi / 72) — PyMuPDF's default resolution is 72 DPI
        scale = RENDER_DPI / 72.0
        matrix = fitz.Matrix(scale, scale)

        for page_idx in range(doc.page_count):
            try:
                page = doc[page_idx]
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                img_bytes = pix.tobytes("jpeg", jpg_quality=92)
                image = Image.open(io.BytesIO(img_bytes))
                pages.append(RenderedPage(
                    page_number=page_idx + 1,
                    image=image,
                    width_px=pix.width,
                    height_px=pix.height,
                ))
            except Exception as e:
                logger.warning("Failed to render PDF page %d: %s", page_idx + 1, e)

        doc.close()

        if not pages:
            raise RuntimeError("No pages could be rendered from PDF")

        return pages

    def render_page_bytes(self, pdf_bytes: bytes, page_number: int = 1) -> bytes:
        """
        Render a single PDF page to JPEG bytes. page_number is 1-based.
        Useful for thumbnail/preview generation.
        """
        pages = self.render_pages(pdf_bytes)
        if page_number < 1 or page_number > len(pages):
            raise ValueError(
                f"Page {page_number} out of range (PDF has {len(pages)} pages)"
            )
        page = pages[page_number - 1]
        buf = io.BytesIO()
        page.image.save(buf, format="JPEG", quality=92)
        return buf.getvalue()


# ─── Singleton ────────────────────────────────────────────────────────────────
pdf_renderer = PDFRenderer()
