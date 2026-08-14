---
name: load-a-share-data
description: Load normalized A-share daily market observations from an approved data source.
---

# Load A-share Data

Normalize six-digit symbols to their SH, SZ or BJ suffix, request a bounded lookback window,
preserve the trading date and source, and return no observations for an invalid symbol. Do not
scrape unapproved websites or infer missing prices.
