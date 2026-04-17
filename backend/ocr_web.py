"""
ocr_web.py  —  Web-based OCR for NSU Transcript Extraction
=====================================================================
VERSION: 3.0.0 - Production Release with Azure Document Intelligence

Features:
1. Google Cloud Vision API (1000 free/month) - Most accurate
2. Azure Document Intelligence (99%+ accuracy) - Premium fallback
3. Native PDF text extraction - For digital PDFs
4. Improved table parsing logic
5. Department detection from NSU ID
6. Course validation against official catalog
7. Engine selection (google_vision, azure)

OCR Performance: Maximum accuracy mode enabled by default.
Both Google Vision and Azure use highest quality settings.
"""

__version__ = "3.0.0"

import os
import re
import io
import sys
import base64
import json
import tempfile
import warnings
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from pathlib import Path
from urllib import request as urllib_request
from urllib import parse as urllib_parse
from urllib.error import URLError, HTTPError

warnings.filterwarnings('ignore')

# Maximum accuracy configuration (hardcoded for best results)
# These values ensure highest quality OCR output
API_TIMEOUT = int(os.environ.get('API_TIMEOUT', 60))  # Allow more time for accurate processing
OCR_CONFIDENCE_THRESHOLD = 0.5  # Low threshold to capture all text, post-processing handles accuracy
MAX_CGPA = 4.0
MAX_CREDITS_PER_COURSE = 6
MAX_TOTAL_CREDITS = 200

# Google Vision maximum accuracy settings
GOOGLE_VISION_FEATURES = [
    {"type": "DOCUMENT_TEXT_DETECTION"}  # Best for structured documents like transcripts
]
GOOGLE_VISION_IMAGE_CONTEXT = {
    "languageHints": ["en"],  # English language hint for better accuracy
    "textDetectionParams": {
        "enableTextDetectionConfidenceScore": True
    }
}

# Setup logging
_logger = logging.getLogger(__name__)

# Load environment variables if dotenv is available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
except ImportError:
    pass

# Import course catalog for validation
try:
    from nsu_courses import COURSE_LOOKUP, get_course_info
    COURSE_CATALOG_AVAILABLE = True
except ImportError:
    COURSE_LOOKUP = {}
    COURSE_CATALOG_AVAILABLE = False
    def get_course_info(code):
        return None

# API Keys - Load from centralized config (no hardcoded fallbacks)
try:
    from app.config import get_settings
    _settings = get_settings()
    GOOGLE_VISION_API_KEY = _settings.GOOGLE_VISION_API_KEY
    # Azure credentials
    AZURE_DOC_INTELLIGENCE_KEY = getattr(_settings, 'AZURE_DOC_INTELLIGENCE_KEY', '') or ''
    AZURE_DOC_INTELLIGENCE_ENDPOINT = getattr(_settings, 'AZURE_DOC_INTELLIGENCE_ENDPOINT', '') or ''
    _logger.info("OCR module: Loaded settings from config")
except Exception as e:
    # Fallback to environment variables for backward compatibility
    _logger.warning(f"OCR module: Could not load from config ({e}), using env vars")
    GOOGLE_VISION_API_KEY = os.environ.get('GOOGLE_CLOUD_VISION_KEY') or os.environ.get('GOOGLE_VISION_API_KEY', '')
    AZURE_DOC_INTELLIGENCE_KEY = os.environ.get('AZURE_DOC_INTELLIGENCE_KEY', '')
    AZURE_DOC_INTELLIGENCE_ENDPOINT = os.environ.get('AZURE_DOC_INTELLIGENCE_ENDPOINT', '')

# Warn if no OCR provider is configured
if not GOOGLE_VISION_API_KEY and not AZURE_DOC_INTELLIGENCE_KEY:
    _logger.warning("No OCR API keys configured - OCR functionality will be limited")

# Import Azure OCR module
try:
    from ocr_azure import AzureDocIntelligence, azure_ocr
    AZURE_MODULE_AVAILABLE = True
except ImportError:
    AZURE_MODULE_AVAILABLE = False
    _logger.warning("Azure OCR module not available")

VALID_GRADES = {'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F', 'W', 'I', 'P', 'TR'}
COURSE_PATTERN = re.compile(r'^([A-Z]{2,4})(\d{3}[A-Z]?)$')
SEMESTER_PATTERN = re.compile(r'(Spring|Summer|Fall)\s*(\d{4})', re.IGNORECASE)

# Full-line pattern: matches "CSE115 3 A-" or "CSE 115  3.0  B+" format
# Note: Don't use \b at end because +/- are not word characters
FULL_LINE_PATTERN = re.compile(
    r'\b([A-Z]{2,4})\s*(\d{3}[A-Z]?)\s+(\d(?:\.\d)?)\s+([ABCDF][+-]?|W|I|P|TR)(?:\s|$)',
    re.IGNORECASE
)

# Table header detection patterns
TABLE_HEADER_PATTERNS = [
    re.compile(r'Course\s*(?:Code)?.*Credit.*Grade', re.IGNORECASE),
    re.compile(r'Subject.*(?:Credit|Cr\.?).*Grade', re.IGNORECASE),
]

# Extended course prefixes for any department
ALL_COURSE_PREFIXES = {
    'CSE', 'EEE', 'ECE', 'MAT', 'PHY', 'CHE', 'ENG', 'BEN', 'BIO',
    'ENV', 'ECO', 'BUS', 'ACT', 'FIN', 'MKT', 'MGT', 'MIS', 'HRM',
    'SOC', 'POL', 'HIS', 'PHI', 'ANT', 'PSY', 'ARC', 'LAW', 'ESL',
    'GEN', 'COM', 'MED', 'PHA', 'PUB', 'MPH', 'STA', 'IST', 'LIN',
    'JMS', 'CIS', 'MSC', 'NST', 'ART', 'MUS', 'THE', 'REL', 'GEO',
    'CHI', 'JPN', 'FRE', 'GER', 'SPA', 'ARA', 'BAN', 'URD', 'HIN',
    'ACC', 'MNS', 'BME', 'CEE', 'IPE', 'TEX', 'AER', 'NFS', 'PAD',  # PAD = Public Administration
}

# OCR corrections for common misreads (extended list)
# ═══════════════════════════════════════════════════════════════════════════════
# DEPARTMENT DETECTION FROM NSU ID
# ═══════════════════════════════════════════════════════════════════════════════

VALID_DEPARTMENTS = {
    # School of Engineering & Applied Science
    42: "CSE",   # Computer Science & Engineering
    43: "EEE",   # Electrical & Electronic Engineering
    44: "ECE",   # Electronic & Computer Engineering
    45: "ETE",   # Electronics & Telecommunications Engineering
    46: "ARC",   # Architecture
    47: "ENV",   # Environmental Science & Management
    
    # School of Business
    30: "BBA",   # Bachelor of Business Administration
    31: "MBA",   # Master of Business Administration
    
    # School of Arts and Social Science
    50: "ECO",   # Economics
    51: "ENG",   # English
    52: "POL",   # Political Science / Governance
    
    # School of Life Science
    60: "PHR",   # Pharmacy
    61: "PBH",   # Public Health
    62: "MIC",   # Microbiology
    63: "BCH",   # Biochemistry & Biotechnology
}

DEPARTMENT_FULL_NAMES = {
    # School of Engineering & Applied Science
    42: "Computer Science & Engineering",
    43: "Electrical & Electronic Engineering",
    44: "Electronic & Computer Engineering",
    45: "Electronics & Telecommunications Engineering",
    46: "Architecture",
    47: "Environmental Science & Management",
    
    # School of Business
    30: "Bachelor of Business Administration",
    31: "Master of Business Administration",
    
    # School of Arts and Social Science
    50: "Economics",
    51: "English",
    52: "Political Science & Governance",
    
    # School of Life Science
    60: "Pharmacy",
    61: "Public Health",
    62: "Microbiology",
    63: "Biochemistry & Biotechnology",
}


def detect_department_from_id(student_id: str) -> dict:
    """
    Detect department from NSU student ID.
    
    NSU ID formats observed:
    - Pattern 1: "XXXXXXX S DD" format (e.g., "0920402 S 43") where DD is dept code at end
    - Pattern 2: "XXXXXXXXDD" format (10 continuous digits)
    
    The department code (42=CSE, 43=EEE, 30=BBA) can appear:
    - At the END after "S" separator (most reliable)
    - At positions 7-8 in 10-digit format
    - At positions 5-6 in some older formats
    
    Args:
        student_id: The NSU student ID (various formats)
        
    Returns:
        dict with keys:
        - valid: bool - whether department was detected successfully
        - department_code: int - the numeric department code (42, 43, 30)
        - department_name: str - short name (CSE, EEE, BBA)
        - department_full_name: str - full name
        - error: str - error message if invalid
    """
    def make_valid_result(dept_code: int) -> dict:
        return {
            "valid": True,
            "department_code": dept_code,
            "department_name": VALID_DEPARTMENTS[dept_code],
            "department_full_name": DEPARTMENT_FULL_NAMES[dept_code]
        }
    
    if not student_id:
        return {
            "valid": False, 
            "error": "No student ID provided"
        }
    
    original = str(student_id).strip()
    
    # Pattern 1: Check for "S XX" or "S XX" pattern (space + S + optional space + 2 digits)
    # This handles formats like "0920402 S 43" or "0920402S43"
    match = re.search(r'S\s*(\d{2})\s*$', original, re.IGNORECASE)
    if match:
        try:
            dept_code = int(match.group(1))
            if dept_code in VALID_DEPARTMENTS:
                return make_valid_result(dept_code)
        except ValueError:
            pass
    
    # Clean all non-digits for position-based extraction
    clean_id = ''.join(c for c in original if c.isdigit())
    
    # Pattern 2: Try last 2 digits (works for formats where dept code is at the end)
    # E.g., "092040243" -> last 2 = "43" = EEE
    if len(clean_id) >= 9:
        try:
            dept_code = int(clean_id[-2:])
            if dept_code in VALID_DEPARTMENTS:
                return make_valid_result(dept_code)
        except ValueError:
            pass
    
    # Pattern 3: Try positions 7-8 (0-indexed) for 10-digit format
    # E.g., "0920402543" -> positions 7-8 = "54" (not valid), but "0920424302" -> "43"
    if len(clean_id) >= 10:
        try:
            dept_code = int(clean_id[7:9])
            if dept_code in VALID_DEPARTMENTS:
                return make_valid_result(dept_code)
        except ValueError:
            pass
    
    # Pattern 4: Try positions 5-6 (original format assumption)
    # E.g., "0920442543" -> positions 5-6 = "42" = CSE
    if len(clean_id) >= 7:
        try:
            dept_code = int(clean_id[5:7])
            if dept_code in VALID_DEPARTMENTS:
                return make_valid_result(dept_code)
        except ValueError:
            pass
    
    # No valid department found
    attempted_codes = []
    if len(clean_id) >= 9:
        attempted_codes.append(f"last 2 digits: {clean_id[-2:]}")
    if len(clean_id) >= 10:
        attempted_codes.append(f"positions 7-8: {clean_id[7:9]}")
    if len(clean_id) >= 7:
        attempted_codes.append(f"positions 5-6: {clean_id[5:7]}")
    
    return {
        "valid": False, 
        "error": f"Could not detect valid department. Tried: {', '.join(attempted_codes) if attempted_codes else 'ID too short'}. Valid codes: CSE(42), EEE(43), BBA(30)"
    }


def validate_courses_against_catalog(courses: list) -> list:
    """
    Validate extracted courses against the official NSU course catalog.
    
    Args:
        courses: List of CourseRecord objects
        
    Returns:
        List of unknown course codes not found in the catalog
    """
    if not COURSE_CATALOG_AVAILABLE:
        return []
    
    unknown_courses = []
    for course in courses:
        code = course.course_code.upper().strip()
        # Remove 'L' suffix for lab courses when checking (labs might not be separate entries)
        base_code = code.rstrip('L') if code.endswith('L') else code
        
        if get_course_info(code) is None and get_course_info(base_code) is None:
            # Check if it's at least a valid course prefix
            prefix_match = re.match(r'^([A-Z]{2,4})\d{3}[A-Z]?$', code)
            if prefix_match:
                unknown_courses.append(code)
    
    return unknown_courses


# Grade corrections — ONLY applied during grade validation, never globally.
# Dangerous broad corrections ('S':'B', 'E':'F', '0':'D', 'O':'D') removed
# because they cause false grade assignments from non-grade text.
GRADE_CORRECTIONS = {
    # Number/letter confusion in grade context
    '8+': 'B+', '8-': 'B-', '8': 'B', '6': 'B',
    # Plus/minus symbol issues
    'A+': 'A', 'A1': 'A-', 'Al': 'A-', 'A|': 'A-', 'At': 'A-', 'A~': 'A-', 'A.': 'A',
    'Bt': 'B+', 'B1': 'B-', 'B~': 'B-', 'B.': 'B',
    'C1': 'C-', 'Ct': 'C+', 'C~': 'C-', 'C.': 'C',
    'D1': 'D+', 'Dt': 'D+', 'D.': 'D',
    # Transfer/special grades
    'T8': 'TR', 'TR.': 'TR', 'T R': 'TR', 'ТR': 'TR',  # Cyrillic T
    'P+': 'P', 'P.': 'P',
}

# Course code corrections — applied only to detected course codes
COURSE_CODE_CORRECTIONS = {
    'CSEIS': 'CSE15', 'MAT1I6': 'MAT116', 'MAT12O': 'MAT120',
    'PHY1O7': 'PHY107', 'ENG1O2': 'ENG102',
    'MIS105': 'MIS205', 'MIS1O5': 'MIS205',  # Common 2→1/O misread
    'MIS2O5': 'MIS205',
    'CSEII5': 'CSE115', 'CSEII5L': 'CSE115L',
    'CSE2I5': 'CSE215', 'CSE2I5L': 'CSE215L',
    'CSE22S': 'CSE225', 'CSE22SL': 'CSE225L',
    'CSE23I': 'CSE231', 'CSE23IL': 'CSE231L',
    'CSE3I1': 'CSE311', 'CSE4I1': 'CSE411',
    'EEEIII': 'EEE111', 'EEE14I': 'EEE141',
    'MATI20': 'MAT120', 'MATI25': 'MAT125', 'MATI30': 'MAT130',
    'MATI64': 'MAT164', 'MAT25O': 'MAT250',
    'ECOI01': 'ECO101', 'POLI01': 'POL101', 'SOCI01': 'SOC101',
    'BENI05': 'BEN205', 'BEN2O5': 'BEN205',
    'CSEZ26': 'CSE226',
    'ENGI02': 'ENG102', 'ENGI03': 'ENG103',
    'HISI03': 'HIS103', 'HISI02': 'HIS102',
    'PHII04': 'PHI104',
    'PHYI07': 'PHY107', 'PHYI08': 'PHY108',
    'CHEI01': 'CHE101', 'CHNI01': 'CHN101',
}


@dataclass
class CourseRecord:
    """A single course entry."""
    course_code: str
    credits: float
    grade: str
    semester: str = ""
    confidence: float = 1.0

    def to_csv_row(self) -> str:
        return f"{self.course_code},{self.credits},{self.grade},{self.semester}"


@dataclass
class OCRResult:
    """OCR extraction result."""
    success: bool
    courses: list = field(default_factory=list)
    raw_text: list = field(default_factory=list)
    error: Optional[str] = None
    student_name: str = ""
    student_id: str = ""
    cgpa: float = 0.0
    total_credits: float = 0.0
    engine_used: str = ""
    confidence_score: float = 0.0
    # Department detection fields
    department_code: int = 0
    department_name: str = ""
    department_full_name: str = ""
    department_valid: bool = False
    # Course validation fields
    unknown_courses: list = field(default_factory=list)

    @property
    def csv_data(self) -> str:
        lines = ["Course_Code,Credits,Grade,Semester"]
        for course in self.courses:
            lines.append(course.to_csv_row())
        return "\n".join(lines)

    @property
    def course_count(self) -> int:
        return len(self.courses)


class WebOCR:
    """
    Improved OCR with multiple engines and better parsing.

    Priority:
    1. Native PDF text (for digital PDFs)
    2. Google Vision API (most accurate, 1000 free/month)
    3. Azure Document Intelligence (99%+ accuracy, premium)
    
    Engine selection:
    - 'auto': Auto-select best available engine
    - 'google_vision': Force Google Cloud Vision
    - 'azure': Force Azure Document Intelligence
    """

    def __init__(self, google_api_key: str = None, azure_key: str = None,
                 azure_endpoint: str = None, progress_callback=None,
                 engine: str = 'auto'):
        """
        Initialize WebOCR with API keys and engine selection.
        
        Args:
            google_api_key: Google Cloud Vision API key
            azure_key: Azure Document Intelligence key
            azure_endpoint: Azure Document Intelligence endpoint
            progress_callback: Progress reporting callback
            engine: OCR engine selection ('auto', 'google_vision', 'azure')
        """
        # Use module-level constants as fallback (loaded from .env at import time)
        # Also check environment directly for runtime flexibility
        self.google_api_key = google_api_key or GOOGLE_VISION_API_KEY or os.environ.get('GOOGLE_CLOUD_VISION_KEY') or os.environ.get('GOOGLE_VISION_API_KEY', '')
        self.azure_key = azure_key or AZURE_DOC_INTELLIGENCE_KEY
        self.azure_endpoint = azure_endpoint or AZURE_DOC_INTELLIGENCE_ENDPOINT
        self.progress_callback = progress_callback
        self.engine = engine.lower() if engine else 'auto'
        
        # Initialize Azure client if available
        self.azure_client = None
        if AZURE_MODULE_AVAILABLE and (self.azure_key and self.azure_endpoint):
            self.azure_client = AzureDocIntelligence(self.azure_key, self.azure_endpoint)
        
        _logger.info(f"WebOCR initialized - Engine: {self.engine}, Google: {'✓' if self.google_api_key else '✗'}, Azure: {'✓' if self.azure_client and self.azure_client.is_configured else '✗'}")

    def _report(self, stage: str, progress: float, text: str = ""):
        if self.progress_callback:
            self.progress_callback(stage, progress, text)

    def extract(self, file_path: str) -> OCRResult:
        """Extract transcript data from PDF or image."""
        path = Path(file_path)
        if not path.exists():
            return OCRResult(success=False, error=f"File not found: {file_path}")

        ext = path.suffix.lower()
        try:
            self._report("init", 5, "Starting extraction...")

            if ext == '.pdf':
                return self._extract_pdf(path)
            elif ext in {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}:
                return self._extract_image(path)
            else:
                return OCRResult(success=False, error=f"Unsupported: {ext}")
        except Exception as e:
            _logger.exception(f"OCR extraction error: {e}")
            return OCRResult(success=False, error=str(e))

    def _extract_pdf(self, path: Path) -> OCRResult:
        """Extract from PDF."""
        import fitz

        self._report("pdf", 10, "Opening PDF...")
        doc = fitz.open(str(path))

        # Try native text extraction first (for digital PDFs)
        all_text = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                all_text.append(text)

        full_text = "\n".join(all_text)

        # If we got substantial text, parse it directly
        if len(full_text) > 50:
            doc.close()
            self._report("parse", 50, "Parsing digital PDF...")
            result = self._parse_transcript_text(full_text)
            result.engine_used = "PyMuPDF (Native Text)"
            result.confidence_score = 0.98
            self._report("complete", 100, "Done!")
            return result

        # Otherwise, need OCR for scanned PDF
        self._report("ocr", 30, "Running OCR on scanned PDF...")

        ocr_text = ""
        last_error = None
        pages_processed = 0
        actual_engine = None  # Track which engine was actually used
        total_confidence = 0.0
        confidence_count = 0

        for i, page in enumerate(doc):
            self._report("page", 30 + (i / len(doc)) * 50, f"OCR page {i+1}/{len(doc)}...")

            # Render page to image at higher resolution for better OCR
            pix = page.get_pixmap(matrix=fitz.Matrix(4.0, 4.0))
            img_data = pix.tobytes("png")

            # Compress if too large for OCR API (free tier limit ~1MB)
            if len(img_data) > 900000:
                img_data = self._compress_image(img_data)

            # Run OCR with selected engine (now returns confidence)
            page_text, error, page_engine, page_confidence = self._ocr_image(img_data, "page.png")
            pages_processed += 1
            
            # Track which engine was used (use first successful page's engine)
            if page_text and not actual_engine:
                actual_engine = page_engine
            
            # Accumulate confidence scores
            if page_confidence > 0:
                total_confidence += page_confidence
                confidence_count += 1

            if page_text:
                ocr_text += page_text + "\n"
            if error:
                last_error = error
                _logger.warning(f"Page {i+1} OCR error: {error}")

        doc.close()

        if not ocr_text.strip():
            if last_error:
                error_msg = f"OCR failed on {pages_processed} page(s): {last_error}"
            else:
                error_msg = f"OCR processed {pages_processed} page(s) but found no text. APIs configured: Google Vision={bool(self.google_api_key)}, Azure={bool(self.azure_client)}"
            return OCRResult(success=False, error=error_msg)

        self._report("parse", 85, "Parsing extracted text...")
        result = self._parse_transcript_text(ocr_text)
        result.engine_used = actual_engine or ("Google Vision" if self.google_api_key else ("Azure" if self.azure_client else "None"))
        
        # Use real average confidence across all pages
        if confidence_count > 0:
            result.confidence_score = total_confidence / confidence_count
        else:
            result.confidence_score = 0.90  # Default if no confidence data

        self._report("complete", 100, "Done!")
        return result

    def _extract_image(self, path: Path) -> OCRResult:
        """Extract from image file."""
        self._report("image", 20, "Reading image...")

        with open(path, 'rb') as f:
            img_data = f.read()

        # Compress if too large
        if len(img_data) > 900000:
            self._report("compress", 30, "Compressing...")
            img_data = self._compress_image(img_data)

        self._report("ocr", 40, "Running OCR...")
        text, error, engine_used, confidence = self._ocr_image(img_data, path.name)

        if not text:
            if error:
                error_msg = f"OCR failed: {error}"
            else:
                error_msg = f"OCR found no text. APIs configured: Google={bool(self.google_api_key)}, Azure={bool(self.azure_client and self.azure_client.is_configured)}"
            return OCRResult(success=False, error=error_msg)

        self._report("parse", 80, "Parsing...")
        result = self._parse_transcript_text(text)
        result.engine_used = engine_used or "Unknown"
        result.confidence_score = confidence if confidence > 0 else 0.90  # Use real confidence

        self._report("complete", 100, "Done!")
        return result

    def _ocr_image(self, img_data: bytes, filename: str) -> tuple:
        """Run OCR on image data using selected or available API.

        Returns:
            tuple: (text, error, engine_used, confidence) - text is the extracted text, 
                   error is the error message if any, engine_used is the name of the engine,
                   confidence is the average confidence score (0.0 to 1.0)
        """
        google_error = None
        azure_error = None
        google_tried = False
        azure_tried = False
        engine_used = None

        # Determine engine order based on selection
        if self.engine == 'google_vision':
            engines = ['google']
        elif self.engine == 'azure':
            engines = ['azure']
        else:
            # Auto mode: try Google first (faster), then Azure
            engines = ['google', 'azure']

        for engine in engines:
            if engine == 'google' and self.google_api_key:
                google_tried = True
                text, google_error, confidence = self._google_vision_ocr(img_data)
                if text:
                    return text, None, "Google Cloud Vision", confidence
            elif engine == 'azure' and self.azure_client and self.azure_client.is_configured:
                azure_tried = True
                text, azure_error, confidence = self.azure_client.extract_text_with_confidence(img_data, filename)
                if text:
                    return text, None, "Azure Document Intelligence", confidence

        # Build error message
        error_msg = ""
        if google_tried and azure_tried:
            if google_error and azure_error:
                error_msg = f"Both OCR APIs failed - Google: {google_error}; Azure: {azure_error}"
            elif google_error:
                error_msg = f"Google Vision failed ({google_error}), Azure found no text"
            elif azure_error:
                error_msg = f"Azure failed ({azure_error}), Google Vision found no text"
            else:
                error_msg = "Both OCR APIs processed OK but found no text."
        elif google_tried:
            error_msg = google_error or "Google Vision API processed but found no text"
        elif azure_tried:
            error_msg = azure_error or "Azure Document Intelligence processed but found no text"
        else:
            error_msg = "No OCR API keys configured. Set GOOGLE_CLOUD_VISION_KEY or AZURE_DOC_INTELLIGENCE_KEY in .env"
        
        return "", error_msg, None, 0.0

    def _google_vision_ocr(self, img_data: bytes) -> tuple:
        """
        Google Cloud Vision API text detection with maximum accuracy settings.
        
        Uses DOCUMENT_TEXT_DETECTION for optimal text extraction from structured
        documents like transcripts. This provides better handling of:
        - Tables and columns
        - Multi-line text blocks
        - Character-level confidence scores
        
        Returns:
            tuple: (text, error, confidence) where confidence is 0.0 to 1.0
        """
        if not self.google_api_key:
            return "", None, 0.0

        try:
            b64_image = base64.b64encode(img_data).decode('utf-8')

            # Maximum accuracy payload with language hints and confidence scoring
            payload = {
                "requests": [{
                    "image": {"content": b64_image},
                    "features": GOOGLE_VISION_FEATURES,  # DOCUMENT_TEXT_DETECTION for best results
                    "imageContext": GOOGLE_VISION_IMAGE_CONTEXT  # English hints + confidence scoring
                }]
            }

            req = urllib_request.Request(
                "https://vision.googleapis.com/v1/images:annotate",
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'x-goog-api-key': self.google_api_key
                }
            )

            with urllib_request.urlopen(req, timeout=API_TIMEOUT) as response:
                result = json.loads(response.read().decode('utf-8'))

            responses = result.get('responses', [])
            if responses:
                if 'error' in responses[0]:
                    error_msg = responses[0]['error'].get('message', 'Unknown error')
                    return "", f"API error: {error_msg}", 0.0
                annotation = responses[0].get('fullTextAnnotation', {})
                text = annotation.get('text', '')
                
                # Extract REAL confidence from API response
                avg_confidence = 0.0
                if annotation and 'pages' in annotation:
                    confidence_scores = []
                    for page in annotation.get('pages', []):
                        for block in page.get('blocks', []):
                            if 'confidence' in block:
                                confidence_scores.append(block['confidence'])
                    if confidence_scores:
                        avg_confidence = sum(confidence_scores) / len(confidence_scores)
                        _logger.info(f"Google Vision OCR: {len(confidence_scores)} blocks, avg confidence: {avg_confidence:.2%}")
                    else:
                        # If no block-level confidence, use 0.95 as default for successful extraction
                        avg_confidence = 0.95
                        _logger.info("Google Vision OCR: No block confidence available, using default 0.95")
                
                if text:
                    return text, None, avg_confidence
                return "", None, 0.0
            else:
                return "", "No response from API", 0.0

        except HTTPError as e:
            try:
                error_body = e.read().decode('utf-8')
                error_json = json.loads(error_body)
                error_msg = error_json.get('error', {}).get('message', str(e.reason))
            except (json.JSONDecodeError, AttributeError):
                error_msg = str(e.reason)
            return "", f"HTTP {e.code}: {error_msg}", 0.0
        except URLError as e:
            return "", f"Network error: {e.reason}", 0.0
        except Exception as e:
            return "", f"Error: {str(e)}", 0.0

    def _compress_image(self, data: bytes) -> bytes:
        """Compress image for API limits."""
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(data))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            max_dim = 4000
            if img.width > max_dim or img.height > max_dim:
                ratio = min(max_dim / img.width, max_dim / img.height)
                img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)

            output = io.BytesIO()
            img.save(output, format='JPEG', quality=90, optimize=True)
            return output.getvalue()
        except ImportError as e:
            _logger.warning(f"PIL not available for image compression: {e}")
            return data
        except Exception as e:
            _logger.warning(f"Image compression failed: {e}")
            return data

    def _parse_transcript_text(self, text: str) -> OCRResult:
        """
        Parse transcript text using SIMPLE SEQUENTIAL MATCHING.
        
        Strategy:
        1. Find ALL course codes with line positions
        2. Find ALL grades with line positions
        3. Sort both by line number
        4. For each course, find the nearest grade AFTER it (within reasonable distance)
        
        This is simpler and more reliable than semester-scoped matching.
        """
        courses = []
        student_name = ""
        student_id = ""
        cgpa = 0.0
        total_credits_from_pdf = 0.0

        lines = text.replace('\r', '\n').split('\n')
        
        # ===== WATERMARK NOISE FILTER =====
        # NSU transcripts have a large diagonal watermark "NORTH SOUTH UNIVERSITY"
        # that OCR reads as hundreds of short fragments. These cause:
        # - Phantom course codes, grade misassignment, wrong credits
        # Strategy:
        # 1. Strip trailing watermark fragments from meaningful lines
        # 2. Remove pure noise lines
        # 3. Remove grading legend table lines (A, B+, C, etc. as standalone entries
        #    in the legend, not course grades)
        
        # Step 1: Strip trailing watermark fragments from lines
        # Patterns like "VERST", "IVERSI", "RTH SOUTH" appended to meaningful text
        _WM_TRAIL = re.compile(
            r'\s+'                           # leading whitespace
            r'(?:'
            r'[A-Z]{0,3}TH\s*[A-Z]*'        # "RTH SO", "2TH SOU", "TH UNI"
            r'|TY\s*N[OAKR]*'               # "TY NOR", "TY NOK"
            r'|[A-Z]*SOUTH\s*[A-Z]*'        # "SOUTH UNI"
            r'|[A-Z]*NORTH\s*[A-Z]*'        # "NORTH S"
            r'|[A-Z]*UNIVER[SITY]*'         # "UNIVERS", "UNIVERSE"
            r'|[A-Z]*VERS[ITY]*'            # "VERSI", "VERSITY"
            r'|[A-Z]*OUTH\s*[A-Z]*'         # "OUTH UNT"
            r'|[A-Z]{0,3}ERS[ITY]*'         # "ERSITY", "ERSI"
            r'|[A-Z]{0,2}IVER[SITY]*'       # "IVERSI"
            r'|NIVER[SITY]*'                # "NIVERSI"
            r'|[A-Z]*SO\s*[A-Z]*'           # "RTH SO"
            r'|[A-Z]*SIT[Y]*'               # "SITY"
            r'|SOUTH\s+[A-Z]*'              # "SOUTH LIVERSI"
            r'|NORTH\s+S'                   # "NORTH S"
            r'|UNIVE[RSA]*'                 # "UNIVE", "UNIVERS"
            r'|JUNIT'                       # "JUNIT"
            r'|TENOR'                       # "TENOR"
            r'|THUN'                        # "THUN"
            r'|THIN'                        # "THIN"
            r'|SOL\b'                       # "SOL"
            r'|NSU\b'                       # "NSU" (watermark, not course)
            r'|SEEK'                        # "SEEK" from "SEEK KNOWLEDGE"
            r')'
            r'\s*$'                          # must be at end of line
        )
        
        # Strip watermark fragments PREFIXED to data on the same line
        # OCR merges watermark text with actual data: "TH3.0 F 0.0 0.0", "T3.0 A"
        # These prefixes are short uppercase fragments from "NORTH SOUTH UNIVERSITY"
        _WM_PREFIX = re.compile(
            r'^(?:'
            r'TH'                            # "TH3.0 F 0.0 0.0"
            r'|TY'                           # "TY3.0"
            r'|[A-Z]{1,2}TH'                 # "JTH3.0"
            r')'
            r'(\d+\.\d)'                      # Must be followed by a decimal number (credit/grade data)
        )
        # Special case: single "T" prefix before credit/grade data
        # Only match when "T" is followed by a credit pattern AND the line
        # doesn't look like a course code (e.g., "THE" would be a title word)
        _WM_PREFIX_T = re.compile(
            r'^T(\d+\.\d\s+[ABCDFWIP])'      # "T3.0 A", "T3.0 B+" etc.
        )
        # "T3.0" standalone (just a credit value with watermark prefix)
        _WM_PREFIX_T2 = re.compile(
            r'^T(\d+\.\d)\s*$'               # "T3.0" at end of line
        )
        
        # Strip watermark fragments EMBEDDED in data lines
        # e.g., "Semester Credit: 9.00NIVERS UTGPA: 3.80" -> "Semester Credit: 9.00 TGPA: 3.80"
        _WM_MID = re.compile(
            r'(?:'
            r'NIVERS\s*U?'                   # "9.00NIVERS UTGPA"
            r'|[A-Z]{1,3}TH\s+UND'           # "TH UND"
            r'|TH\s+UN[I]*'                  # "TH UNI"
            r'|\s+ITH\s+UN'                  # " ITH UN"
            r'|\s+ERST'                      # " ERST"
            r'|\s+ENCAS'                     # " ENCAS"
            r'|\s+TEES'                      # " TEES"
            r'|\s+TVERSI'                    # " TVERSI"
            r')'
        )
        
        cleaned_lines = []
        for line in lines:
            cleaned = _WM_TRAIL.sub('', line).strip()
            # Strip watermark prefix before credit/grade data
            cleaned = _WM_PREFIX.sub(r'\1', cleaned)
            cleaned = _WM_PREFIX_T.sub(r'\1', cleaned)
            cleaned = _WM_PREFIX_T2.sub(r'\1', cleaned)
            # Strip watermark fragments embedded in data lines
            cleaned = _WM_MID.sub(' ', cleaned).strip()
            cleaned_lines.append(cleaned)
        
        # Step 2: Remove pure noise lines (no meaningful content)
        # A line is noise if it's short, all uppercase, and doesn't contain
        # course codes, grades, credits, semester names, or keywords
        _NOISE_LINE = re.compile(
            r'^(?:'
            r'[A-Z]{1,6}$'                   # "VERSITY", "ORTH"
            r'|[A-Z]{1,4}\s+[A-Z]{1,4}$'    # "ORTH SC", "RTH SO"
            r'|[A-Z]{1,4}\s+[A-Z]{1,4}\s+[A-Z]{1,4}$'
            r'|[A-Z]*SOUTH\s*[A-Z]*$'        # "SOUTH UNI"
            r'|[A-Z]*NORTH\s*[A-Z]*$'        # "NORTH SOU"
            r'|[A-Z]*UNIVER[SITY]*$'         # "UNIVERS"
            r'|[A-Z]*VERS[ITY]*$'            # "VERSI"
            r'|TY\s*N[OAKR]*$'               # "TY NOR"
            r'|[A-Z]*OUTH\s*[A-Z]*$'         # "OUTH UNT"
            r'|[A-Z]{0,3}ERS[ITY]*$'         # "ERSITY"
            r'|[A-Z]{0,2}IVER[SITY]*$'       # "IVERSI"
            r'|NIVER[SITY]*$'                # "NIVERSI"
            r'|[A-Z]*SO\s*[A-Z]*$'           # "RTH SO"
            r'|[A-Z]*SIT[Y]*$'               # "SITY"
            r'|[A-Z]{1,3}TH[A-Z\s]*$'        # "2TH SO", "RTH SOU"
            r'|UNIVE[RSA]*$'                 # "UNIVE"
            r'|[A-Z]*LIVER[SITY]*$'          # "LIVERSI"
            r'|\d[A-Z]{1,5}$'                # "2TH", "0SA" (digit+watermark fragment)
            r'|\d{6,}$'                      # "0112106", "018030" (long digit strings)
            r'|SEEK\s+KNOWLEDGE$'            # "SEEK KNOWLEDGE" watermark
            r'|UNIF[LWE]*$'                  # "UNIFE", "UNIFL" watermark fragment
            r'|LUND$'                        # "LUND" watermark fragment
            r'|"OUTH\s+UNI[A-Z]*$'           # "OUTH UNIFL" watermark fragment
            r')$'
        )
        
        # Meaningful content patterns - if a line has ANY of these, keep it
        _MEANINGFUL = re.compile(
            r'(?:'
            r'[A-Z]{2,4}\s?\d{3}[A-Z]?'     # Course code
            r'|[ABCDF][+-]?'                 # Grade letter
            r'|\d+\.\d+'                     # Decimal number
            r'|(?:Spring|Summer|Fall)\s+\d{4}'  # Semester
            r'|(?:Student|Course|Credit|Grade|TGPA|CGPA|Semester|Total|Cumulative|Degree|Major|Name|Date|Official|Summary|School|Bachelor|Department|Title|Working|Introduction|Financial|Management|Accounting|Marketing|Economics|Business|Calculus|Physics|Engineering|Computer|Statistics|Composition|Advanced|Intermediate|Corporate|Investment|Bank|Legal|Environment|Production|Entrepreneurship|Sociology|Internship|Strategic|Taxation|Communication|Ethics|Biology|Chinese|Numerical|Electrical|Semiconductor|Signals|Systems|Digital|Verilog|Mechanical|Switchgear|Protection|Project|Drawing|Circuits|Transmission|Distribution|Architecture|Organization|Probability|Optimization|Methodology|Public|Administration|Governance|Reliability|Operation|General|Analytic|Geometry)'
            r')',
            re.IGNORECASE
        )
        # Separate check for actual lowercase content (course titles have lowercase words)
        # This must NOT use IGNORECASE — we need real lowercase letters to distinguish
        # course titles from watermark fragments like "VERSE", "EKST", "ERST"
        _HAS_LOWERCASE = re.compile(r'[a-z]{3,}')
        
        filtered_lines = []
        for line in cleaned_lines:
            if not line:
                filtered_lines.append(line)
                continue
            # Keep if it has meaningful content (course codes, grades, numbers, keywords)
            if _MEANINGFUL.search(line):
                filtered_lines.append(line)
                continue
            # Keep if it has real lowercase words (course titles like "Introduction to...")
            if _HAS_LOWERCASE.search(line):
                filtered_lines.append(line)
                continue
            # Drop pure noise lines
            if _NOISE_LINE.match(line):
                continue
            # Drop very short all-caps lines with no digits or lowercase
            if len(line) <= 12 and line.isupper() and not any(c.isdigit() for c in line):
                continue
            filtered_lines.append(line)
        
        _logger.info(f"Watermark filter: {len(lines)} -> {len(filtered_lines)} lines (removed {len(lines) - len(filtered_lines)} noise)")
        lines = filtered_lines
        
        # ===== METADATA EXTRACTION =====
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Student ID - handle multiple NSU ID formats
            # Format 1: "XXXXXXX S DD" (e.g., "0920402 S 43")  
            # Format 2: "XXXXXXX 0 DD" (OCR reads as-is)
            # Format 3: 10+ continuous digits
            # Format 4: "Student ID : XXXXXXX S DD"
            # IMPORTANT: Preserve the exact character from OCR (don't normalize)
            if not student_id:
                # First try: "Student ID" label followed by the ID value
                # Match "071415 0 30" or "0920402 S 43" patterns - preserve exact separator
                id_label_match = re.search(r'Student\s*ID\s*[:\s]+(\d{6,7})\s*([S0s5])\s*(\d{2})', line_clean, re.IGNORECASE)
                if id_label_match:
                    # Preserve the exact separator character from OCR
                    sep = id_label_match.group(2)
                    student_id = f"{id_label_match.group(1)} {sep} {id_label_match.group(3)}"
                
                # Also try without separator: "Student ID : XXXXXXXXXX"
                if not student_id:
                    id_label_match2 = re.search(r'Student\s*ID\s*[:\s]+(\d{9,10})', line_clean, re.IGNORECASE)
                    if id_label_match2:
                        student_id = id_label_match2.group(1)
                
                # Try pattern: "XXXXXXX S DD" or "XXXXXXX 0 DD" anywhere on line
                if not student_id:
                    id_match_sep = re.search(r'\b(\d{6,7})\s*([S0s5])\s*(\d{2})\b', line_clean)
                    if id_match_sep:
                        # Preserve exact separator
                        sep = id_match_sep.group(2)
                        student_id = f"{id_match_sep.group(1)} {sep} {id_match_sep.group(3)}"
                
                # Try continuous 9-10 digit ID (no separator)
                if not student_id:
                    id_match = re.search(r'\b(\d{9,10})\b', line_clean)
                    if id_match:
                        student_id = id_match.group(1)
                
                # Try colon-prefixed format: ": 0920402 S 43" or ": 071415 0 30"
                if not student_id:
                    id_match2 = re.search(r':\s*(\d{6,7})\s*(\w)\s*(\d{2})', line_clean)
                    if id_match2:
                        # Preserve exact separator
                        sep = id_match2.group(2)
                        student_id = f"{id_match2.group(1)} {sep} {id_match2.group(3)}"
            
            # Student Name - improved extraction to avoid institutional labels
            if not student_name and ('Student Name' in line_clean or 'Name:' in line_clean):
                # Institutional labels to skip (case-insensitive check)
                skip_labels = [
                    'student id', 'date of birth', 'degree conferred', 'official transcript',
                    'course title', 'school', 'engineering', 'university', 'department',
                    'college', 'faculty', 'sciences', 'physical sciences', 'arts', 'business',
                    'unofficial transcript', 'transcript', 'north south', 'nsu'
                ]
                
                # First try to extract name from the same line (e.g., "Name: John Doe")
                same_line_match = re.search(r'(?:Student\s*)?Name\s*:\s*([A-Za-z][A-Za-z\s\.]+)', line_clean, re.IGNORECASE)
                if same_line_match:
                    candidate = same_line_match.group(1).strip()
                    candidate_lower = candidate.lower()
                    # Validate: at least 2 words, doesn't contain institutional labels
                    if (len(candidate.split()) >= 2 and 
                        not any(label in candidate_lower for label in skip_labels)):
                        student_name = candidate
                
                # If not found on same line, look ahead for the actual name
                # NSU transcripts often have format where values start with ":"
                if not student_name:
                    for j in range(i + 1, min(i + 15, len(lines))):
                        potential_name = lines[j].strip()
                        if not potential_name:
                            continue
                        
                        # Handle NSU format where name is on a line starting with ":"
                        # e.g., ": Komol Arafat Gani"
                        if potential_name.startswith(':'):
                            potential_name = potential_name[1:].strip()
                        
                        # Skip if it's another header or empty after stripping
                        if not potential_name or len(potential_name) < 5:
                            continue
                        
                        potential_lower = potential_name.lower()
                        
                        # Skip headers like "Student ID", "Date of Birth", etc.
                        if any(label in potential_lower for label in skip_labels):
                            continue
                        
                        # Must be letters, spaces, and periods only (for initials)
                        if re.match(r'^[A-Za-z][A-Za-z\s\.]+$', potential_name):
                            # Validate: typical names have 2-5 words
                            word_count = len(potential_name.split())
                            if 2 <= word_count <= 5:
                                student_name = potential_name
                                break
            
            # CGPA - multiple patterns for different transcript formats
            # Take the LAST valid CGPA found (most recent cumulative value)
            if any(x in line_clean.upper() for x in ['CUMULATIVE', 'CGPA', 'CUM. GPA', 'CUM GPA']):
                # Try multiple patterns
                cgpa_patterns = [
                    r':\s*(\d+\.\d{1,2})',           # ": 3.45"
                    r'(\d+\.\d{1,2})\s*$',           # "3.45" at end
                    r'CGPA\s*[:=]?\s*(\d+\.\d{1,2})',  # "CGPA 3.45" or "CGPA: 3.45"
                    r'(\d+\.\d{1,2})\s*/\s*4\.0',    # "3.45/4.0"
                ]
                for pattern in cgpa_patterns:
                    cgpa_match = re.search(pattern, line_clean)
                    if cgpa_match:
                        potential_cgpa = float(cgpa_match.group(1))
                        if 0.0 <= potential_cgpa <= 4.0:
                            cgpa = potential_cgpa
                            break
                
                # If value not on same line, check next line (OCR splits across lines)
                if cgpa == 0.0:
                    for j in range(i + 1, min(i + 3, len(lines))):
                        next_line = lines[j].strip()
                        for pattern in cgpa_patterns:
                            cgpa_match = re.search(pattern, next_line)
                            if cgpa_match:
                                potential_cgpa = float(cgpa_match.group(1))
                                if 0.0 <= potential_cgpa <= 4.0:
                                    cgpa = potential_cgpa
                                    break
                        if cgpa > 0.0:
                            break
            
            # Total Credits - multiple patterns
            # NSU transcripts use "Total Credits Counted" (for CGPA calc) and "Total Credits Passed"
            # We want "Counted" as it matches the CGPA denominator.
            # OCR often splits label and value across many lines, so check current + up to 8 lines ahead.
            if any(x in line_clean.upper() for x in ['TOTAL CREDITS', 'CREDITS EARNED', 'CREDIT HOURS']):
                # Skip "Total Credits Passed" — we want "Counted" for CGPA calculation
                is_passed = 'PASSED' in line_clean.upper()
                is_transfer = 'TRANSFER' in line_clean.upper() or 'WAIVER' in line_clean.upper()
                cr_patterns = [
                    r':\s*(\d+(?:\.\d+)?)',           # ": 130"
                    r'(\d{2,3}(?:\.\d+)?)\s*$',       # "130" at end
                ]
                found = False
                for pattern in cr_patterns:
                    cr_match = re.search(pattern, line_clean)
                    if cr_match:
                        val = float(cr_match.group(1))
                        if not is_passed and not is_transfer and 0 < val <= 250:
                            total_credits_from_pdf = val
                            found = True
                        break
                
                # If value not on same line, check next lines (OCR splits across lines)
                # Labels and values can be many lines apart in OCR output
                if not found and not is_passed and not is_transfer:
                    for j in range(i + 1, min(i + 10, len(lines))):
                        next_line = lines[j].strip()
                        for pattern in cr_patterns:
                            cr_match = re.search(pattern, next_line)
                            if cr_match:
                                val = float(cr_match.group(1))
                                if 0 < val <= 250:
                                    total_credits_from_pdf = val
                                    found = True
                                break
                        if found:
                            break

        # ===== PASS 0: FULL-LINE MATCHES (highest confidence) =====
        # FULL_LINE_PATTERN captures "CSE115 3 A-" on a single line — most reliable
        # Use a local semester lookup here because the semester ranges used by
        # later passes are built afterward.
        def get_semester_for_pass0(line_num: int) -> str:
            for j in range(line_num, -1, -1):
                sem_match = re.search(r'(Spring|Summer|Fall)\s+(\d{4})', lines[j], re.IGNORECASE)
                if sem_match:
                    return f"{sem_match.group(1).capitalize()} {sem_match.group(2)}"
            return ""

        pass0_matched_lines = set()  # Track lines already matched in pass 0
        pass0_courses = []  # [(code, credits, grade, semester, line_num), ...]
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean:
                continue
            for match in FULL_LINE_PATTERN.finditer(line_clean):
                prefix = match.group(1).upper()
                number = match.group(2).upper()
                code = prefix + number
                # Apply course code corrections (I/1/O/0 confusion)
                code = COURSE_CODE_CORRECTIONS.get(code, code)
                if prefix not in ALL_COURSE_PREFIXES:
                    continue
                credits = float(match.group(3))
                grade = match.group(4).upper()
                # Apply grade corrections before validation
                if grade not in VALID_GRADES:
                    grade = GRADE_CORRECTIONS.get(grade, grade)
                if grade not in VALID_GRADES:
                    continue
                semester = get_semester_for_pass0(i)
                pass0_courses.append((code, credits, grade, semester, i))
                pass0_matched_lines.add(i)
        
        _logger.info(f"PASS 0: {len(pass0_courses)} full-line matches (highest confidence)")
        
        # Course code pattern (needed for PASS 0.5 and PASS 1)
        course_code_pattern = re.compile(r'\b([A-Z]{2,4})\s?(\d{3}[A-Z]?)\b')
        
        # ===== PASS 0.5: DOUBLE-GRADE PRE-MATCH =====
        # When OCR produces "A A" or "A A 2.0 2.0" on a single line, it means two adjacent
        # courses have their grades merged. Find the two nearest course codes and assign directly.
        double_grade_pattern = re.compile(r'^([ABCDF][+-]?)\s+([ABCDF][+-]?)(?:\s+(\d+\.\d+)\s+(\d+\.\d+))?\s*$')
        pass05_courses = []  # [(code, credits, grade, semester, line_num), ...]
        pass05_matched_lines = set()  # Lines consumed by pass 0.5
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean:
                continue
            m = double_grade_pattern.match(line_clean)
            if not m:
                continue
            grade1 = m.group(1).upper()
            grade2 = m.group(2).upper()
            if grade1 not in VALID_GRADES or grade2 not in VALID_GRADES:
                continue
            
            # Look backward for the two nearest course codes
            found_codes = []
            for j in range(i - 1, max(i - 15, -1), -1):
                prev_line = lines[j].strip()
                for cm in course_code_pattern.finditer(prev_line):
                    prefix = cm.group(1).upper()
                    number = cm.group(2).upper()
                    code = prefix + number
                    code = COURSE_CODE_CORRECTIONS.get(code, code)
                    if prefix in ALL_COURSE_PREFIXES:
                        found_codes.append((code, j))
                if len(found_codes) >= 2:
                    break
            
            if len(found_codes) >= 2:
                # found_codes is in reverse order (closest first), take first two
                found_codes = found_codes[:2]
                # Assign grade2 to the closer course, grade1 to the further
                # (grades appear after their respective course codes, so the closer
                #  code is the second course and the further is the first)
                code1, line1 = found_codes[1]  # Further back = first course
                code2, line2 = found_codes[0]  # Closer = second course
                
                # Get credits: look between course code and grade line
                cr1 = 3.0
                for j in range(line1 + 1, i):
                    cr_m = re.match(r'^(\d+\.\d+)$', lines[j].strip())
                    if cr_m:
                        v = float(cr_m.group(1))
                        if 0 < v <= 10:
                            cr1 = v
                            break
                cr2 = 3.0
                for j in range(line2 + 1, i):
                    cr_m = re.match(r'^(\d+\.\d+)$', lines[j].strip())
                    if cr_m:
                        v = float(cr_m.group(1))
                        if 0 < v <= 10:
                            cr2 = v
                            break
                
                # Only use double-grade line credits if per-course lookup found nothing
                # (default 3.0). The per-course lookup is more reliable because it
                # finds the credit directly after the course code, while the merged
                # "2.0 2.0" on the double-grade line is often an OCR misread.
                if m.group(3) and m.group(4):
                    if cr1 == 3.0:  # Still default — no per-course credit found
                        cr1 = float(m.group(3))
                    if cr2 == 3.0:  # Still default — no per-course credit found
                        cr2 = float(m.group(4))
                
                sem1 = get_semester_for_pass0(line1)
                sem2 = get_semester_for_pass0(line2)
                
                pass05_courses.append((code1, cr1, grade1, sem1, line1))
                pass05_courses.append((code2, cr2, grade2, sem2, line2))
                pass05_matched_lines.add(i)
                # Also mark the credit lines as consumed
                for j in range(line1 + 1, i):
                    if re.match(r'^(\d+\.\d+)$', lines[j].strip()):
                        pass05_matched_lines.add(j)
                _logger.debug(f"PASS 0.5: {code1}->{grade1}, {code2}->{grade2} from double-grade line {i}")
        
        _logger.info(f"PASS 0.5: {len(pass05_courses)} double-grade pre-matches")
        
        # ===== PASS 1: COLLECT ALL DATA =====
        
        # Grade patterns (multiple formats)
        grade_patterns = [
            re.compile(r'([123456])\.0\s+([ABCDF][+-]?)\s+\d+\.\d+\s+\d+\.\d+'),  # "3.0 A- 3.0 3.0"
            re.compile(r'^([ABCDF][+-]?)\s+\d+\.\d+\s+\d+\.\d+'),  # "A- 3.0 3.0" at start
            re.compile(r'([123456])\.0\s+([ABCDF][+-]?)(?:\s*$|\s+[A-Z])'),  # "3.0 A-" or "2.0 A"
            re.compile(r'^([ABCDF][+-]?)\s*$'),  # Just "A" or "B+" (standalone)
            re.compile(r'([ABCDF][+-]?)\s+0\.0\s+0\.0'),  # "C 0.0 0.0" (failed)
            re.compile(r'\s([ABCDF][+-]?)\s+\d+\.\d+\s+\d+\.\d+'),  # Grade with CC CP anywhere
            re.compile(r'^\s*([123456])\.0\s+([ABCDF][+-]?)\s*'),  # Simpler: "3.0 A" at line start
            re.compile(r'\b([ABCDF][+-]?)\s+\d+\.\d+\s+\d+\.\d+\b'),  # Grade CC CP anywhere in line
            re.compile(r'^([ABCDF][+-]?)\s+([ABCDF][+-]?)\s+\d+\.\d+\s+\d+\.\d+'),  # "A A 2.0 2.0" (double grade from merged lines)
            re.compile(r'^([ABCDF][+-]?)\s+([ABCDF][+-]?)\s*$'),  # "A A" standalone (credits on next line)
        ]
        
        # Find ALL semester headers with their line numbers
        # Also track TGPA/CGPA lines as block delimiters
        semester_headers = []  # [(line_num, semester), ...]
        block_ends = []  # Line numbers where semester blocks end (TGPA/CGPA lines)
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            sem_match = re.search(r'(Spring|Summer|Fall)\s+(\d{4})', line_clean, re.IGNORECASE)
            if sem_match:
                semester = f"{sem_match.group(1).capitalize()} {sem_match.group(2)}"
                semester_headers.append((i, semester))
            
            # TGPA/CGPA lines mark end of semester data
            if re.search(r'TGPA|CGPA|Semester Credit', line_clean):
                block_ends.append(i)
        
        _logger.debug(f"Found {len(semester_headers)} semester headers: {[(l, s) for l, s in semester_headers]}")
        _logger.debug(f"Found {len(block_ends)} block-end lines (TGPA/CGPA): {block_ends}")
        
        # Sort semester headers by line number
        semester_headers.sort(key=lambda x: x[0])
        block_ends.sort()
        
        # Build semester ranges: each semester header is valid until the
        # first TGPA/CGPA line after it, or until the next semester header,
        # whichever comes first. This prevents courses from one semester
        # bleeding into the next when noise lines shift positions.
        semester_ranges = []  # [(start, end, semester), ...]
        
        for idx, (sem_line, semester) in enumerate(semester_headers):
            start = sem_line
            
            # Find the earliest boundary after this semester header:
            # 1. Next semester header
            # 2. First TGPA/CGPA line after this header
            # Use whichever comes first
            next_header = semester_headers[idx + 1][0] if idx + 1 < len(semester_headers) else len(lines)
            
            # Find first block_end after this semester header
            next_block_end = len(lines)
            for be in block_ends:
                if be > sem_line:
                    next_block_end = be
                    break
            
            end = min(next_header - 1, next_block_end)
            semester_ranges.append((start, end, semester))
        
        # For each course, find which semester range it falls into
        def get_semester_for_line(line_num):
            for start, end, semester in semester_ranges:
                if start <= line_num <= end:
                    return semester
            
            # Fallback: find most recent header before this line
            best = ""
            for sem_line, semester in semester_headers:
                if sem_line <= line_num:
                    best = semester
            return best
        
        # Collect ALL course codes
        all_courses = []  # [(code, line_num, semester), ...]
        seen_code_in_line = {}  # Track course codes per line to avoid duplicates
        
        for i, line in enumerate(lines):
            # Skip lines already matched in PASS 0 or PASS 0.5
            if i in pass0_matched_lines or i in pass05_matched_lines:
                continue
            
            line_clean = line.strip()
            if not line_clean:
                continue
            
            # Skip summary stats lines (but NOT lines that just happen to be near "Summary")
            if 'Total Credits Counted' in line_clean and ':' in line_clean:
                continue
            if 'Total Credits Passed' in line_clean and ':' in line_clean:
                continue
            if 'Total Grade Points' in line_clean and ':' in line_clean:
                continue
            
            for match in course_code_pattern.finditer(line_clean):
                prefix = match.group(1).upper()
                number = match.group(2).upper()
                
                if prefix not in ALL_COURSE_PREFIXES:
                    continue
                
                code = prefix + number
                # Apply course code corrections (I/1/O/0 confusion)
                code = COURSE_CODE_CORRECTIONS.get(code, code)
                
                # Skip if we already found this code in this line
                line_key = (code, i)
                if line_key in seen_code_in_line:
                    continue
                seen_code_in_line[line_key] = True
                
                # Skip if already matched in PASS 0 or PASS 0.5
                if any(c[0] == code and c[4] == i for c in pass0_courses):
                    continue
                if any(c[0] == code and c[4] == i for c in pass05_courses):
                    continue
                
                semester = get_semester_for_line(i)
                all_courses.append((code, i, semester))
                if not semester:
                    _logger.debug(f"Course {code} at line {i} has no semester")
        
        _logger.info(f"Found {len(all_courses)} course codes in OCR")
        
        # Collect ALL grades
        all_grades = []  # [(grade, credits, line_num, is_failed), ...]
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean:
                continue
            
            # Check for failed pattern "C 0.0 0.0" or "D+ 0.0 0.0"
            is_failed = bool(re.search(r'0\.0\s+0\.0', line_clean))
            
            grade_found = None
            credits_found = 3.0
            
            # Try pattern 5: Failed pattern "C 0.0 0.0"
            match = grade_patterns[4].search(line_clean)
            if match:
                grade_found = match.group(1).upper()
                is_failed = True
                # Look back for credits (reduced window to prevent cross-course)
                for j in range(max(0, i-3), i):
                    cr_match = re.search(r'\b([123456])\.0\b', lines[j])
                    if cr_match:
                        credits_found = float(cr_match.group(1))
                        break
            
            # Try pattern 1: "3.0 A- 3.0 3.0"
            if not grade_found:
                match = grade_patterns[0].search(line_clean)
                if match:
                    credits_found = float(match.group(1))
                    grade_found = match.group(2).upper()
            
            # Try pattern 2: "A- 3.0 3.0"
            if not grade_found:
                match = grade_patterns[1].match(line_clean)
                if match:
                    grade_found = match.group(1).upper()
                    # Look back for credits (reduced window)
                    for j in range(max(0, i-3), i):
                        cr_match = re.search(r'\b([123456])\.0\b', lines[j])
                        if cr_match:
                            credits_found = float(cr_match.group(1))
                            break
            
            # Try pattern 3: "3.0 A-"
            if not grade_found:
                match = grade_patterns[2].search(line_clean)
                if match:
                    credits_found = float(match.group(1))
                    grade_found = match.group(2).upper()
            
            # Try pattern 4: Just "A", "B+", "C-" (single grade letter)
            if not grade_found:
                match = grade_patterns[3].match(line_clean)
                if match:
                    grade_found = match.group(1).upper()
                    # Look back for credits (reduced window)
                    for j in range(max(0, i-3), i):
                        cr_match = re.search(r'\b([123456])\.0\b', lines[j])
                        if cr_match:
                            credits_found = float(cr_match.group(1))
                            break
            
            # Try pattern 6: Grade anywhere in line (with CC CP format)
            if not grade_found:
                match = grade_patterns[5].search(line_clean)
                if match:
                    grade_found = match.group(1).upper()
                    # Look back for credits (reduced window)
                    for j in range(max(0, i-3), i):
                        cr_match = re.search(r'\b([123456])\.0\b', lines[j])
                        if cr_match:
                            credits_found = float(cr_match.group(1))
                            break
            
            # Try pattern 7: Simple "3.0 A" at line start (last resort)
            if not grade_found:
                match = grade_patterns[6].match(line_clean)
                if match:
                    credits_found = float(match.group(1))
                    grade_found = match.group(2).upper()
            
            # Try pattern 8: Grade CC CP anywhere in line (broadest match)
            if not grade_found:
                match = grade_patterns[7].search(line_clean)
                if match:
                    grade_found = match.group(1).upper()
                    # Look back for credits (reduced window)
                    for j in range(max(0, i-3), i):
                        cr_match = re.search(r'\b([123456])\.0\b', lines[j])
                        if cr_match:
                            credits_found = float(cr_match.group(1))
                            break
            
            # Try pattern 9: Double grade "A A 2.0 2.0" (OCR merges adjacent lines)
            if not grade_found:
                match = grade_patterns[8].match(line_clean)
                if match:
                    grade1 = match.group(1).upper()
                    grade2 = match.group(2).upper()
                    # Both grades are valid — add first one, second will be found on next iteration
                    # or add both now since they represent two separate course grades
                    if grade1 in VALID_GRADES or GRADE_CORRECTIONS.get(grade1, '') in VALID_GRADES:
                        grade1 = GRADE_CORRECTIONS.get(grade1, grade1) if grade1 not in VALID_GRADES else grade1
                        all_grades.append((grade1, credits_found, i, is_failed))
                    if grade2 in VALID_GRADES or GRADE_CORRECTIONS.get(grade2, '') in VALID_GRADES:
                        grade2 = GRADE_CORRECTIONS.get(grade2, grade2) if grade2 not in VALID_GRADES else grade2
                        all_grades.append((grade2, credits_found, i, is_failed))
                    grade_found = None  # Already added above, skip the default append
            
            # Try pattern 10: Double grade "A A" standalone (credits on next line)
            if not grade_found:
                match = grade_patterns[9].match(line_clean)
                if match:
                    grade1 = match.group(1).upper()
                    grade2 = match.group(2).upper()
                    # Look ahead for credits on next line (e.g., "2.0 2.0")
                    next_credits = []
                    for j in range(i + 1, min(i + 3, len(lines))):
                        cr_match = re.match(r'^(\d+\.\d+)\s+(\d+\.\d+)', lines[j].strip())
                        if cr_match:
                            next_credits = [float(cr_match.group(1)), float(cr_match.group(2))]
                            break
                    
                    if grade1 in VALID_GRADES or GRADE_CORRECTIONS.get(grade1, '') in VALID_GRADES:
                        grade1 = GRADE_CORRECTIONS.get(grade1, grade1) if grade1 not in VALID_GRADES else grade1
                        cr1 = next_credits[0] if len(next_credits) >= 1 else credits_found
                        all_grades.append((grade1, cr1, i, is_failed))
                    if grade2 in VALID_GRADES or GRADE_CORRECTIONS.get(grade2, '') in VALID_GRADES:
                        grade2 = GRADE_CORRECTIONS.get(grade2, grade2) if grade2 not in VALID_GRADES else grade2
                        cr2 = next_credits[1] if len(next_credits) >= 2 else credits_found
                        all_grades.append((grade2, cr2, i, is_failed))
                    grade_found = None  # Already added above, skip the default append
            
            if grade_found:
                # Apply grade corrections (e.g., '8+' -> 'B+')
                if grade_found not in VALID_GRADES:
                    grade_found = GRADE_CORRECTIONS.get(grade_found, grade_found)
                all_grades.append((grade_found, credits_found, i, is_failed))
        
        _logger.info(f"Found {len(all_grades)} grades in OCR")
        
        # ===== PASS 2: SEQUENTIAL LINE-ORDER MATCHING =====
        # Strategy: Process courses in line order, assign grades in line order
        # This ensures clustered courses get sequential grades
        
        all_courses.sort(key=lambda x: x[1])  # Sort by line number
        all_grades.sort(key=lambda x: x[2])   # Sort by line number
        
        used_grades = set()
        matched = []
        
        # Track next expected grade index for sequential matching
        next_grade_idx = 0
        
        # FIRST PASS: Sequential matching - each course gets the next available grade within range
        remaining_courses = []
        for code, code_line, semester in all_courses:
            best_grade = None
            best_grade_idx = -1
            best_distance = float('inf')
            
            # Start searching from next_grade_idx to maintain sequence
            for g_idx in range(len(all_grades)):
                if g_idx in used_grades:
                    continue
                    
                grade, credits, grade_line, is_failed = all_grades[g_idx]
                
                # Grade must be within reasonable range (15 lines before to 20 lines after)
                if grade_line < code_line - 15:
                    continue
                if grade_line > code_line + 20:
                    break  # Grades are sorted, stop looking
                
                distance = abs(grade_line - code_line)
                if distance < best_distance:
                    best_grade = (grade, credits, is_failed)
                    best_grade_idx = g_idx
                    best_distance = distance
            
            if best_grade:
                grade, credits, is_failed = best_grade
                used_grades.add(best_grade_idx)
                matched.append((code, credits, grade, semester, code_line, is_failed))
                _logger.debug(f"TIGHT matched: {code} (line {code_line}) -> {grade} ({credits} cr)")
            else:
                remaining_courses.append((code, code_line, semester))
        
        _logger.info(f"After tight pass: {len(matched)} matched, {len(remaining_courses)} remaining")
        
        # SECOND PASS: Medium window (within 60 lines)
        still_remaining = []
        for code, code_line, semester in remaining_courses:
            best_grade = None
            best_grade_idx = -1
            best_distance = float('inf')
            
            for g_idx, (grade, credits, grade_line, is_failed) in enumerate(all_grades):
                if g_idx in used_grades:
                    continue
                
                # Grade can be up to 30 lines before, 60 lines after
                if grade_line < code_line - 30:
                    continue
                    
                distance = abs(grade_line - code_line)
                if distance <= 60 and distance < best_distance:
                    best_grade = (grade, credits, is_failed)
                    best_grade_idx = g_idx
                    best_distance = distance
            
            if best_grade:
                grade, credits, is_failed = best_grade
                used_grades.add(best_grade_idx)
                matched.append((code, credits, grade, semester, code_line, is_failed))
                _logger.debug(f"MEDIUM matched: {code} (line {code_line}) -> {grade} ({credits} cr)")
            else:
                still_remaining.append((code, code_line, semester))
        
        unmatched_courses = still_remaining
        _logger.info(f"After medium pass: {len(matched)} matched, {len(unmatched_courses)} remaining")
        
        # FALLBACK PASS: Try wider window for unmatched
        if unmatched_courses:
            _logger.info(f"FALLBACK: Trying to match {len(unmatched_courses)} unmatched courses")
            still_unmatched = []
            for code, code_line, semester in unmatched_courses:
                best_grade = None
                best_grade_idx = -1
                best_distance = float('inf')
                
                for g_idx, (grade, credits, grade_line, is_failed) in enumerate(all_grades):
                    if g_idx in used_grades:
                        continue
                    
                    # Allow MUCH wider window - 150 lines forward, 50 lines back
                    distance = abs(grade_line - code_line)
                    if grade_line >= code_line - 50 and distance <= 150:
                        if distance < best_distance:
                            best_grade = (grade, credits, is_failed)
                            best_grade_idx = g_idx
                            best_distance = distance
                
                if best_grade:
                    grade, credits, is_failed = best_grade
                    used_grades.add(best_grade_idx)
                    matched.append((code, credits, grade, semester, code_line, is_failed))
                    _logger.debug(f"FALLBACK matched: {code} -> {grade}")
                else:
                    still_unmatched.append((code, code_line, semester))
            
            # STRAY GRADE PASS: For still-unmatched courses, scan nearby raw lines
            # for standalone grade letters that weren't captured by grade patterns
            if still_unmatched:
                stray_matched = []
                stray_unmatched = []
                for code, code_line, semester in still_unmatched:
                    stray_grade = None
                    stray_credits = 3.0
                    # Look within 25 lines after the course code for a standalone grade
                    for j in range(code_line + 1, min(code_line + 25, len(lines))):
                        raw_line = lines[j].strip()
                        # Skip watermark/noise lines
                        if not raw_line or len(raw_line) > 30:
                            continue
                        # Check for standalone grade letter
                        grade_match = re.match(r'^([ABCDF][+-]?)\s*$', raw_line)
                        if grade_match:
                            g = grade_match.group(1).upper()
                            if g in VALID_GRADES:
                                stray_grade = g
                                break
                        # Also check for "grade credit credit" format on same line
                        grade_match2 = re.match(r'^([ABCDF][+-]?)\s+(\d+\.\d+)\s+(\d+\.\d+)', raw_line)
                        if grade_match2:
                            g = grade_match2.group(1).upper()
                            if g in VALID_GRADES:
                                stray_grade = g
                                stray_credits = float(grade_match2.group(2))
                                break
                    
                    if stray_grade:
                        matched.append((code, stray_credits, stray_grade, semester, code_line, False))
                        _logger.debug(f"STRAY matched: {code} -> {stray_grade}")
                        stray_matched.append(code)
                    else:
                        stray_unmatched.append((code, code_line, semester))
                
                if stray_matched:
                    _logger.info(f"STRAY pass matched {len(stray_matched)} courses: {stray_matched}")
                if stray_unmatched:
                    _logger.warning(f"Unmatched courses (no confident grade found): {[c[0] for c in stray_unmatched]}")
        
        _logger.info(f"Matched {len(matched)} courses via multi-pass, {len(pass0_courses)} via PASS 0, {len(pass05_courses)} via PASS 0.5")
        
        # Build final course list — PASS 0 results first (highest confidence)
        seen_course_keys = set()
        for code, credits, grade, semester, line_num in pass0_courses:
            key = (code, semester)
            if key not in seen_course_keys:
                seen_course_keys.add(key)
                courses.append(CourseRecord(
                    course_code=code,
                    credits=credits,
                    grade=grade,
                    semester=semester,
                    confidence=0.98  # Full-line match = highest confidence
                ))
        
        # Then PASS 0.5 results (double-grade pre-match, high confidence)
        for code, credits, grade, semester, line_num in pass05_courses:
            key = (code, semester)
            if key not in seen_course_keys:
                seen_course_keys.add(key)
                courses.append(CourseRecord(
                    course_code=code,
                    credits=credits,
                    grade=grade,
                    semester=semester,
                    confidence=0.95  # Double-grade pre-match = high confidence
                ))
        
        # Then add multi-pass matches (lower confidence)
        for code, credits, grade, semester, line_num, is_failed in matched:
            key = (code, semester)
            if key not in seen_course_keys:
                seen_course_keys.add(key)
                courses.append(CourseRecord(
                    course_code=code,
                    credits=credits,
                    grade=grade,
                    semester=semester,
                    confidence=0.90 if not is_failed else 0.85
                ))
        
        # SORT CHRONOLOGICALLY by semester (year, then Spring->Summer->Fall)
        def semester_sort_key(course):
            sem = course.semester
            if sem:
                parts = sem.split()
                if len(parts) == 2:
                    season_order = {'Spring': 0, 'Summer': 1, 'Fall': 2}
                    try:
                        year = int(parts[1])
                        season = season_order.get(parts[0], 3)
                        return (year, season, course.course_code)
                    except ValueError:
                        pass
            return (9999, 9, course.course_code)
        
        courses.sort(key=semester_sort_key)
        
        # Log unmatched
        unmatched_count = len(all_courses) - len(matched)
        if unmatched_count > 0:
            _logger.warning(f"Could not match {unmatched_count} courses to grades")

        raw_text = [w for w in text.split() if w.strip()][:100]

        # ===== DEPARTMENT DETECTION =====
        dept_info = detect_department_from_id(student_id)
        department_code = dept_info.get('department_code', 0)
        department_name = dept_info.get('department_name', '')
        department_full_name = dept_info.get('department_full_name', '')
        department_valid = dept_info.get('valid', False)
        
        if department_valid:
            _logger.info(f"Detected department: {department_name} ({department_code}) from ID {student_id}")
        elif student_id:
            _logger.warning(f"Could not detect valid department from ID {student_id}: {dept_info.get('error', 'Unknown error')}")
        
        # ===== CREDIT SANITY CHECK =====
        # OCR commonly misreads "3.0" as "4.0" or "2.0" in the credit column.
        # Use the course catalog (COURSE_LOOKUP) when available to override
        # OCR-misread credits with known correct values.
        # Only override when the OCR credit is clearly wrong:
        # - 2.0 for a course that the catalog says is 3+ credits
        # - 4.0+ for a non-thesis course
        # Don't override 3.0 credits — that's the most common value and likely correct.
        for c in courses:
            if c.credits in (1.0, 1.5, 3.0):
                continue  # Common credit values — keep as-is
            
            # Check course catalog for known credit value
            catalog_credits = None
            if COURSE_CATALOG_AVAILABLE:
                info = get_course_info(c.course_code)
                if info and 'credits' in info:
                    catalog_credits = float(info['credits'])
            
            if c.credits == 2.0 and catalog_credits is not None and catalog_credits >= 3.0:
                # OCR read 2.0 but catalog says 3+ — likely OCR misread of 3.0
                # Default to 3.0 rather than exact catalog value, since different
                # programs may assign different credits (e.g., CHE101=4 in catalog
                # but 3.0 for engineering students)
                _logger.info(f"Credit sanity: {c.course_code} 2.0->3.0 (catalog confirms 3+ credits)")
                c.credits = 3.0
                continue
            
            # Heuristic for courses not in catalog or with unusual credits
            is_thesis = False
            for i, line in enumerate(lines):
                if c.course_code in line:
                    for j in range(i, min(i + 4, len(lines))):
                        title_line = lines[j].strip().lower()
                        if 'thesis' in title_line or 'project' in title_line or 'internship' in title_line:
                            is_thesis = True
                    break
            
            if c.credits == 4.0 and not is_thesis:
                _logger.info(f"Credit sanity: {c.course_code} 4.0->3.0 (non-thesis course)")
                c.credits = 3.0
            elif c.credits > 4.0 and not is_thesis:
                _logger.info(f"Credit sanity: {c.course_code} {c.credits}->3.0 (unusual credits)")
                c.credits = 3.0
        
        # ===== COURSE VALIDATION =====
        unknown_courses = validate_courses_against_catalog(courses)
        if unknown_courses:
            _logger.info(f"Found {len(unknown_courses)} courses not in catalog: {unknown_courses[:5]}...")

        return OCRResult(
            success=True,
            courses=courses,
            raw_text=raw_text,
            student_name=student_name,
            student_id=student_id,
            cgpa=cgpa,
            total_credits=total_credits_from_pdf,
            department_code=department_code,
            department_name=department_name,
            department_full_name=department_full_name,
            department_valid=department_valid,
            unknown_courses=unknown_courses
        )
    
    def _is_watermark_only(self, line: str) -> bool:
        """Check if line contains only watermark text."""
        if not line or len(line) < 3:
            return True
        
        line_upper = line.upper().strip()
        
        # Pure watermark patterns
        watermarks = [
            'NORTH SOUTH', 'UNIVERSITY', 'NIVERSITY', 'IVERSITY', 'VERSITY',
            'ERSITY', 'RTH SO', 'ORTH SC', 'TH SOUTH', 'SOUTH UNIV',
            'NORTH S', 'RTH SOUTH', 'OUTH UNIV', 'UNIVER', 'IVERSIT'
        ]
        
        # If the line is short and matches watermark, skip it
        if len(line_upper) < 25:
            for w in watermarks:
                if w in line_upper:
                    # But don't skip if it has a course code
                    if re.search(r'[A-Z]{3}\s?\d{3}', line_upper):
                        return False
                    return True
        
        return False


# Alias for compatibility
TranscriptOCR = WebOCR


def main():
    """Test CLI."""
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ocr_web.py <file.pdf|image.png>")
        print("\nOCR Engines:")
        print(f"  Google Vision: {'Configured' if GOOGLE_VISION_API_KEY else 'Not configured'}")
        print(f"  Azure Document Intelligence: {'Configured' if AZURE_DOC_INTELLIGENCE_KEY else 'Not configured'}")
        print("\nTo use Google Vision (most accurate):")
        print("  set GOOGLE_VISION_API_KEY=your_key")
        sys.exit(1)

    ocr = WebOCR()
    result = ocr.extract(sys.argv[1])

    if result.success:
        print(f"\n[OK] Extracted {result.course_count} courses")
        print(f"  Engine: {result.engine_used}")
        print(f"  Student ID: {result.student_id or 'N/A'}")
        print(f"  CGPA: {result.cgpa or 'N/A'}")
        print("\nCSV Output:")
        print(result.csv_data)
    else:
        print(f"[ERROR] {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
