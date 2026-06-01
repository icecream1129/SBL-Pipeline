"""MySQL connection and upsert helpers for the SBL daily importer."""

from __future__ import annotations

import os
from typing import Iterable

import mysql.connector
from dotenv import load_dotenv


REQUIRED_TABLE_COLUMNS = {
    "brokerage",
    "data_date",
    "stock_ticker",
    "amount",
    "duration",
    "rate",
    "source_file",
    "uploaded_at",
    "updated_at",
}


def get_connection():
    """Create a MySQL connection using values from .env or environment."""
    load_dotenv()

    required_env_vars = ["MYSQL_HOST", "MYSQL_USER", "MYSQL_DATABASE"]
    missing = [name for name in required_env_vars if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
            + ". Create a .env file based on .env.example."
        )

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE"),
    )


def validate_table_structure(connection) -> None:
    """Check the table has the columns and key needed by the importer."""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute("SHOW COLUMNS FROM stock_lending_data")
        columns = {row["Field"] for row in cursor.fetchall()}

        cursor.execute("SHOW INDEX FROM stock_lending_data")
        indexes = cursor.fetchall()

    missing_columns = sorted(REQUIRED_TABLE_COLUMNS - columns)
    if "stocker_ticker" in columns:
        missing_columns.append("rename stocker_ticker to stock_ticker")

    primary_key_columns = [
        row["Column_name"]
        for row in sorted(indexes, key=lambda item: item["Seq_in_index"])
        if row["Key_name"] == "PRIMARY"
    ]
    expected_primary_key = ["brokerage", "data_date", "stock_ticker", "duration"]

    problems = []
    if missing_columns:
        problems.append("missing columns: " + ", ".join(missing_columns))
    if primary_key_columns != expected_primary_key:
        problems.append(
            "primary key should be "
            + ", ".join(expected_primary_key)
            + " for ON DUPLICATE KEY UPDATE to work"
        )

    if problems:
        raise RuntimeError(
            "stock_lending_data is not using the preferred importer structure yet. "
            + "Please review setup_table.sql. Problems found: "
            + "; ".join(problems)
        )


def upsert_stock_lending_rows(rows: Iterable[dict]) -> int:
    """Insert rows and update existing rows that share the table primary key."""
    rows = list(rows)
    if not rows:
        return 0

    sql = """
        INSERT INTO stock_lending_data (
            brokerage,
            data_date,
            stock_ticker,
            amount,
            duration,
            rate,
            source_file
        )
        VALUES (
            %(brokerage)s,
            %(data_date)s,
            %(stock_ticker)s,
            %(amount)s,
            %(duration)s,
            %(rate)s,
            %(source_file)s
        )
        ON DUPLICATE KEY UPDATE
            amount = VALUES(amount),
            rate = VALUES(rate),
            source_file = VALUES(source_file),
            updated_at = CURRENT_TIMESTAMP
    """

    connection = get_connection()
    try:
        validate_table_structure(connection)
        with connection.cursor() as cursor:
            cursor.executemany(sql, rows)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return len(rows)
