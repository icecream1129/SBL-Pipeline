"""Brokerage-specific column mappings for the SBL daily importer.

Edit the keys in each column_mapping when a brokerage sends a file with
different Excel column names. The values should stay as the final database
column names used by main_import.py.
"""

BROKERAGE_CONFIGS = {
    "Huatai": {
        "brokerage_name": "Huatai",
        "column_mapping": {
            "证券代码": "stock_ticker",
            "证劵代码": "stock_ticker",
            "stock code": "stock_ticker",
            "数量（股）": "amount",
            "数量": "amount",
            "可用数量": "amount",
            "期限": "duration",
            "最长可用期限": "duration",
            "利率": "rate",
            "费率": "rate",
        },
    },
    "Guotai": {
        "brokerage_name": "Guotai",
        "column_mapping": {
            "证券代码": "stock_ticker",
            "证劵代码": "stock_ticker",
            "stock code": "stock_ticker",
            "数量": "amount",
            "可用数量": "amount",
            "最长可用期限": "duration",
            "期限": "duration",
            "费率": "rate",
            "利率": "rate",
        },
    },
    "CITIC": {
        "brokerage_name": "CITIC",
        "column_mapping": {
            "证券代码": "stock_ticker",
            "证劵代码": "stock_ticker",
            "stock code": "stock_ticker",
            "数量": "amount",
            "可用数量": "amount",
            "期限": "duration",
            "最长可用期限": "duration",
        },
    },
    "Haitong": {
        "brokerage_name": "Haitong",
        # Use 0 when this brokerage's file does not provide a duration column.
        # This keeps the primary key consistent while marking duration as unknown.
        "default_duration_days": 0,
        "column_mapping": {
            "Stock Code": "stock_ticker",
            "证券代码": "stock_ticker",
            "证劵代码": "stock_ticker",
            "Available Quantity": "amount",
            "数量": "amount",
            "可用数量": "amount",
            "期限": "duration",
            "最长可用期限": "duration",
            "Duration": "duration",
            "Rate(%)": "rate",
            "费率": "rate",
            "利率": "rate",
            "参考基准费率": "rate",
        },
    },
}
