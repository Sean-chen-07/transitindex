"""Source adapters: turn a raw external feed into MetricValueRecords.

Each adapter parses one source format (StatCan tables, open-data CSVs, ...) into
the canonical `MetricValueRecord` shape. Pure stdlib; fetchers do the I/O.
"""
