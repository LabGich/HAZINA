# Hazina V2 sample data pack

## Kenyan bank fixtures (synthetic)
The four bank CSV and JSON files in this pack are synthetic test fixtures, not genuine customer statements and not official bank-issued sample exports. They are based on the column layouts and examples found in public research. Verify against an authorized, redacted export before treating a mapping as bank-production compatible.

- Equity: Date, Description, Debit, Credit, Balance. Illustrative DD-MM-YYYY date.
- KCB: NO., DATE, REFERENCE NO, DETAILS, Debit, Credit, DEBIT, CREDIT BALANCE. Based on a publicly accessible KCB statement sample; its debit and credit balance columns should be interpreted carefully before mapping.
- Co-operative Bank: Date, Transaction Details, Withdrawals, Deposits, Balance.
- NCBA: Date, Narration, Debits, Credits, Balance. NCBA's internet banking manual documents statement generation in Excel, PDF or XML; this CSV is only a fixture.

All sample monetary amounts are KES and intentionally fictional.

## External source datasets (download from source)
### Explore My Data — Bank Transactions (CC0)
The dataset page offers 100-row and 1,000-row files in CSV, JSON, JSONL, Excel and Parquet:
https://exploremydata.com/datasets/bank-transactions

Direct downloads:
- CSV 100: https://exploremydata.com/datasets/bank-transactions-100.csv
- CSV 1,000: https://exploremydata.com/datasets/bank-transactions-1000.csv
- JSON 100: https://exploremydata.com/datasets/bank-transactions-100.json
- JSON 1,000: https://exploremydata.com/datasets/bank-transactions-1000.json
- JSONL 100: https://exploremydata.com/datasets/bank-transactions-100.jsonl
- JSONL 1,000: https://exploremydata.com/datasets/bank-transactions-1000.jsonl
- Excel 100: https://exploremydata.com/datasets/bank-transactions-100.xlsx
- Excel 1,000: https://exploremydata.com/datasets/bank-transactions-1000.xlsx
- Parquet 100: https://exploremydata.com/datasets/bank-transactions-100.parquet
- Parquet 1,000: https://exploremydata.com/datasets/bank-transactions-1000.parquet

The data is synthetic, public domain CC0, USD-denominated, and has signed amounts and per-account reconciled running balances.

### Utilly — fictional bank statement
Guide and downloadable files:
https://getutilly.com/guides/sample-bank-statement-csv
https://getutilly.com/guides/sample-bank-statement-files
https://getutilly.com/guides/sample-bank-statement-excel

Direct sample downloads documented on the guide:
- Bank-style CSV (title lines, Debit/Credit split, beginning balance and totals): https://getutilly.com/sample/bank-csv.csv
- Clean signed-amount CSV: https://getutilly.com/sample/bank/csv
- Excel workbook: https://getutilly.com/sample/bank-xlsx.xlsx
- PDF statement: https://getutilly.com/sample/bank.pdf

The Utilly data is fictional, 31 transactions, with documented totals and a reconciled closing balance. Its guide also links to QuickBooks CSV, Xero CSV, QBO, IIF and QIF variants.

## Important mapping note
Explore My Data and Utilly are independent generic test sources. Do not label either as Equity, KCB, Co-op or NCBA. Use them to test generic signed-amount, split Debit/Credit, parsing, file-format and reconciliation behavior.
