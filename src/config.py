"""Đọc và kiểm tra cấu hình chạy ứng dụng."""

from __future__ import annotations

import base64
import binascii
import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ConfigurationError(ValueError):
    """Cấu hình thiếu hoặc không hợp lệ."""


def load_env_file(path: Path | None = None) -> None:
    """Đọc tệp .env đơn giản mà không ghi đè biến môi trường hiện có."""

    env_path = path or PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name:
            os.environ.setdefault(name, value)


def decode_aes_key(encoded_key: str) -> bytes:
    """Giải mã khóa base64 và bắt buộc khóa AES-256 dài 32 byte."""

    try:
        key = base64.b64decode(encoded_key, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ConfigurationError("AES_KEY không phải chuỗi base64 hợp lệ.") from exc
    if len(key) != 32:
        raise ConfigurationError("AES_KEY phải biểu diễn đúng 32 byte.")
    return key


@dataclass(frozen=True, slots=True)
class Settings:
    """Cấu hình đã được kiểm tra."""

    database_path: Path
    encryption_key: bytes
    flask_secret_key: str
    key_id: str = "key-v1"
    testing: bool = False

    @classmethod
    def from_env(cls, *, testing: bool = False) -> "Settings":
        load_env_file()
        encoded_key = os.getenv("AES_KEY", "").strip()
        if not encoded_key:
            raise ConfigurationError(
                "Thiếu AES_KEY. Hãy chạy: python scripts/generate_key.py"
            )

        secret_key = os.getenv("FLASK_SECRET_KEY", "").strip()
        if not secret_key:
            raise ConfigurationError(
                "Thiếu FLASK_SECRET_KEY. Hãy chạy: python scripts/generate_key.py"
            )

        configured_path = Path(
            os.getenv("DATABASE_PATH", "instance/student_records.db")
        )
        database_path = (
            configured_path
            if configured_path.is_absolute()
            else PROJECT_ROOT / configured_path
        )
        return cls(
            database_path=database_path,
            encryption_key=decode_aes_key(encoded_key),
            flask_secret_key=secret_key,
            key_id=os.getenv("KEY_ID", "key-v1").strip() or "key-v1",
            testing=testing,
        )

