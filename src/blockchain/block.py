"""Cấu trúc và phép băm khối kiểm toán."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


BLOCK_HASH_DOMAIN = b"secure-student-record/audit-block/v1\x00"
ZERO_HASH = "0" * 64
GENESIS_TIMESTAMP = "1970-01-01T00:00:00.000000Z"


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def calculate_block_hash(
    *,
    block_index: int,
    timestamp: str,
    previous_hash: str,
    record_id: str,
    version: int,
    operation: str,
    envelope_hash: str,
) -> str:
    """Băm JSON chuẩn, có tiền tố miền để tránh dùng nhầm ngữ cảnh."""

    payload = {
        "block_index": block_index,
        "envelope_hash": envelope_hash,
        "operation": operation,
        "previous_hash": previous_hash,
        "record_id": record_id,
        "timestamp": timestamp,
        "version": version,
    }
    return hashlib.sha256(BLOCK_HASH_DOMAIN + _canonical_json_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class AuditBlock:
    block_index: int
    timestamp: str
    previous_hash: str
    record_id: str
    version: int
    operation: str
    envelope_hash: str
    block_hash: str

    def expected_hash(self) -> str:
        return calculate_block_hash(
            block_index=self.block_index,
            timestamp=self.timestamp,
            previous_hash=self.previous_hash,
            record_id=self.record_id,
            version=self.version,
            operation=self.operation,
            envelope_hash=self.envelope_hash,
        )

    def as_database_tuple(self) -> tuple[Any, ...]:
        return (
            self.block_index,
            self.timestamp,
            self.previous_hash,
            self.record_id,
            self.version,
            self.operation,
            self.envelope_hash,
            self.block_hash,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_index": self.block_index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "record_id": self.record_id,
            "version": self.version,
            "operation": self.operation,
            "envelope_hash": self.envelope_hash,
            "block_hash": self.block_hash,
        }


def genesis_block() -> AuditBlock:
    """Trả về khối khởi nguyên cố định, giống nhau ở mọi lần chạy."""

    block_hash = calculate_block_hash(
        block_index=0,
        timestamp=GENESIS_TIMESTAMP,
        previous_hash=ZERO_HASH,
        record_id="",
        version=0,
        operation="GENESIS",
        envelope_hash=ZERO_HASH,
    )
    return AuditBlock(
        block_index=0,
        timestamp=GENESIS_TIMESTAMP,
        previous_hash=ZERO_HASH,
        record_id="",
        version=0,
        operation="GENESIS",
        envelope_hash=ZERO_HASH,
        block_hash=block_hash,
    )


def new_block(
    previous: AuditBlock,
    *,
    timestamp: str,
    record_id: str,
    version: int,
    operation: str,
    envelope_hash: str,
) -> AuditBlock:
    block_index = previous.block_index + 1
    block_hash = calculate_block_hash(
        block_index=block_index,
        timestamp=timestamp,
        previous_hash=previous.block_hash,
        record_id=record_id,
        version=version,
        operation=operation,
        envelope_hash=envelope_hash,
    )
    return AuditBlock(
        block_index=block_index,
        timestamp=timestamp,
        previous_hash=previous.block_hash,
        record_id=record_id,
        version=version,
        operation=operation,
        envelope_hash=envelope_hash,
        block_hash=block_hash,
    )


def block_from_row(row: Mapping[str, Any]) -> AuditBlock:
    return AuditBlock(
        block_index=int(row["block_index"]),
        timestamp=str(row["timestamp"]),
        previous_hash=str(row["previous_hash"]),
        record_id=str(row["record_id"]),
        version=int(row["version"]),
        operation=str(row["operation"]),
        envelope_hash=str(row["envelope_hash"]),
        block_hash=str(row["block_hash"]),
    )
