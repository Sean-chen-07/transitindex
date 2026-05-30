"""Gold-fixture evaluation harness for the LLM PDF extractor.

`gold` scores an extractor run against hand-verified true values, guarding
against prompt/model regressions: precision (clean values land within
tolerance) and flag-recall (the hard rows get flagged for review).
"""
