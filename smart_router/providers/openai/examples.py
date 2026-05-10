"""Example usage snippets for OpenAI provider adapter.

Example: build provider from config engine

```python
from pathlib import Path
from smart_router.core.config import ConfigEngine
from smart_router.providers.openai import OpenAIProvider
from smart_router.schemas.provider import ProviderMessage

engine = ConfigEngine(Path("smart_router/configs/default.yaml"))
engine.load()
provider = OpenAIProvider.from_config_engine(engine, session_id="sess-1")

response = await provider.generate(
    [ProviderMessage(role="user", content="Summarize this repo")],
    model="gpt-5.4",
)
```
"""
