# NSU Degree Audit - App Package
import sys
from pathlib import Path

# Add backend directory to sys.path once at package load so that legacy
# modules (auth, database, core, ocr_web, etc.) can be imported from
# anywhere inside the app package without each file repeating this.
_backend_path = str(Path(__file__).parent.parent)
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)
