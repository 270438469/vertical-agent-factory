"""Durable request metering and idempotency storage."""

import json
import sqlite3
import threading
from datetime import datetime, timezone


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _month_prefix():
    return datetime.now(timezone.utc).strftime("%Y-%m")


class UsageStore(object):
    def __init__(self, path):
        self.path = str(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS usage_events (
                    request_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    latency_ms INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_usage_tenant_month
                    ON usage_events(tenant_id, created_at);
                CREATE TABLE IF NOT EXISTS idempotency_records (
                    tenant_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, idempotency_key)
                );
                """
            )

    def request_count(self, tenant_id):
        prefix = _month_prefix() + "%"
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM usage_events "
                "WHERE tenant_id = ? AND created_at LIKE ?",
                (tenant_id, prefix),
            ).fetchone()
        return int(row["total"])

    def summary(self, tenant_id):
        prefix = _month_prefix() + "%"
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS requests,
                       COALESCE(SUM(input_tokens), 0) AS input_tokens,
                       COALESCE(SUM(output_tokens), 0) AS output_tokens,
                       COALESCE(SUM(total_tokens), 0) AS total_tokens
                FROM usage_events
                WHERE tenant_id = ? AND created_at LIKE ?
                """,
                (tenant_id, prefix),
            ).fetchone()
        return dict(row)

    def record(self, request_id, tenant_id, provider, model, status, usage, latency_ms):
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO usage_events (
                    request_id, tenant_id, created_at, provider, model, status,
                    input_tokens, output_tokens, total_tokens, latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    tenant_id,
                    _utc_now(),
                    provider,
                    model or "",
                    status,
                    int(usage.get("input_tokens") or 0),
                    int(usage.get("output_tokens") or 0),
                    int(usage.get("total_tokens") or 0),
                    int(latency_ms),
                ),
            )

    def idempotent_response(self, tenant_id, idempotency_key):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT request_hash, response_json FROM idempotency_records "
                "WHERE tenant_id = ? AND idempotency_key = ?",
                (tenant_id, idempotency_key),
            ).fetchone()
        if row is None:
            return None
        return row["request_hash"], json.loads(row["response_json"])

    def save_idempotent_response(
        self, tenant_id, idempotency_key, request_hash, response
    ):
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO idempotency_records (
                    tenant_id, idempotency_key, request_hash, response_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    idempotency_key,
                    request_hash,
                    json.dumps(response, ensure_ascii=False, sort_keys=True),
                    _utc_now(),
                ),
            )
