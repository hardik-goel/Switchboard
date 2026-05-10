"""Example execution flow snippets for runtime orchestration.

```python
from smart_router.core.orchestrator import ExecutionRequest, ProviderOrchestrator
from smart_router.core.registry import ProviderRegistry
from smart_router.providers.openai import register_openai_provider

registry = ProviderRegistry()
register_openai_provider(registry, config_engine)
orchestrator = ProviderOrchestrator(registry, max_retries=1)

request = ExecutionRequest(
    provider="openai",
    model="gpt-5.4",
    messages=[{"role": "user", "content": "Explain this module"}],
    session_id="sess-10",
)

result = await orchestrator.execute(request)
```
"""
