"""Verified-datasheet tooling (annotation + derivedFrom expansion).

Marked as a regular package so `optimization_validator.kfold` can import the single
derivedFrom-expansion implementation via `verified_datasheet.expand_derived.expand_rows`
without relying on implicit namespace-package resolution.
"""
