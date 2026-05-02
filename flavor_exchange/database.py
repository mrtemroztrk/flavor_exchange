"""
database.py
───────────
SQLite bağlantısını context manager olarak yönetir.
Tüm modüller veritabanına buradan erişir.

Kullanım:
    from database import get_connection, init_database

    with get_connection() as conn:
        conn.execute("INSERT INTO products ...", (...))
        rows = conn.execute("SELECT * FROM products").fetchall()
"""
import sqlite3
from contextlib import contextmanager
from typing import Iterator

import config


# ─────────────────────────────────────────────────────────────
# Şema (CREATE TABLE komutları)
# ─────────────────────────────────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT CHECK(role IN ('admin', 'waiter')) NOT NULL,
    full_name     TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT UNIQUE NOT NULL,
    category       TEXT NOT NULL,
    cost           REAL NOT NULL,
    base_price     REAL NOT NULL,
    current_price  REAL NOT NULL,
    min_margin     REAL DEFAULT 0.20,
    max_margin     REAL DEFAULT 1.50,
    stock          INTEGER NOT NULL DEFAULT 100,
    initial_stock  INTEGER NOT NULL DEFAULT 100,
    volatility     REAL DEFAULT 0.005,
    is_active      INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    waiter_id     INTEGER,
    table_no      INTEGER,
    status        TEXT CHECK(status IN ('pending','cooking','served','cancelled')) DEFAULT 'pending',
    total_amount  REAL DEFAULT 0,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at  DATETIME,
    is_simulated  INTEGER DEFAULT 0,
    FOREIGN KEY(waiter_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id     INTEGER NOT NULL,
    product_id   INTEGER NOT NULL,
    quantity     INTEGER NOT NULL,
    locked_price REAL NOT NULL,
    FOREIGN KEY(order_id)   REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS price_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id   INTEGER NOT NULL,
    price        REAL NOT NULL,
    timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_simulated INTEGER DEFAULT 0,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE INDEX IF NOT EXISTS idx_price_history_product
    ON price_history(product_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_orders_created
    ON orders(created_at);
"""


# ─────────────────────────────────────────────────────────────
# Bağlantı Yönetimi
# ─────────────────────────────────────────────────────────────
@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """
    SQLite bağlantısını güvenli şekilde açar.
    Hata olursa rollback, normal çıkışta commit yapar.
    """
    conn = sqlite3.connect(config.DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database() -> None:
    """Tabloları kurar (yoksa oluşturur)."""
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)


def execute(query: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Hızlı SELECT için yardımcı."""
    with get_connection() as conn:
        cur = conn.execute(query, params)
        return cur.fetchall()


def execute_write(query: str, params: tuple = ()) -> int:
    """INSERT/UPDATE/DELETE; etkilenen satır id'sini döner."""
    with get_connection() as conn:
        cur = conn.execute(query, params)
        return cur.lastrowid or cur.rowcount


def reset_database() -> None:
    """
    DİKKAT: Tüm verileri siler. Sadece geliştirme/seed için kullanın.
    """
    import os
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    init_database()
