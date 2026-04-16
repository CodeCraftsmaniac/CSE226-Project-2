"""
NSU Degree Audit - Supabase Database Module
============================================
Handles database operations for user auth and scan history.
Uses cse226_ocr_ prefixed tables to avoid conflicts.

Thread-safe connection pooling for 20+ concurrent users.
"""

import os
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Load configuration from centralized settings
try:
    from app.config import get_settings
    _settings = get_settings()
    SUPABASE_URL = _settings.SUPABASE_URL
    SUPABASE_KEY = _settings.SUPABASE_ANON_KEY
    SUPABASE_SERVICE_ROLE_KEY = _settings.SUPABASE_SERVICE_ROLE_KEY
    logger.info("Database module: Loaded settings from config")
except Exception as e:
    # Graceful fallback to environment variables (matches auth.py pattern)
    logger.warning(f"Database module: Could not load from config ({e}), using env vars")
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', os.getenv('SUPABASE_ANON_KEY', ''))
    SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')

# Thread-safe client management for concurrent users
_supabase_client = None
_client_lock = threading.Lock()
DEVICE_CODES_TABLE = 'cse226_ocr_device_codes'

def get_supabase():
    """
    Get or create Supabase client (thread-safe).
    Uses double-check locking for concurrent access.
    Uses service role key for backend operations.
    """
    global _supabase_client
    if _supabase_client is None:
        with _client_lock:
            # Double-check after acquiring lock
            if _supabase_client is None:
                try:
                    from supabase import create_client
                    # Use service role key for backend operations (bypasses RLS)
                    key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
                    if not key:
                        logger.error("No Supabase key available")
                        return None
                    logger.info(f"Creating Supabase client: {SUPABASE_URL[:40]}...")
                    _supabase_client = create_client(SUPABASE_URL, key)
                    logger.info("Supabase client created successfully")
                except ImportError as e:
                    logger.error(f"Supabase SDK not installed: {e}")
                    return None
                except Exception as e:
                    logger.error(f"Failed to create Supabase client: {e}")
                    return None
    return _supabase_client


def _normalize_email(email: str) -> str:
    """Normalize user emails for consistent lookups."""
    return (email or '').strip().lower()


def _to_iso8601(value: Any) -> Optional[str]:
    """Convert common timestamp types to an ISO-8601 string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str):
        return value
    else:
        return str(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


# ─── User Operations ────────────────────────────────────────────────────────────

def create_user(email: str, name: str, provider: str = 'google') -> Optional[Dict]:
    """Create or get existing user in cse226_ocr_users table."""
    supabase = get_supabase()
    if not supabase:
        logger.error("create_user: Supabase client not available")
        return None

    normalized_email = _normalize_email(email)
    display_name = (name or '').strip()

    try:
        # Check if user exists
        result = supabase.table('cse226_ocr_users').select('*').eq('email', normalized_email).execute()

        if result.data:
            # Update last login
            update_payload = {
                'last_login': datetime.now(timezone.utc).isoformat(),
            }
            if display_name:
                update_payload['name'] = display_name
            if provider:
                update_payload['provider'] = provider

            update_result = supabase.table('cse226_ocr_users').update(update_payload).eq('email', normalized_email).execute()
            logger.info(f"User already exists: {normalized_email}")
            if update_result.data:
                return update_result.data[0]
            refreshed = supabase.table('cse226_ocr_users').select('*').eq('email', normalized_email).execute()
            return refreshed.data[0] if refreshed.data else result.data[0]

        # Create new user
        new_user = {
            'email': normalized_email,
            'name': display_name,
            'provider': provider
        }

        result = supabase.table('cse226_ocr_users').insert(new_user).execute()
        logger.info(f"Created new user: {normalized_email}")
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Create user error for {normalized_email}: {e}")
        return None


def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email from cse226_ocr_users table."""
    supabase = get_supabase()
    if not supabase:
        return None
    normalized_email = _normalize_email(email)
    try:
        result = supabase.table('cse226_ocr_users').select('*').eq('email', normalized_email).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Get user by ID from cse226_ocr_users table."""
    supabase = get_supabase()
    if not supabase:
        return None
    try:
        result = supabase.table('cse226_ocr_users').select('*').eq('id', user_id).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


def get_user_by_token(token: str) -> Optional[Dict]:
    """Get user by CLI token from cse226_ocr_users table."""
    supabase = get_supabase()
    if not supabase:
        return None
    try:
        result = supabase.table('cse226_ocr_users').select('*').eq('cli_token', token).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        # Column may not exist yet - try alternative lookup
        logger.debug(f"get_user_by_token: cli_token column may not exist: {e}")
        return None


def save_user_token(user_id: str, token: str) -> bool:
    """Save CLI token for a user."""
    supabase = get_supabase()
    if not supabase:
        return False
    try:
        supabase.table('cse226_ocr_users').update({
            'cli_token': token
        }).eq('id', user_id).execute()
        logger.info(f"Token saved for user {user_id}")
        return True
    except Exception as e:
        # Column may not exist - log and continue
        logger.warning(f"save_user_token: cli_token column may not exist: {e}")
        return False


# ─── Scan History Operations ────────────────────────────────────────────────────

def save_scan(
    user_id: str,
    filename: str,
    total_courses: int,
    total_credits: float,
    cgpa: float,
    analysis_data: Dict[str, Any],
    source: str = 'web'
) -> Optional[Dict]:
    """Save a transcript scan to cse226_ocr_scans table."""
    supabase = get_supabase()
    if not supabase:
        logger.error("save_scan: Supabase client not available")
        return None
    
    try:
        scan_record = {
            'user_id': user_id,
            'filename': filename,
            'total_courses': total_courses,
            'total_credits': total_credits,
            'cgpa': cgpa,
            'analysis_data': analysis_data,
            'source': source
        }
        
        result = supabase.table('cse226_ocr_scans').insert(scan_record).execute()
        if result.data:
            logger.info(f"Saved scan for user {user_id}: {filename}")
            return result.data[0]
        else:
            logger.error(f"save_scan: No data returned from insert")
            return None
    except Exception as e:
        logger.error(f"Save scan error for user {user_id}: {e}")
        return None


def get_user_scans(user_id: str, limit: int = 50) -> List[Dict]:
    """Get scan history for a user from cse226_ocr_scans table.
    Excludes analysis_data for faster listing (fetched separately in detail view).
    """
    supabase = get_supabase()
    if not supabase:
        return []
    try:
        # Select only needed fields for listing (exclude large analysis_data)
        result = supabase.table('cse226_ocr_scans')\
            .select('id, user_id, filename, total_courses, total_credits, cgpa, source, created_at')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        return result.data or []
    except Exception:
        return []


def get_scan_by_id(scan_id: str) -> Optional[Dict]:
    """Get a specific scan by ID from cse226_ocr_scans table."""
    supabase = get_supabase()
    if not supabase:
        return None
    try:
        result = supabase.table('cse226_ocr_scans').select('*').eq('id', scan_id).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


def delete_scan(scan_id: str, user_id: str) -> bool:
    """Delete a scan (only if owned by user) from cse226_ocr_scans table."""
    supabase = get_supabase()
    if not supabase:
        return False
    try:
        result = supabase.table('cse226_ocr_scans')\
            .delete()\
            .eq('id', scan_id)\
            .eq('user_id', user_id)\
            .execute()
        return len(result.data) > 0 if result.data else False
    except Exception:
        return False


# ─── Analytics Operations ───────────────────────────────────────────────────────

def get_user_stats(user_id: str) -> Dict[str, Any]:
    """Get statistics for a user from cse226_ocr_scans table."""
    supabase = get_supabase()
    if not supabase:
        return {'total_scans': 0, 'avg_cgpa': 0.0, 'total_courses_scanned': 0, 'total_credits_scanned': 0.0}
    
    try:
        scans = supabase.table('cse226_ocr_scans')\
            .select('cgpa, total_credits, total_courses')\
            .eq('user_id', user_id)\
            .execute()
        
        if not scans.data:
            return {
                'total_scans': 0,
                'avg_cgpa': 0.0,
                'total_courses_scanned': 0,
                'total_credits_scanned': 0.0
            }
        
        cgpas = [float(s['cgpa']) for s in scans.data if s.get('cgpa')]
        
        return {
            'total_scans': len(scans.data),
            'avg_cgpa': round(sum(cgpas) / len(cgpas), 2) if cgpas else 0.0,
            'total_courses_scanned': sum(s.get('total_courses', 0) for s in scans.data),
            'total_credits_scanned': sum(float(s.get('total_credits', 0)) for s in scans.data)
        }
    except Exception:
        return {'total_scans': 0, 'avg_cgpa': 0.0, 'total_courses_scanned': 0, 'total_credits_scanned': 0.0}


# ─── Device Code Operations ────────────────────────────────────────────────────

def save_device_code(
    device_code: str,
    status: str,
    expires_at: Any,
    token: Optional[str] = None,
    user_data: Optional[Dict[str, Any]] = None,
    created_at: Any = None,
) -> Optional[Dict[str, Any]]:
    """Create or update a CLI device-code record."""
    supabase = get_supabase()
    if not supabase:
        logger.error("save_device_code: Supabase client not available")
        return None

    record = {
        'device_code': (device_code or '').strip().upper(),
        'status': status,
        'expires_at': _to_iso8601(expires_at),
        'token': token,
        'user_data': user_data,
        'created_at': _to_iso8601(created_at or datetime.now(timezone.utc)),
    }

    try:
        result = supabase.table(DEVICE_CODES_TABLE).upsert(record).execute()
        return result.data[0] if result.data else record
    except Exception as e:
        logger.error(f"save_device_code error for {record['device_code']}: {e}")
        return None


def get_device_code(device_code: str) -> Optional[Dict[str, Any]]:
    """Get a device-code record by code."""
    supabase = get_supabase()
    if not supabase:
        return None

    try:
        result = supabase.table(DEVICE_CODES_TABLE).select('*').eq(
            'device_code',
            (device_code or '').strip().upper(),
        ).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.debug(f"get_device_code failed: {e}")
        return None


def delete_device_code(device_code: str) -> bool:
    """Delete a device-code record."""
    supabase = get_supabase()
    if not supabase:
        return False

    try:
        result = supabase.table(DEVICE_CODES_TABLE).delete().eq(
            'device_code',
            (device_code or '').strip().upper(),
        ).execute()
        return bool(result.data)
    except Exception as e:
        logger.debug(f"delete_device_code failed: {e}")
        return False


def consume_device_code(device_code: str) -> Optional[Dict[str, Any]]:
    """Atomically fetch and delete a device-code record.

    Uses a single Supabase ``delete`` call which returns the deleted rows,
    making the consume operation atomic and preventing race conditions
    where two concurrent polls could both read the same code before
    either deletes it.
    """
    supabase = get_supabase()
    if not supabase:
        return None

    code = (device_code or '').strip().upper()
    if not code:
        return None

    try:
        # delete() returns the deleted rows — atomic read-and-remove
        result = supabase.table(DEVICE_CODES_TABLE).delete().eq(
            'device_code', code,
        ).eq('status', 'pending').execute()

        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.debug(f"consume_device_code failed: {e}")
        return None


def cleanup_expired_device_codes(now: Any = None) -> int:
    """Delete expired device-code records and return the count removed."""
    supabase = get_supabase()
    if not supabase:
        return 0

    cutoff = _to_iso8601(now or datetime.now(timezone.utc))
    try:
        result = supabase.table(DEVICE_CODES_TABLE).delete().lt('expires_at', cutoff).execute()
        return len(result.data or [])
    except Exception as e:
        logger.debug(f"cleanup_expired_device_codes failed: {e}")
        return 0


def count_pending_device_codes(now: Any = None) -> int:
    """Count still-pending, non-expired device codes."""
    supabase = get_supabase()
    if not supabase:
        return 0

    cutoff = _to_iso8601(now or datetime.now(timezone.utc))
    try:
        result = supabase.table(DEVICE_CODES_TABLE).select('device_code').eq(
            'status',
            'pending',
        ).gte('expires_at', cutoff).execute()
        return len(result.data or [])
    except Exception as e:
        logger.debug(f"count_pending_device_codes failed: {e}")
        return 0


# ─── Health Check ───────────────────────────────────────────────────────────────

def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        supabase = get_supabase()
        if not supabase:
            return False
        supabase.table('cse226_ocr_users').select('id').limit(1).execute()
        return True
    except Exception:
        return False
