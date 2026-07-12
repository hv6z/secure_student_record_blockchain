"""Khởi tạo ứng dụng Flask và các lớp bảo vệ dùng chung."""

from __future__ import annotations

import secrets
from typing import Any

from flask import Flask, abort, render_template, request, session

from src.config import Settings
from src.services.record_service import RecordService


def create_app(settings: Settings | None = None) -> Flask:
    """Tạo ứng dụng và nối giao diện với dịch vụ hồ sơ duy nhất."""

    resolved = settings or Settings.from_env()
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_mapping(
        SECRET_KEY=resolved.flask_secret_key,
        TESTING=resolved.testing,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=1_000_000,
    )

    service = RecordService(
        resolved.database_path,
        resolved.encryption_key,
        key_id=resolved.key_id,
    )
    service.initialize()
    app.extensions["record_service"] = service

    @app.context_processor
    def add_template_helpers() -> dict[str, Any]:
        return {
            "csrf_token": _csrf_token,
            "operation_label": _operation_label,
        }

    @app.before_request
    def protect_post_requests() -> None:
        if request.method != "POST":
            return
        expected = session.get("_csrf_token")
        supplied = request.form.get("csrf_token", "")
        if (
            not isinstance(expected, str)
            or not isinstance(supplied, str)
            or not expected
            or not secrets.compare_digest(expected, supplied)
        ):
            abort(400, description="Phiên biểu mẫu không hợp lệ hoặc đã hết hạn.")

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "img-src 'self' data:; form-action 'self'; frame-ancestors 'self'",
        )
        return response

    from .routes import web

    app.register_blueprint(web)

    @app.errorhandler(400)
    def bad_request(error):
        return (
            render_template(
                "error.html",
                status_code=400,
                title="Yêu cầu không hợp lệ",
                message=getattr(error, "description", "Không thể xử lý yêu cầu."),
            ),
            400,
        )

    @app.errorhandler(404)
    def not_found(_error):
        return (
            render_template(
                "error.html",
                status_code=404,
                title="Không tìm thấy nội dung",
                message="Nội dung bạn yêu cầu không tồn tại hoặc đã được chuyển đi.",
            ),
            404,
        )

    @app.errorhandler(500)
    def internal_error(_error):
        return (
            render_template(
                "error.html",
                status_code=500,
                title="Không thể hoàn tất yêu cầu",
                message="Hệ thống gặp lỗi ngoài dự kiến. Dữ liệu chưa được thay đổi.",
            ),
            500,
        )

    return app


def _csrf_token() -> str:
    token = session.get("_csrf_token")
    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def _operation_label(operation: str) -> str:
    return {
        "GENESIS": "Khởi nguyên",
        "CREATE": "Tạo hồ sơ",
        "UPDATE": "Cập nhật",
        "DELETE": "Xóa hồ sơ",
    }.get(operation, operation)
