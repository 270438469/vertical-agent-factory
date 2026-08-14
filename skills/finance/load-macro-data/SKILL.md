---
name: load-macro-data
description: Load bounded, dated macroeconomic observations for a governed finance analysis.
---

# Load Macro Data

Normalize the requested region, call `finance.macro_data.read`, preserve indicator identifiers,
dates and sources, and return an explicit empty dataset when coverage is unavailable. Never
substitute a model-generated value for missing source data.
