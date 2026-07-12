"""Lược đồ dữ liệu chỉ lưu hồ sơ ở dạng mã hóa."""

from __future__ import annotations

from pathlib import Path

from src.blockchain.block import genesis_block

from .connection import connect_database, immediate_transaction


SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    record_id TEXT PRIMARY KEY,
    lookup_token BLOB NOT NULL UNIQUE,
    current_version INTEGER NOT NULL CHECK (current_version >= 1),
    status TEXT NOT NULL CHECK (status IN ('active', 'deleted')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS record_versions (
    record_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 1),
    schema_version INTEGER NOT NULL CHECK (schema_version >= 1),
    algorithm TEXT NOT NULL,
    key_id TEXT NOT NULL,
    nonce BLOB NOT NULL,
    ciphertext BLOB NOT NULL,
    envelope_hash TEXT NOT NULL CHECK (length(envelope_hash) = 64),
    operation TEXT NOT NULL CHECK (operation IN ('CREATE', 'UPDATE', 'DELETE')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (record_id, version),
    UNIQUE (key_id, nonce),
    FOREIGN KEY (record_id) REFERENCES records(record_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS audit_blocks (
    block_index INTEGER PRIMARY KEY CHECK (block_index >= 0),
    timestamp TEXT NOT NULL,
    previous_hash TEXT NOT NULL CHECK (length(previous_hash) = 64),
    record_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 0),
    operation TEXT NOT NULL CHECK (operation IN ('GENESIS', 'CREATE', 'UPDATE', 'DELETE')),
    envelope_hash TEXT NOT NULL CHECK (length(envelope_hash) = 64),
    block_hash TEXT NOT NULL UNIQUE CHECK (length(block_hash) = 64)
);

CREATE INDEX IF NOT EXISTS idx_record_versions_record
    ON record_versions(record_id, version);
CREATE INDEX IF NOT EXISTS idx_audit_blocks_record
    ON audit_blocks(record_id, version);
"""


def initialize_database(database_path: str | Path) -> None:
    """Tạo ba bảng và khối khởi nguyên bất biến nếu cơ sở dữ liệu còn trống."""

    path = Path(database_path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)

    connection = connect_database(path)
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        with immediate_transaction(connection):
            connection.executescript(SCHEMA)
            block = genesis_block()
            connection.execute(
                """
                INSERT OR IGNORE INTO audit_blocks (
                    block_index, timestamp, previous_hash, record_id,
                    version, operation, envelope_hash, block_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                block.as_database_tuple(),
            )
            connection.execute("PRAGMA user_version = 1")
    finally:
        connection.close()
