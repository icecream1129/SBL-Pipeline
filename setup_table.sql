-- Safe setup for a daily stock lending import table.
-- This file does not drop or delete existing data.
-- Change the database/schema name in your MySQL client if needed.

CREATE TABLE IF NOT EXISTS stock_lending_data (
    brokerage VARCHAR(100) NOT NULL,
    data_date DATE NOT NULL,
    stock_ticker VARCHAR(50) NOT NULL,
    amount VARCHAR(100) DEFAULT '',
    duration INT NOT NULL,
    rate DECIMAL(12, 6) NULL,
    source_file VARCHAR(255) DEFAULT '',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (brokerage, data_date, stock_ticker, duration)
);

-- If you already have a table, do not drop it blindly.
-- First inspect it:
--
-- SHOW COLUMNS FROM stock_lending_data;
-- SHOW INDEX FROM stock_lending_data;
--
-- If columns are missing, review and run only the ALTER statements you need.

-- ALTER TABLE stock_lending_data
--     ADD COLUMN source_file VARCHAR(255) DEFAULT '',
--     ADD COLUMN uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- ALTER TABLE stock_lending_data
--     MODIFY brokerage VARCHAR(100) NOT NULL,
--     MODIFY stock_ticker VARCHAR(50) NOT NULL,
--     MODIFY amount VARCHAR(100) DEFAULT '',
--     MODIFY rate DECIMAL(12, 6) NULL;

-- ON DUPLICATE KEY UPDATE needs this primary key or an equivalent unique key:
-- ALTER TABLE stock_lending_data
--     ADD PRIMARY KEY (brokerage, data_date, stock_ticker, duration);

-- If you ever find a column named stocker_ticker, rename it to stock_ticker:
-- ALTER TABLE stock_lending_data
--     RENAME COLUMN stocker_ticker TO stock_ticker;
