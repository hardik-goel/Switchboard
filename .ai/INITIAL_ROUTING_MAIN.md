You are building a production-grade modular AI routing/orchestration CLI system.

IMPORTANT:
Before doing anything:

1. Read all files inside `.ai/`
2. Treat `.ai/ARCHITECTURE.md` as source of truth
3. Treat `.ai/IMPLEMENTATION_STATUS.md` as current project state
4. Treat `.ai/NEXT_STEPS.md` as execution priority
5. Treat `.ai/CODING_STANDARDS.md` as mandatory rules
6. Treat `ai/SESSION_CONTEXT.md` as Temporary working memory.

(AI updates:

current assumptions
current blockers
temporary reasoning

Then clears stale entries later.)

Your responsibilities:

* continue project safely
* preserve architecture
* maintain modularity
* avoid hidden dependencies
* avoid rewriting stable modules
* maintain strict contracts/interfaces
* update project memory files continuously

SYSTEM GOAL:
Create a local terminal AI router that intelligently routes coding prompts between:

* OpenAI models
* Claude models
* Gemini
* Ollama/local models
* future providers

Routing decisions based on:

* complexity
* latency
* cost
* reasoning depth
* repository size
* token estimates
* fallback policies

TECH STACK:

* Python
* Typer
* Pydantic
* YAML config
* SQLite telemetry
* async-first architecture

MANDATORY RULES:

* Strong typing everywhere
* Tests mandatory
* Logging mandatory
* No hidden dependencies
* No architecture drift
* No undocumented abstractions
* Config-driven design only

WORKFLOW:

1. Read `.ai/`
2. Determine current state
3. Determine next logical task
4. Implement ONLY that task
5. Add/update tests
6. Update:

   * IMPLEMENTATION_STATUS.md
   * DECISIONS_LOG.md
   * NEXT_STEPS.md
7. Show changed file tree
8. Explain integration impact

Before implementing:

* explicitly state which ROADMAP phase/subphase is being worked on
* explicitly state what remains after completion

DO NOT:

* rebuild unrelated modules
* redesign architecture unnecessarily
* create monolithic code
* skip tests
* skip typing
* skip logging

If architecture gaps exist:

* document them first
* then implement minimally compatible solutions

Start by:

1. analyzing repository state
2. summarizing current architecture
3. identifying next implementation target
4. implementing incrementally
