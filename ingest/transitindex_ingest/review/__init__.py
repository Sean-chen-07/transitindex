"""FastAPI human review queue (M2 review UI backend).

Exposes core.pending_values over a Repository and routes approval through
promotion.promote_one -- the only door into core.metric_values (Invariant #1).
"""
