"""Example prompt classifications.

```python
from smart_router.core.analyzer import PromptAnalyzer

analyzer = PromptAnalyzer()

# Trivial task
await analyzer.analyze("rename variable foo to bar in this file")

# Debugging task
await analyzer.analyze("debug failing test with stack trace in auth module")

# Refactor
await analyzer.analyze("refactor payment service logic across multiple files")

# Architecture redesign
await analyzer.analyze("redesign architecture for multi-tenant auth and concurrency safety")

# Repo migration
await analyzer.analyze("migrate repo-wide API usage from v1 to v2 across all modules")
```
"""
