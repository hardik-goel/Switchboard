"""Configuration schemas for routing and providers."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Model capability and cost metadata."""

    name: str = Field(min_length=1)
    max_input_tokens: int = Field(ge=1)
    max_output_tokens: int = Field(ge=1)
    latency_tier: str = Field(min_length=1)
    reasoning_tier: str = Field(min_length=1)
    cost_per_1k_input: float = Field(ge=0.0)
    cost_per_1k_output: float = Field(ge=0.0)
    context_window: int = Field(default=128000, ge=1)
    speed_class: str = Field(default="balanced", min_length=1)
    streaming_support: bool = True
    tool_support: bool = False
    capabilities: list[str] = Field(default_factory=list)


class ProviderConfig(BaseModel):
    """Provider-level config and listed models."""

    enabled: bool = True
    api_base: str | None = None
    settings: dict[str, str | int | float | bool] = Field(default_factory=dict)
    models: list[ModelConfig] = Field(default_factory=list)


class RoutingPolicyConfig(BaseModel):
    """Policy knobs controlling deterministic routing behavior."""

    default_provider: str = Field(min_length=1)
    fallback_order: list[str] = Field(default_factory=list)
    max_cost_per_request: float | None = Field(default=None, ge=0.0)
    prioritize_latency: bool = False
    prioritize_cost: bool = False


class AppConfig(BaseModel):
    """Top-level application configuration."""

    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    routing: RoutingPolicyConfig
