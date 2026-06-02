"""Main command-line importer for daily stock lending Excel files."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

import pandas as pd

from brokerage_configs import BROKERAGE_CONFIGS
from database import import_stock_lending_rows


FINAL_COLUMNS = ["stock_ticker", "amount", "duration", "rate"]
REQUIRED_COLUMNS = ["brokerage", "data_date", "stock_ticker", "duration"]


def normalize_column_name(value) -> str:
    """Make Excel column names easier to match across brokerages."""
    text = str(value).strip().lower()
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def clean_stock_ticker(value) -> str:
    """Return Chinese stock tickers as 6-character text values."""
    if value is None or pd.isna(value):
        return ""

    ticker = str(value).strip()

    # Handle Excel/pandas values like 1.0.
    if ticker.endswith(".0"):
        ticker = ticker[:-2]

    ticker = ticker.replace(" ", "")
    if ticker.isdigit():
        ticker = ticker.zfill(6)

    return ticker.upper()


def clean_standardized_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean mapped columns before row validation."""
    df = df.copy()
    df["stock_ticker"] = df["stock_ticker"].apply(clean_stock_ticker)
    return df


def clean_duration(value):
    if pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def clean_rate(value):
    """Convert rates to decimals for MySQL.

    Examples:
    - 0.035 -> Decimal("0.035")
    - "3.5%" -> Decimal("0.035")
    - 3.5 -> Decimal("0.035")
    """
    if pd.isna(value) or str(value).strip() == "":
        return None

    text = str(value).strip().replace(",", "")
    has_percent = "%" in text
    text = text.replace("%", "")

    try:
        rate = Decimal(text)
    except InvalidOperation:
        return None

    if has_percent or rate > 1:
        rate = rate / Decimal("100")

    return rate


def clean_data_date(value: str) -> str:
    if not value.strip():
        return date.today().isoformat()

    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("Date must use yyyy-mm-dd format, for example 2026-06-01.") from exc


def choose_brokerage() -> str:
    brokerages = list(BROKERAGE_CONFIGS.keys())
    print("\nAvailable brokerages:")
    for index, brokerage in enumerate(brokerages, start=1):
        print(f"  {index}. {brokerage}")

    choice = input("\nWhich brokerage is this file from? Enter name or number: ").strip()
    if choice.isdigit():
        selected_index = int(choice) - 1
        if 0 <= selected_index < len(brokerages):
            return brokerages[selected_index]

    for brokerage in brokerages:
        if choice.lower() == brokerage.lower():
            return brokerage

    raise ValueError(f"Unknown brokerage: {choice}")


def build_standardized_dataframe(raw_df: pd.DataFrame, column_mapping: dict) -> pd.DataFrame:
    """Return only the final columns needed by the database."""
    normalized_mapping = {
        normalize_column_name(source): target for source, target in column_mapping.items()
    }
    output = pd.DataFrame(index=raw_df.index)

    for original_column in raw_df.columns:
        normalized_column = normalize_column_name(original_column)
        target_column = normalized_mapping.get(normalized_column)
        if target_column in FINAL_COLUMNS and target_column not in output.columns:
            output[target_column] = raw_df[original_column]

    for column in FINAL_COLUMNS:
        if column not in output.columns:
            output[column] = ""

    return output[FINAL_COLUMNS]


def apply_default_duration(
    standardized_df: pd.DataFrame,
    default_duration_days,
) -> pd.DataFrame:
    """Fill duration when a brokerage config explicitly provides a default."""
    if default_duration_days is None:
        return standardized_df

    standardized_df = standardized_df.copy()
    standardized_df["duration"] = standardized_df["duration"].replace("", pd.NA)
    standardized_df.loc[standardized_df["duration"].isna(), "duration"] = (
        str(default_duration_days)
    )
    return standardized_df


def validate_required_mapped_columns(
    raw_df: pd.DataFrame,
    standardized_df: pd.DataFrame,
    default_duration_days=None,
) -> None:
    """Fail early if required Excel columns were not mapped."""
    missing = [
        column
        for column in ("stock_ticker", "duration")
        if standardized_df[column].replace("", pd.NA).isna().all()
    ]
    if "duration" in missing and default_duration_days is not None:
        missing.remove("duration")
    if not missing:
        return

    original_columns = [str(column) for column in raw_df.columns]
    normalized_columns = [normalize_column_name(column) for column in raw_df.columns]

    raise ValueError(
        "No usable data was mapped for required field(s): "
        + ", ".join(missing)
        + ". Update brokerage_configs.py for the selected brokerage.\n\n"
        + "Excel columns found:\n  - "
        + "\n  - ".join(original_columns)
        + "\n\nNormalized names to use in column_mapping:\n  - "
        + "\n  - ".join(normalized_columns)
    )


def validate_and_clean_rows(
    df: pd.DataFrame,
    brokerage: str,
    data_date: str,
    source_file: str,
) -> tuple[list[dict], Counter]:
    valid_rows = []
    skipped_reasons = Counter()

    for row_number, row in df.iterrows():
        cleaned = {
            "brokerage": brokerage,
            "data_date": data_date,
            "stock_ticker": row.get("stock_ticker"),
            "amount": "" if pd.isna(row.get("amount")) else str(row.get("amount")).strip(),
            "duration": clean_duration(row.get("duration")),
            "rate": clean_rate(row.get("rate")),
            "source_file": source_file,
        }

        missing_required = [
            column for column in REQUIRED_COLUMNS if cleaned.get(column) in (None, "")
        ]
        if missing_required:
            skipped_reasons[f"missing/invalid {', '.join(missing_required)}"] += 1
            continue

        valid_rows.append(cleaned)

    return valid_rows, skipped_reasons


def main():
    print("Daily SBL Excel Importer")
    print("========================")

    try:
        brokerage_key = choose_brokerage()
        brokerage_name = BROKERAGE_CONFIGS[brokerage_key]["brokerage_name"]

        file_path_input = input("\nExcel file path: ").strip().strip("'\"")
        file_path = Path(file_path_input).expanduser()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if file_path.suffix.lower() != ".xlsx":
            raise ValueError("Please provide an Excel .xlsx file.")

        data_date = clean_data_date(input("File date yyyy-mm-dd (blank = today): "))

        print("\nReading Excel file...")
        raw_df = pd.read_excel(file_path)
        rows_read = len(raw_df)

        column_mapping = BROKERAGE_CONFIGS[brokerage_key]["column_mapping"]
        default_duration_days = BROKERAGE_CONFIGS[brokerage_key].get(
            "default_duration_days"
        )
        standardized_df = build_standardized_dataframe(raw_df, column_mapping)
        standardized_df = apply_default_duration(
            standardized_df,
            default_duration_days=default_duration_days,
        )
        validate_required_mapped_columns(
            raw_df,
            standardized_df,
            default_duration_days=default_duration_days,
        )
        standardized_df = clean_standardized_dataframe(standardized_df)
        valid_rows, skipped_reasons = validate_and_clean_rows(
            standardized_df,
            brokerage=brokerage_name,
            data_date=data_date,
            source_file=file_path.name,
        )

        import_summary = import_stock_lending_rows(valid_rows)
        skipped_count = rows_read - len(valid_rows)

        print("\nImport summary")
        print("--------------")
        print(f"Rows read: {rows_read}")
        print(f"Rows inserted: {import_summary['inserted']}")
        print(f"Rows updated: {import_summary['updated']}")
        print(f"Rows unchanged duplicates: {import_summary['unchanged_duplicates']}")
        print(f"Rows skipped: {skipped_count}")

        if import_summary["unchanged_duplicates"]:
            print(
                "\nUnchanged duplicates mean the row already existed in MySQL "
                "with the same amount, rate, and source file, so it was left alone."
            )

        if skipped_reasons:
            print("\nSkipped row reasons:")
            for reason, count in skipped_reasons.items():
                print(f"  - {reason} ({count})")

        print("\nDone.")

    except Exception as exc:
        print(f"\nImport failed: {exc}")
        raise


if __name__ == "__main__":
    main()
