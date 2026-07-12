"""Kiểm thử các luồng web quan trọng và mã chống giả mạo biểu mẫu."""

from __future__ import annotations

import re

import pytest

from src.config import Settings
from src.web.app import create_app


@pytest.fixture
def app(tmp_path):
    settings = Settings(
        database_path=tmp_path / "web.db",
        encryption_key=b"w" * 32,
        flask_secret_key="khoa-phien-kiem-thu",
        key_id="test-key",
        testing=True,
    )
    return create_app(settings)


@pytest.fixture
def client(app):
    return app.test_client()


def _csrf_token(client) -> str:
    response = client.get("/students/new")
    match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    assert match is not None
    return match.group(1).decode("ascii")


def _student_form(csrf_token: str | None = None) -> dict:
    data = {
        "student_code": "SV001",
        "full_name": "Nguyễn Văn An",
        "date_of_birth": "2004-05-20",
        "program": "An toàn thông tin",
        "course_code": "MMH101",
        "course_name": "Mật mã học",
        "score": "8.5",
        "gpa": "8.5",
    }
    if csrf_token is not None:
        data["csrf_token"] = csrf_token
    return data


@pytest.mark.parametrize(
    "path", ["/", "/students", "/students/new", "/blockchain", "/verification"]
)
def test_main_pages_are_available(client, path) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert "Hồ sơ sinh viên".encode("utf-8") in response.data


def test_post_without_csrf_is_rejected(client) -> None:
    response = client.post("/students/new", data=_student_form())
    assert response.status_code == 400
    assert "Phiên biểu mẫu không hợp lệ".encode("utf-8") in response.data


def test_create_student_then_view_detail(client) -> None:
    response = client.post(
        "/students/new",
        data=_student_form(_csrf_token(client)),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Nguyễn Văn An".encode("utf-8") in response.data
    assert "MMH101".encode("utf-8") in response.data
    assert "Dữ liệu toàn vẹn".encode("utf-8") in response.data

    listing = client.get("/students")
    assert "SV001".encode("utf-8") in listing.data


def test_create_update_verify_and_delete_student(client) -> None:
    created = client.post(
        "/students/new",
        data=_student_form(_csrf_token(client)),
        follow_redirects=False,
    )
    assert created.status_code == 302
    detail_path = created.headers["Location"]
    record_id = detail_path.rstrip("/").split("/")[-1]

    changed = _student_form(_csrf_token(client))
    changed.update(
        {
            "full_name": "Nguyễn Văn An đã cập nhật",
            "gpa": "9.0",
            "expected_version": "1",
        }
    )
    updated = client.post(
        f"/students/{record_id}/edit",
        data=changed,
        follow_redirects=True,
    )
    assert updated.status_code == 200
    assert "Nguyễn Văn An đã cập nhật".encode("utf-8") in updated.data

    verified = client.post(
        "/verification",
        data={"csrf_token": _csrf_token(client), "record_id": record_id},
    )
    assert verified.status_code == 200
    assert "Dữ liệu toàn vẹn".encode("utf-8") in verified.data

    deleted = client.post(
        f"/students/{record_id}/delete",
        data={"csrf_token": _csrf_token(client), "expected_version": "2"},
        follow_redirects=True,
    )
    assert deleted.status_code == 200
    assert "SV001".encode("utf-8") not in deleted.data

    detail = client.get(detail_path)
    assert detail.status_code == 200
    assert "Đã xóa".encode("utf-8") in detail.data


def test_security_headers_are_present(client) -> None:
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
