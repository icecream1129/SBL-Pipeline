"""MySQL connection and insert/update helpers for the SBL daily importer."""

from __future__ import annotations

import os
from decimal import Decimal
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
            + " so duplicate rows can be detected"
        )

    if problems:
        raise RuntimeError(
            "stock_lending_data is not using the preferred importer structure yet. "
            + "Please review setup_table.sql. Problems found: "
            + "; ".join(problems)
        )


def values_are_equal(existing_value, new_value) -> bool:
    """Compare MySQL values with cleaned Python values."""
    if existing_value is None and new_value is None:
        return True
    if existing_value is None or new_value is None:
        return False
    if isinstance(existing_value, Decimal) or isinstance(new_value, Decimal):
        return Decimal(str(existing_value)) == Decimal(str(new_value))
    return str(existing_value) == str(new_value)


def rows_are_unchanged(existing_row: dict, new_row: dict) -> bool:
    """Return True when the database row already matches the upload row."""
    return (
        values_are_equal(existing_row["amount"], new_row["amount"])
        and values_are_equal(existing_row["rate"], new_row["rate"])
        and values_are_equal(existing_row["source_file"], new_row["source_file"])
    )


def import_stock_lending_rows(rows: Iterable[dict]) -> dict:
    """Insert new rows, update changed rows, and count unchanged duplicates."""
    rows = list(rows)
    summary = {
        "inserted": 0,
        "updated": 0,
        "unchanged_duplicates": 0,
    }
    if not rows:
        return summary

    select_sql = """
        SELECT amount, rate, source_file
        FROM stock_lending_data
        WHERE brokerage = %(brokerage)s
          AND data_date = %(data_date)s
          AND stock_ticker = %(stock_ticker)s
          AND duration = %(duration)s
        LIMIT 1
    """

    insert_sql = """
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
    """

    update_sql = """
        UPDATE stock_lending_data
        SET
            amount = %(amount)s,
            rate = %(rate)s,
            source_file = %(source_file)s,
            updated_at = CURRENT_TIMESTAMP
        WHERE brokerage = %(brokerage)s
          AND data_date = %(data_date)s
          AND stock_ticker = %(stock_ticker)s
          AND duration = %(duration)s
    """

    connection = get_connection()
    try:
        validate_table_structure(connection)
        with connection.cursor(dictionary=True) as cursor:
            for row in rows:
                cursor.execute(select_sql, row)
                existing_row = cursor.fetchone()

                if existing_row is None:
                    cursor.execute(insert_sql, row)
                    summary["inserted"] += 1
                elif rows_are_unchanged(existing_row, row):
                    summary["unchanged_duplicates"] += 1
                else:
                    cursor.execute(update_sql, row)
                    summary["updated"] += 1

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return summary
