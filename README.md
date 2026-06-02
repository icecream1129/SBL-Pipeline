# Daily SBL Excel Importer

This project imports daily stock lending Excel `.xlsx` files from multiple brokerages into one MySQL table:

```text
new_schema.stock_lending_data
```

Each brokerage can use different Excel column names. Update `brokerage_configs.py` to map those Excel columns into the final database fields.

## Files

- `main_import.py` asks for brokerage, file path, and date, then cleans and imports the Excel rows.
- `brokerage_configs.py` stores editable column mappings for each brokerage.
- `database.py` handles the MySQL connection and insert/update logic.
- `setup_table.sql` creates the preferred table and includes safe ALTER suggestions.
- `.env.example` shows the MySQL login variables needed by the importer.
- `requirements.txt` lists the Python packages to install.

## Install Packages

From this folder:

```bash
python3 -m pip install -r requirements.txt
```

## Set Up `.env`

Create a file named `.env` in this folder:

```bash
cp .env.example .env
```

Then edit `.env` with your real MySQL details:

```text
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_real_password
MYSQL_DATABASE=new_schema
```

Do not put real passwords into the Python files.

## Set Up the Table

Open `setup_table.sql` in your MySQL client and run the `CREATE TABLE IF NOT EXISTS` statement.

Your current table already existed when this project was created. It had the core columns, but was missing the tracking fields and did not have the preferred primary key. Review the commented `ALTER TABLE` suggestions in `setup_table.sql` before running them.

The importer uses this duplicate/update rule:

```text
brokerage + data_date + stock_ticker + duration
```

The table needs a primary key or unique key on those four columns so the importer can tell whether a row is new, changed, or already unchanged.

When a row already exists, the importer compares `amount`, `rate`, and `source_file`. Exact matches are counted as unchanged duplicates and are not updated.

## Run the Importer

From this folder:

```bash
python3 main_import.py
```

The script will ask:

1. Which brokerage the file belongs to
2. The Excel `.xlsx` file path
3. The file date in `yyyy-mm-dd` format

If you leave the date blank, the script uses today's date.

## Update Brokerage Mappings

Open `brokerage_configs.py`.

Each mapping uses this format:

```python
"Excel column name": "database_column_name"
```

Example:

```python
"stock code": "stock_ticker",
"qty": "amount",
"days": "duration",
"fee rate": "rate",
```

You can add more possible Excel names for each brokerage. The final database column names should stay as:

```text
stock_ticker
amount
duration
rate
```

## Cleaning Rules

- Stock tickers are stripped, uppercased, and required.
- Duration is converted to an integer number of days and is required.
- Missing amount is stored as a blank string.
- Missing rate is stored as `NULL`.
- Rates are converted to decimals:
  - `0.035` stays `0.035`
  - `3.5%` becomes `0.035`
  - `3.5` becomes `0.035`

Rows missing required fields are skipped and listed in the final summary.
