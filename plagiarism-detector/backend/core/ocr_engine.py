"""
OCR Engine - Extract text from uploaded images using Tesseract/PIL.
Supports: PNG, JPG, JPEG, TIFF, BMP, WEBP
"""

import base64
import io
import os
from typing import Optional, Tuple

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    import os, sys

    # Windows: auto-locate Tesseract
    if sys.platform == "win32":
        win_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.environ.get("TESSERACT_CMD", ""),
        ]
        for p in win_paths:
            if p and os.path.isfile(p):
                pytesseract.pytesseract.tesseract_cmd = p
                break

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


def enhance_image_for_ocr(image) -> 'Image':
    """Pre-process image to improve OCR accuracy."""
    # Convert to grayscale
    img = image.convert('L')
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    # Sharpen
    img = img.filter(ImageFilter.SHARPEN)
    # Resize if too small
    w, h = img.size
    if w < 300 or h < 300:
        scale = max(300 / w, 300 / h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return img


def extract_text_from_image_bytes(image_bytes: bytes) -> Tuple[str, dict]:
    """
    Extract text from raw image bytes.
    Returns (extracted_text, metadata)
    """
    if not PIL_AVAILABLE:
        return "", {"error": "PIL not available", "confidence": 0}

    try:
        img = Image.open(io.BytesIO(image_bytes))
        original_size = img.size
        
        if TESSERACT_AVAILABLE:
            enhanced = enhance_image_for_ocr(img)
            # Get detailed OCR data
            data = pytesseract.image_to_data(
                enhanced,
                output_type=pytesseract.Output.DICT,
                config='--psm 3'
            )
            # Filter confident words
            confidences = [int(c) for c in data['conf'] if int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            text = pytesseract.image_to_string(enhanced, config='--psm 3')
            text = text.strip()
            
            return text, {
                "ocr_engine": "tesseract",
                "confidence": round(avg_confidence, 1),
                "original_size": original_size,
                "word_count": len(text.split()),
                "success": bool(text)
            }
        else:
            # Fallback: basic text extraction without OCR
            return "", {
                "error": "Tesseract not installed",
                "confidence": 0,
                "success": False,
                "message": "Install tesseract-ocr for image support"
            }

    except Exception as e:
        return "", {"error": str(e), "confidence": 0, "success": False}


def extract_text_from_base64(b64_data: str, mime_type: str = "image/jpeg") -> Tuple[str, dict]:
    """Extract text from base64-encoded image."""
    try:
        # Remove data URL prefix if present
        if ',' in b64_data:
            b64_data = b64_data.split(',', 1)[1]
        image_bytes = base64.b64decode(b64_data)
        return extract_text_from_image_bytes(image_bytes)
    except Exception as e:
        return "", {"error": f"Base64 decode failed: {e}", "success": False}


def extract_text_from_file(filepath: str) -> Tuple[str, dict]:
    """Extract text from image file path."""
    try:
        with open(filepath, 'rb') as f:
            return extract_text_from_image_bytes(f.read())
    except Exception as e:
        return "", {"error": str(e), "success": False}


def is_supported_image(filename: str) -> bool:
    ext = os.path.splitext(filename.lower())[1]
    return ext in {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.webp', '.gif'}
