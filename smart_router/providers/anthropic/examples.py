"""Example usage snippets for Anthropic provider.

```python
from pathlib import Path
from smart_router.core.config import ConfigEngine
from smart_router.providers.anthropic import AnthropicProvider
from smart_router.schemas.provider import ProviderMessage

engine = ConfigEngine(Path("smart_router/configs/default.yaml"))
engine.load()
provider = AnthropicProvider.from_config_engine(engine, session_id="sess-2")

result = await provider.generate(
    [ProviderMessage(role="user", content="Summarize this code")],
    model="claude-sonnet",
)
```
"""
