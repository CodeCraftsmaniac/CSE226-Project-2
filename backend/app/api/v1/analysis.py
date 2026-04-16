"""
Analysis Endpoints
==================
Degree audit analysis retrieval.
FastAPI analysis endpoints.
"""
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel

from app.middleware.rate_limit import limiter

router = APIRouter()
logger = logging.getLogger(__name__)


# Lazy loading functions
def get_dependencies():
    """Lazy load dependency functions."""
    try:
        from app.dependencies import (
            get_current_user_optional, get_db_user_id, 
            DB_MODULE_AVAILABLE
        )
        
        async def require_auth(authorization):
            """Wrapper to require authentication."""
            user = await get_current_user_optional(authorization)
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return user
        
        def require_db():
            """Wrapper to require database."""
            if not DB_MODULE_AVAILABLE:
                raise HTTPException(503, "Database not available")
        
        return require_auth, get_db_user_id, DB_MODULE_AVAILABLE, require_db
    except Exception as e:
        logger.warning(f"Could not load dependencies: {e}")
        async def _require_auth(authorization = None):
            raise HTTPException(401, "Auth not available")
        async def _get_db_user_id(user):
            return None
        def _require_db():
            raise HTTPException(503, "Database not available")
        return _require_auth, _get_db_user_id, False, _require_db


def get_db_functions():
    """Lazy load database functions."""
    try:
        from database import get_user_scans, get_scan_by_id
        return get_user_scans, get_scan_by_id
    except Exception:
        return None, None


# ═══════════════════════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class AnalysisResponse(BaseModel):
    """Analysis response."""
    success: bool = True
    analysis: Dict[str, Any]


# ═══════════════════════════════════════════════════════════════════════════════
# Analysis Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/analysis/latest", response_model=AnalysisResponse)
@limiter.limit("30/minute")
async def get_latest_analysis(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Get latest degree audit analysis.
    
    Returns the most recent transcript analysis for the authenticated user.
    Requires authentication.
    """
    import json
    
    get_current_user, get_db_user_id, DB_MODULE_AVAILABLE, require_db = get_dependencies()
    get_user_scans, get_scan_by_id = get_db_functions()
    
    # Require DB
    require_db()
    
    # Get user
    user = await get_current_user(authorization)
    logger.info(f"Latest analysis request for user: {user.get('email')}")
    
    if not get_user_scans:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Get db_id for queries
    db_user_id = await get_db_user_id(user)
    logger.info(f"User db_id: {db_user_id}")
    
    if not db_user_id:
        logger.warning(f"Could not get db_user_id for {user.get('email')}")
        raise HTTPException(status_code=404, detail="No analysis found")
    
    # Get latest scan ID (lightweight query without analysis_data)
    scans = get_user_scans(db_user_id, limit=1)
    
    if not scans or len(scans) == 0:
        logger.info(f"No scans found for user {db_user_id}")
        raise HTTPException(status_code=404, detail="No analysis found")
    
    scan_id = scans[0]['id']
    logger.info(f"Found latest scan {scan_id} for user {db_user_id}")
    
    # Fetch full scan with analysis_data
    scan = get_scan_by_id(scan_id) if get_scan_by_id else scans[0]
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Parse analysis_data if it's a JSON string
    analysis_data = scan.get('analysis_data', {})
    if isinstance(analysis_data, str):
        try:
            analysis_data = json.loads(analysis_data)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse analysis_data for scan {scan['id']}")
            analysis_data = {}
    
    # Determine required credits from curriculum data (not hardcoded)
    curriculum = analysis_data.get('curriculum', {})
    required_credits = curriculum.get('total_credits', 130)

    # Build response with all necessary fields
    analysis = {
        'id': scan['id'],
        'filename': scan['filename'],
        'student_name': scan.get('student_name', ''),
        'student_id': scan.get('student_id', ''),
        'department': scan.get('department', ''),
        'cgpa': float(scan.get('cgpa', 0)),
        'total_courses': scan.get('total_courses', 0),
        'total_credits': float(scan.get('total_credits', 0)),
        'earned_credits': float(scan.get('total_credits', 0)),  # Alias
        'required_credits': required_credits,
        'remaining_credits': max(0, required_credits - float(scan.get('total_credits', 0))),
        'graduation_progress': min(1.0, float(scan.get('total_credits', 0)) / required_credits) if required_credits > 0 else 0,
        'courses': analysis_data.get('courses', []),
        'level1': analysis_data.get('level1', {}),
        'level2': analysis_data.get('level2', {}),
        'level3': analysis_data.get('level3', {}),
        'curriculum': curriculum,
        'summary': analysis_data.get('summary', ''),
        'created_at': scan['created_at'],
        'source': scan.get('source', 'web'),
    }
    
    return AnalysisResponse(analysis=analysis)
