"""Upload endpoint tests."""

import io

import database
from app.api.v1 import upload as upload_routes


def test_upload_validation_no_file(test_client):
    """Test upload validation fails without file."""
    response = test_client.post("/api/upload/validate")
    assert response.status_code == 422


def test_upload_validation_with_csv(test_client, sample_csv_content):
    """Test upload validation accepts CSV file."""
    csv_file = io.BytesIO(sample_csv_content.encode())
    response = test_client.post(
        "/api/upload/validate",
        files={"file": ("transcript.csv", csv_file, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


def test_upload_validation_rejects_content_mismatch(test_client):
    """A declared PDF must contain actual PDF bytes."""
    fake_pdf = io.BytesIO(b"this is definitely not a pdf")
    response = test_client.post(
        "/api/upload/validate",
        files={"file": ("transcript.pdf", fake_pdf, "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "do not match" in data["error"].lower()


def test_upload_csv_processing(test_client, sample_csv_content, monkeypatch):
    """Test CSV file upload and processing."""
    monkeypatch.setattr(
        upload_routes,
        "get_analysis_engine",
        lambda: (
            True,
            lambda courses, kb_path=None, student_id=None: {
                "level1": {},
                "level2": {"cgpa": 3.9, "gpa_credits": 15},
                "level3": {},
                "courses": [{"code": "CSE115", "credits": 3, "grade": "A"}],
            },
        ),
    )

    csv_file = io.BytesIO(sample_csv_content.encode())
    response = test_client.post(
        "/api/upload",
        files={"file": ("transcript.csv", csv_file, "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_upload_invalid_extension(test_client):
    """Test upload rejects invalid file types."""
    fake_file = io.BytesIO(b"not a valid file")
    response = test_client.post(
        "/api/upload",
        files={"file": ("test.exe", fake_file, "application/octet-stream")},
    )
    assert response.status_code == 400


def test_batch_upload_csv_uses_parsed_courses(test_client, sample_csv_content, monkeypatch):
    """Batch CSV uploads should analyze parsed course rows, not raw text."""
    captured = {}

    def fake_run_analysis(courses, kb_path=None, student_id=None):
        captured["courses"] = courses
        captured["kb_path"] = kb_path
        return {
            "level1": {},
            "level2": {"cgpa": 3.75, "gpa_credits": 15},
            "level3": {},
            "courses": [{"code": "CSE115", "credits": 3, "grade": "A"}],
        }

    monkeypatch.setattr(upload_routes, "get_analysis_engine", lambda: (True, fake_run_analysis))

    csv_file = io.BytesIO(sample_csv_content.encode())
    response = test_client.post(
        "/api/upload/batch",
        files=[("files", ("transcript.csv", csv_file, "text/csv"))],
    )

    assert response.status_code == 200
    assert response.json()["processed"] == 1
    assert isinstance(captured["courses"], list)
    assert captured["courses"][0]["course_code"] == "ENG101"


def test_export_csv_uses_top_level_courses(test_client, monkeypatch):
    """Exports should use the canonical top-level course list."""
    async def fake_get_current_user_optional(_authorization=None):
        return {"id": "supabase-user", "email": "student@example.com"}

    async def fake_get_db_user_id(_user):
        return "db-user-1"

    monkeypatch.setattr(
        upload_routes,
        "get_dependencies",
        lambda: (fake_get_current_user_optional, fake_get_db_user_id, True),
    )
    monkeypatch.setattr(
        database,
        "get_scan_by_id",
        lambda scan_id: {
            "id": scan_id,
            "user_id": "db-user-1",
            "filename": "transcript.csv",
            "created_at": "2026-04-16T00:00:00Z",
            "analysis_data": {
                "level1": {"valid_entries": []},
                "level2": {
                    "cgpa": 3.8,
                    "gpa_credits": 6,
                    "total_quality_points": 22.8,
                    "waiver": {"name": "Dean's Scholarship", "level": "25%"},
                },
                "level3": {},
                "courses": [
                    {"code": "CSE115", "credits": 3, "grade": "A", "quality_points": 12, "semester": "Spring 2021"},
                    {"code": "MAT120", "credits": 3, "grade": "A-", "quality_points": 10.8, "semester": "Spring 2021"},
                ],
            },
        },
    )

    response = test_client.get(
        "/api/export/test-scan?format=csv",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    body = response.text
    assert "CSE115" in body
    assert "MAT120" in body
    assert "Dean's Scholarship" in body
