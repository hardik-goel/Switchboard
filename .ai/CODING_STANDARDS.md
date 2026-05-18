# CODING STANDARDS

## Mandatory Rules

* Strong typing everywhere
* Async-first architecture
* No hidden dependencies
* No global mutable state
* All modules independently testable
* Pydantic for schemas
* Typer for CLI
* YAML-based config
* Structured logging only
* Explicit error handling
* No hardcoded provider logic
* No business logic inside CLI layer
* Provider abstraction mandatory
* Every module must expose clean interfaces
* Every module requires tests
* Every module requires docstrings

## File Organization

* One responsibility per module
* Avoid god classes
* Avoid circular imports
* Shared contracts go in schemas/
* Shared interfaces go in core/interfaces/

## AI Development Rules

When implementing:

* NEVER redesign unrelated modules
* NEVER rewrite stable code unnecessarily
* NEVER invent undocumented interfaces
* ALWAYS read .ai/*.md files first
* ALWAYS update IMPLEMENTATION_STATUS.md
* ALWAYS update DECISIONS_LOG.md when architectural decisions change
* ALWAYS keep backward compatibility unless explicitly instructed

## Output Expectations

Every implementation must include:

* code
* tests
* logging
* type hints
* error handling
* example usage
