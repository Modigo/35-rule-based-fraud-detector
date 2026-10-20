"""SQLite connection management and schema initialization."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    merchant_category TEXT NOT NULL,
    channel TEXT NOT NULL,
    device_id TEXT,
    country_code TEXT,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_transactions_customer_timestamp
    ON transactions(customer_id, timestamp);

CREATE TABLE IF NOT EXISTS rules (
    rule_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
    configuration_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessments (
    assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL UNIQUE REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    risk_score INTEGER NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    risk_band TEXT NOT NULL CHECK (risk_band IN ('low', 'medium', 'high')),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assessment_rule_results (
    assessment_id INTEGER NOT NULL REFERENCES assessments(assessment_id) ON DELETE CASCADE,
    rule_id TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    explanation TEXT NOT NULL,
    PRIMARY KEY (assessment_id, rule_id)
);

CREATE TABLE IF NOT EXISTS cases (
    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    assessment_id INTEGER REFERENCES assessments(assessment_id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_review', 'closed')),
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cases_status_created ON cases(status, created_at);
"""


class Database:
    """A small SQLite database wrapper. Use ':memory:' for isolated tests."""

    def __init__(self, path: str | Path = "data/fraud_detector.sqlite3") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection, committing on success and always closing it."""
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
