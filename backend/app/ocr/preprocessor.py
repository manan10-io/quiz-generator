"""
preprocessor.py — Image preprocessing pipeline to maximise OCR accuracy on
scanned question papers and screenshots.

Pipeline stages (each individually toggleable):
  1. Grayscale conversion
  2. Resize to optimal DPI for OCR (Tesseract performs best around 300 DPI)
  3. Denoising (removes scanner speckle / JPEG artifacts)
  4. Deskew (corrects rotated scans — common with flatbed/phone-camera scans)
  5. Adaptive thresholding (binarisation — handles uneven lighting/shadows)
  6. Contrast enhancement (CLAHE — helps faint pencil-photocopy text)
"""

import logging
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Tesseract's accuracy drops off sharply below ~150 DPI and plateaus above
# ~300 DPI, so we normalise every image to this target.
TARGET_DPI = 300
# Most camera-phone photos default to 72 DPI metadata regardless of actual
# pixel density, so we estimate "effective DPI" from pixel width instead.
ASSUMED_PAGE_WIDTH_INCHES = 8.27  # A4 width


@dataclass
class PreprocessResult:
    image: Image.Image
    skew_angle_corrected: float
    was_resized: bool
    original_size: tuple[int, int]
    final_size: tuple[int, int]


class ImagePreprocessor:
    """Prepares a raw scanned/photographed image for OCR."""

    def process(
        self,
        image: Image.Image,
        deskew: bool = True,
        denoise: bool = True,
        threshold: bool = True,
        enhance_contrast: bool = True,
    ) -> PreprocessResult:
        original_size = image.size

        # 1. Ensure RGB (handles RGBA/P/L source modes uniformly)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # 2. Resize to target DPI if the image is too small for reliable OCR
        image, was_resized = self._resize_to_target_dpi(image)

        # 3. Convert to OpenCV grayscale array
        cv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)

        # 4. Deskew
        skew_angle = 0.0
        if deskew:
            cv_img, skew_angle = self._deskew(cv_img)

        # 5. Denoise
        if denoise:
            cv_img = cv2.fastNlMeansDenoising(cv_img, h=10, templateWindowSize=7, searchWindowSize=21)

        # 6. Contrast enhancement (CLAHE handles uneven lighting better than
        #    a global histogram equalisation would)
        if enhance_contrast:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cv_img = clahe.apply(cv_img)

        # 7. Adaptive threshold (binarise)
        if threshold:
            cv_img = cv2.adaptiveThreshold(
                cv_img, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=31,
                C=10,
            )

        result_image = Image.fromarray(cv_img)

        return PreprocessResult(
            image=result_image,
            skew_angle_corrected=skew_angle,
            was_resized=was_resized,
            original_size=original_size,
            final_size=result_image.size,
        )

    # ─── DPI normalisation ────────────────────────────────────────────────────

    def _resize_to_target_dpi(self, image: Image.Image) -> tuple[Image.Image, bool]:
        """
        Scale the image up if it's smaller than what TARGET_DPI would imply
        for a standard page width. Never downscales — large source images
        are left as-is since extra resolution doesn't hurt Tesseract.
        """
        target_width = int(ASSUMED_PAGE_WIDTH_INCHES * TARGET_DPI)
        current_width = image.width

        if current_width >= target_width:
            return image, False

        scale = target_width / current_width
        # Guard against degenerate tiny thumbnails causing absurd upscaling
        scale = min(scale, 4.0)

        new_size = (int(image.width * scale), int(image.height * scale))
        resized = image.resize(new_size, Image.LANCZOS)
        return resized, True

    # ─── Deskew ───────────────────────────────────────────────────────────────

    def _deskew(self, gray: np.ndarray) -> tuple[np.ndarray, float]:
        """
        Detects and corrects small rotational skew using the minimum-area
        bounding rectangle of foreground (text) pixels. Effective for skews
        up to ~15 degrees, which covers the vast majority of scanned papers
        and phone-camera photos of question sheets.
        """
        # Binarise just for angle detection (Otsu threshold)
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        coords = np.column_stack(np.where(bw > 0))
        if coords.shape[0] < 50:
            # Not enough foreground pixels to reliably estimate an angle
            return gray, 0.0

        angle = cv2.minAreaRect(coords)[-1]

        # cv2.minAreaRect returns angle in (-90, 0]; normalise to a signed
        # rotation that's meaningful for cv2.warpAffine (small corrections only)
        if angle < -45:
            angle = 90 + angle

        # Ignore negligible skew — avoids introducing blur from unnecessary
        # rotation on already-straight images
        if abs(angle) < 0.3:
            return gray, 0.0

        # Cap correction to a sane range; beyond this the page is likely
        # genuinely rotated 90°, which deskew-by-small-angle can't fix
        if abs(angle) > 15:
            logger.warning("Skew angle %.1f° exceeds correction range — skipping", angle)
            return gray, 0.0

        (h, w) = gray.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            gray, rotation_matrix, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated, angle

    # ─── Convenience: bytes in, bytes out ────────────────────────────────────

    def process_bytes(self, image_bytes: bytes, **kwargs) -> bytes:
        """Process raw image bytes and return processed PNG bytes."""
        import io

        image = Image.open(io.BytesIO(image_bytes))
        result = self.process(image, **kwargs)

        buf = io.BytesIO()
        result.image.save(buf, format="PNG")
        return buf.getvalue()


# ─── Singleton ────────────────────────────────────────────────────────────────
preprocessor = ImagePreprocessor()
