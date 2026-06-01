"""Brokerage-specific column mappings for the SBL daily importer.

Edit the keys in each column_mapping when a brokerage sends a file with
different Excel column names. The values should stay as the final database
column names used by main_import.py.
"""

BROKERAGE_CONFIGS = {
    "BrokerageA": {
        "brokerage_name": "BrokerageA",
        "column_mapping": {
            "stock code": "stock_ticker",
            "stock ticker": "stock_ticker",
            "ticker": "stock_ticker",
            "证券代码": "stock_ticker",
            "qty": "amount",
            "quantity": "amount",
            "amount": "amount",
            "数量": "amount",
            "days": "duration",
            "duration": "duration",
            "期限": "duration",
            "rate": "rate",
            "fee rate": "rate",
            "费率": "rate",
        },
    },
    "BrokerageB": {
        "brokerage_name": "BrokerageB",
        "column_mapping": {
            "stock code": "stock_ticker",
            "证券代码": "stock_ticker",
            "available quantity": "amount",
            "可用数量": "amount",
            "duration": "duration",
            "最长可用期限": "duration",
            "rate": "rate",
            "参考基准费率": "rate",
        },
    },
    "BrokerageC": {
        "brokerage_name": "BrokerageC",
        "column_mapping": {
            "stock code": "stock_ticker",
            "证券代码": "stock_ticker",
            "quantity": "amount",
            "数量": "amount",
            "duration": "duration",
            "期限": "duration",
            # If this brokerage has no rate column, leave rate mappings out.
        },
    },
    "BrokerageD": {
        "brokerage_name": "BrokerageD",
        "column_mapping": {
            "stock code": "stock_ticker",
            "证券代码": "stock_ticker",
            "amount": "amount",
            "数量": "amount",
            "days": "duration",
            "期限": "duration",
            "rate": "rate",
            "利率": "rate",
        },
    },
}
