"""
Global configuration, paths, and default academic specs.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
VECTOR_DB_DIR = DATA_DIR / "vector_db"
OUTPUT_DIR = BASE_DIR / "output"


for d in [DATA_DIR, UPLOADS_DIR, VECTOR_DB_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Default University Formatting Specs
DEFAULT_FORMAT_SPECS = {
    "font_family": "Times-Roman",
    "font_family_bold": "Times-Bold",
    "font_family_italic": "Times-Italic",
    "font_size": 12,
    "line_spacing": 1.25,
    "alignment": "JUSTIFIED",
    "page_size": "A4",
    "orientation": "PORTRAIT",
    "margin_inches": 1.0,  # 72 points
    "max_pages": 12,
    "max_file_size_mb": 2.0,
    "word_counts": {
        "10_mark": {"min": 400, "max": 500, "target": 450},
        "5_mark": {"min": 200, "max": 250, "target": 225},
        "default": {"min": 350, "max": 450, "target": 400}
    }
}
